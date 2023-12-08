"""
:class:`ProxyFactory` is a helper to create proxies. It will load configuration, build services, create an
:class:`ASGIKernel <harp.core.asgi.kernel.ASGIKernel>` and prepare it for its future purpose.
"""
import asyncio
import logging
from typing import Type

from hypercorn.typing import ASGIFramework
from rodi import CannotResolveTypeException, Container, Services

from harp import get_logger
from harp.applications.api.controllers import DashboardController
from harp.applications.proxy.controllers import HttpProxyController
from harp.core.asgi.events import EVENT_CORE_VIEW
from harp.core.asgi.kernel import ASGIKernel
from harp.core.asgi.resolvers import ProxyControllerResolver
from harp.core.event_dispatcher import LoggingAsyncEventDispatcher
from harp.core.factories.events import EVENT_FACTORY_BIND
from harp.core.factories.events.bind import ProxyFactoryBindEvent
from harp.core.factories.settings import create_settings
from harp.core.types.signs import Default
from harp.core.views.json import on_json_response
from harp.protocols.storage import IStorage

logger = get_logger(__name__)


class ProxyFactory:
    DEFAULT_DASHBOARD_PORT = 4080
    KernelType: Type[ASGIKernel] = ASGIKernel

    def __init__(self, *, bind="localhost", settings=None, dashboard=True, dashboard_port=Default):
        self.settings = create_settings(settings)
        self.container = Container()
        self.dispatcher = self._create_event_dispatcher()

        self.resolver = ProxyControllerResolver()

        self.bind = bind
        self.__server_binds = set()

        self.dashboard = dashboard
        self.dashboard_port = dashboard_port

    def _create_event_dispatcher(self):
        """Creates an event dispatcher and registers the default listeners."""
        dispatcher = LoggingAsyncEventDispatcher()

        # todo move into core or extension, this is not proxy related
        dispatcher.add_listener(EVENT_CORE_VIEW, on_json_response)

        return dispatcher

    def add(self, port, target, *, name=None):
        """
        Adds a port to proxy to a remote target (url).

        :param port: The port to listen on.
        :param target: The target url to proxy to.
        :param name: The name of the proxy. This is used to identify the proxy in the dashboard.
        """
        self.resolver.add(port, HttpProxyController(target, name=name, dispatcher=self.dispatcher))
        self.__server_binds.add(f"{self.bind}:{port}")

    def load(self, plugin):
        """
        Loads a python package that can register itself. The plugin spec will be thought about in the far future, but
        for now it mostly consists of a register function that takes a dispatcher as argument.

        :param plugin: The qualified path of the plugin to load.
        """
        try:
            plugin = __import__(plugin, fromlist=["register"])
        except ImportError as exc:
            raise RuntimeError(f"Module {plugin} does not have a register function or could not be imported.") from exc
        plugin.register(self.container, self.dispatcher, self.settings)

    async def create(self) -> ASGIFramework:
        """
        Builds the actual proxy as an ASGI application.

        :param args:
        :param kwargs:
        :return: ASGI application
        """

        # bind services

        logger.info(f"ProxyFactory::create() Settings={repr(self.settings.values)}")
        await self.dispatcher.dispatch(EVENT_FACTORY_BIND, ProxyFactoryBindEvent(self.container, self.settings))
        provider = self.container.build_provider()
        self._on_create_configure_dashboard_if_needed(provider)
        # noinspection PyTypeChecker
        return self.KernelType(dispatcher=self.dispatcher, resolver=self.resolver)

    def _on_create_configure_dashboard_if_needed(self, provider: Services):
        # todo: use self.config['dashboard_enabled'] ???
        if not self.dashboard:
            return

        port = self.settings["dashboard_port"] if "dashboard_port" in self.settings else self.dashboard_port
        if port is Default:
            port = self.DEFAULT_DASHBOARD_PORT

        try:
            storage = provider.get(IStorage)
            self.resolver.add(port, DashboardController(storage=storage, proxy_settings=self.settings))
            self.__server_binds.add(f"{self.bind}:{port}")
        except CannotResolveTypeException:
            logger.error(
                "Dashboard is enabled but no storage is configured. Dashboard will not be available. Did you forget "
                "to load a storage plugin?"
            )

    def create_hypercorn_config(self):
        """
        Creates a hypercorn config object.

        :return: hypercorn config object
        """
        from hypercorn.config import Config

        config = Config()
        config.bind = [*self.__server_binds]
        config.accesslog = logging.getLogger("hypercorn.access")
        config.errorlog = logging.getLogger("hypercorn.error")
        return config

    async def serve(self):
        """
        Creates and serves the proxy using hypercorn.
        """
        from hypercorn.asyncio import serve

        kernel = await self.create()
        config = self.create_hypercorn_config()

        return await serve(kernel, config)


if __name__ == "__main__":
    proxy = ProxyFactory(dashboard_port=4040)
    proxy.add(8000, "https://httpbin.org/", name="httpbin")
    proxy.load("harp.contrib.sqlalchemy_storage")
    proxy.settings._data["storage"]["url"] = "sqlite+aiosqlite:///custom.db"
    proxy.settings._data["storage"]["drop_tables"] = True
    proxy.settings._data["storage"]["echo"] = False
    asyncio.run(proxy.serve())
