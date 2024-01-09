from typing import Type, cast

from rodi import Container
from whistle import IAsyncEventDispatcher

from harp import get_logger
from harp.config import Config
from harp.core.asgi import ASGIKernel, ASGIRequest, ASGIResponse
from harp.core.asgi.events import EVENT_CORE_REQUEST, EVENT_CORE_VIEW, RequestEvent
from harp.core.asgi.resolvers import ProxyControllerResolver
from harp.core.event_dispatcher import LoggingAsyncEventDispatcher
from harp.core.views.json import on_json_response
from harp.typing import GlobalSettings
from harp.utils.network import Bind

from .events import EVENT_FACTORY_BIND, EVENT_FACTORY_BOUND, FactoryBindEvent, FactoryBoundEvent

logger = get_logger(__name__)


async def ok_controller(request: ASGIRequest, response: ASGIResponse):
    await response.start(status=200)
    await response.body("Ok.")


async def on_health_request(event: RequestEvent):
    if event.request.path == "/healthz":
        event.set_controller(ok_controller)
        event.stop_propagation()


class KernelFactory:
    AsyncEventDispatcherType: Type[IAsyncEventDispatcher] = LoggingAsyncEventDispatcher
    ContainerType: Type[Container] = Container
    KernelType: Type[ASGIKernel] = ASGIKernel

    def __init__(self, configuration: Config):
        self.configuration = configuration
        self.hostname = "[::]"

    async def build(self):
        # we only work on validated configuration
        self.configuration.validate()

        for application in self.configuration.applications:
            logger.info(f"📦 {application}")

        dispatcher = self.build_event_dispatcher()
        container = self.build_container(dispatcher)
        resolver = ProxyControllerResolver()

        # dispatch "bind" event: this is the last chance to add services to the container
        await dispatcher.adispatch(
            EVENT_FACTORY_BIND,
            FactoryBindEvent(
                container,
                self.configuration.settings,
            ),
        )

        # this can fail if configuration is not valid, but we let the container raise exception which is more explicit
        # that what we can show here.
        provider = container.build_provider()

        # dispatch "bound" event: you get a resolved container, do your thing
        await dispatcher.adispatch(
            EVENT_FACTORY_BOUND,
            FactoryBoundEvent(
                provider,
                resolver,
                self.configuration.settings,
            ),
        )

        return self.KernelType(dispatcher=dispatcher, resolver=resolver), [
            Bind(host=self.hostname, port=port) for port in resolver.ports
        ]

    def build_container(self, dispatcher: IAsyncEventDispatcher) -> Container:
        """Factory method responsible for the service injection container creation, registering initial services."""
        container = cast(Container, self.ContainerType())
        container.add_instance(self.configuration.settings, GlobalSettings)
        container.add_instance(dispatcher, IAsyncEventDispatcher)

        self.configuration.register_services(container)

        return container

    def build_event_dispatcher(self) -> IAsyncEventDispatcher:
        """Factory method responsible for the event dispatcher creation, binding initial/generic listeners."""
        dispatcher = cast(IAsyncEventDispatcher, self.AsyncEventDispatcherType())

        dispatcher.add_listener(EVENT_CORE_REQUEST, on_health_request, priority=-100)

        # todo move into core or extension, this is not proxy related
        dispatcher.add_listener(EVENT_CORE_VIEW, on_json_response)

        self.configuration.register_events(dispatcher)

        return dispatcher
