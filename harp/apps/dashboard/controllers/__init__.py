import os

from asgi_middleware_static_file import ASGIMiddlewareStaticFile
from http_router import NotFoundError

from harp import ROOT_DIR, get_logger
from harp.apps.dashboard.settings import DashboardSettings
from harp.apps.proxy.controllers import HttpProxyController
from harp.core.asgi import ASGIRequest, ASGIResponse
from harp.core.controllers import RoutingController
from harp.core.views import json
from harp.errors import ProxyConfigurationError
from harp.protocols.storage import IStorage
from harp.typing.global_settings import GlobalSettings

# from harp.apps.dashboard.schemas import TransactionsByDate
from .system import SystemController
from .transactions import TransactionsController

logger = get_logger(__name__)

# Static directories to look for pre-built assets, in order of priority.
STATIC_BUILD_PATHS = [
    os.path.realpath(os.path.join(ROOT_DIR, "frontend/dist")),
    "/opt/harp/public",
]


class DashboardController:
    name = "ui"

    storage: IStorage
    settings: DashboardSettings
    global_settings: GlobalSettings

    _ui_static_middleware = None
    _ui_devserver_proxy_controller = None

    def __init__(self, storage: IStorage, all_settings: GlobalSettings, local_settings: DashboardSettings):
        # context for usage in handlers
        self.storage = storage
        self.global_settings = all_settings
        self.settings = local_settings

        # controllers for delegating requests
        if self.settings.devserver_port:
            self._ui_devserver_proxy_controller = self._create_ui_devserver_proxy_controller(
                port=self.settings.devserver_port
            )

        # register the subcontrollers, aka the api handlers
        self._internal_api_controller = self._create_routing_controller()

        # if no devserver is configured, we may need to serve static files
        if not self._ui_devserver_proxy_controller:
            for _path in STATIC_BUILD_PATHS:
                if os.path.exists(_path):
                    self._ui_static_middleware = ASGIMiddlewareStaticFile(None, "", [_path])
                    break

        # if no devserver is configured and no static files are found, we can't serve the dashboard
        if not self._ui_static_middleware and not self._ui_devserver_proxy_controller:
            raise ProxyConfigurationError(
                "Dashboard controller could not initiate because it got neither compiled assets nor a devserver "
                "configuration."
            )

    def __repr__(self):
        features = {
            "api": bool(self._internal_api_controller),
            "devserver": bool(self._ui_devserver_proxy_controller),
            "static": bool(self._ui_static_middleware),
        }
        return f"{type(self).__name__}({'+'.join(f for f in features if features[f])})"

    def _create_ui_devserver_proxy_controller(self, *, port):
        return HttpProxyController(f"http://localhost:{port}/")

    def _create_routing_controller(self):
        controller = RoutingController(handle_errors=False)
        router = controller.router
        router.route("/api/blobs/{blob}")(self.get_blob)
        router.route("/api/dashboard")(self.get_dashboard_data)
        router.route("/api/dashboard/{endpoint}")(self.get_dashboard_data_for_endpoint)

        # subcontrollers
        for _controller in (
            TransactionsController(self.storage),
            SystemController(self.global_settings),
        ):
            _controller.register(controller.router)

        return controller

    async def __call__(self, request: ASGIRequest, response: ASGIResponse, *, transaction_id=None):
        request.context.setdefault("user", None)

        if self.settings.auth:
            current_auth = request.basic_auth

            if current_auth:
                request.context["user"] = self.settings.auth.check(current_auth[0], current_auth[1])

            if not request.context["user"]:
                response.headers["content-type"] = "text/plain"
                response.headers["WWW-Authenticate"] = 'Basic realm="Harp Dashboard"'
                await response.start(401)
                await response.body(b"Unauthorized")
                return

        # Is this a prebuilt static asset?
        if self._ui_static_middleware and not request.path.startswith("/api/"):
            try:
                return await self._ui_static_middleware(
                    {
                        "type": request._scope["type"],
                        "path": request._scope["path"] if "." in request._scope["path"] else "/index.html",
                        "method": request._scope["method"],
                    },
                    request._receive,
                    response._send,
                )
            finally:
                response.started = True

        try:
            return await self._internal_api_controller(request, response)
        except NotFoundError:
            if self._ui_devserver_proxy_controller:
                return await self._ui_devserver_proxy_controller(request, response)

        await response.start(status=404)
        await response.body("Not found.")

    async def get_blob(self, request: ASGIRequest, response: ASGIResponse, blob):
        blob = await self.storage.get_blob(blob)

        if not blob:
            response.headers["content-type"] = "text/plain"
            await response.start(status=404)
            await response.body(b"Blob not found.")
            return

        response.headers["content-type"] = blob.content_type or "application/octet-stream"
        await response.start(status=200)

        if blob.content_type == "application/json":
            await response.body(blob.prettify())
        else:
            await response.body(blob.data)

    async def overview_from_transactions(self, request: ASGIRequest, response: ASGIResponse):
        self.storage.find_transactions(
            with_messages=False,
        )

    async def get_dashboard_data(self, request: ASGIRequest, response: ASGIResponse):
        transactions_by_date_list = await self.storage.transactions_grouped_by_date()
        errors_count = sum([t["errors"] for t in transactions_by_date_list])
        transactions_count = sum([t["transactions"] for t in transactions_by_date_list])
        errors_rate = errors_count / transactions_count if transactions_count else 0
        mean_duration = (
            sum([t["meanDuration"] * t["transactions"] for t in transactions_by_date_list]) / transactions_count
            if transactions_count
            else 0
        )

        return json(
            {
                "dailyStats": transactions_by_date_list,
                "errors": {"count": errors_count, "rate": errors_rate},
                "transactions": {"count": transactions_count, "meanDuration": mean_duration},
            }
        )

    async def get_dashboard_data_for_endpoint(self, request: ASGIRequest, response: ASGIResponse, endpoint: str):
        data_foo = [
            {"date": "2022-01-01", "transactions": 120, "errors": 100},
            {"date": "2022-01-02", "transactions": 160, "errors": 30},
            {"date": "2022-01-03", "transactions": 200, "errors": 40},
            {"date": "2022-01-04", "transactions": 100, "errors": 50},
            {"date": "2022-01-05", "transactions": 280, "errors": 60},
            {"date": "2022-01-06", "transactions": 320, "errors": 70},
            {"date": "2022-01-07", "transactions": 300, "errors": 50},
            {"date": "2022-01-08", "transactions": 400, "errors": 90},
            {"date": "2022-01-09", "transactions": 440, "errors": 50},
        ]
        data_bar = [
            {"date": "2022-01-01", "transactions": 120, "errors": 20},
            {"date": "2022-01-02", "transactions": 160, "errors": 30},
            {"date": "2022-01-03", "transactions": 200, "errors": 80},
            {"date": "2022-01-04", "transactions": 100, "errors": 50},
            {"date": "2022-01-05", "transactions": 280, "errors": 30},
            {"date": "2022-01-06", "transactions": 320, "errors": 10},
            {"date": "2022-01-07", "transactions": 300, "errors": 50},
            {"date": "2022-01-08", "transactions": 400, "errors": 50},
            {"date": "2022-01-10", "transactions": 440, "errors": 50},
        ]

        endpoints_data = {
            "foo": data_foo,
            "bar": data_bar,
        }

        return json(
            {
                "dailyStats": endpoints_data[endpoint],
                "errors": {"count": 100, "rate": 0.1},
                "transactions": {"count": 1000, "meanDuration": 0.1},
            }
        )
