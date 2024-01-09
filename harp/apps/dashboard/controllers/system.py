import re
from copy import deepcopy

from harp import __revision__, __version__
from harp.apps.dashboard.utils.dependencies import get_python_dependencies, parse_dependencies
from harp.core.asgi.messages.requests import ASGIRequest
from harp.core.asgi.messages.responses import ASGIResponse
from harp.core.views.json import json
from harp.typing.global_settings import GlobalSettings


def _asdict(obj):
    if isinstance(obj, dict):
        return {k: _asdict(v) for k, v in obj.items()}

    if isinstance(obj, list):
        return [_asdict(v) for v in obj]

    if isinstance(obj, tuple):
        return tuple(_asdict(v) for v in obj)

    if hasattr(obj, "to_dict"):
        result = _asdict(obj.to_dict())
        if isinstance(result, dict):
            return {"@type": type(obj).__name__, **result}
        return result

    return obj


class SystemController:
    prefix = "/api/system"

    def __init__(self, settings: GlobalSettings):
        # a bit of scrambling for passwords etc.
        if "storage" in settings:
            if "url" in settings["storage"]:
                settings["storage"]["url"] = re.sub(r"//[^@]*@", "//***@", settings["storage"]["url"])

        self.settings = deepcopy(dict(settings))
        self._dependencies = None

    def register(self, router):
        router.route(self.prefix + "/")(self.get)
        router.route(self.prefix + "/settings")(self.get_settings)
        router.route(self.prefix + "/dependencies")(self.get_dependencies)

    async def get(self, request: ASGIRequest, response: ASGIResponse):
        context = getattr(request, "context", {})

        return json(
            {
                "version": __version__,
                "revision": __revision__,
                "user": context.get("user"),
            }
        )

    async def get_settings(self, request: ASGIRequest, response: ASGIResponse):
        return json(self.settings)

    async def get_dependencies(self, request: ASGIRequest, response: ASGIResponse):
        return json({"python": await self.__get_cached_python_dependencies()})

    async def __get_cached_python_dependencies(self):
        if self._dependencies is None:
            self._dependencies = parse_dependencies(await get_python_dependencies())
        return self._dependencies
