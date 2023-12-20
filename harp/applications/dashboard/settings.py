from typing import Literal, Optional

from harp.core.settings import BaseSetting, DisabledSettings, FromFileSetting, settings_dataclass
from harp.errors import ProxyConfigurationError


@settings_dataclass
class DashboardAuthBasicSettings(BaseSetting):
    type: str = "basic"
    passwd: Optional[FromFileSetting | dict[str, str]] = None

    def __post_init__(self):
        FromFileSetting.may_override(self, "passwd")


@settings_dataclass
class DashboardAuthSettings:
    type: Optional[Literal["basic"] | None] = None

    def __new__(cls, **kwargs):
        _type = kwargs.pop("type", None)
        available_types = ("basic",)

        if _type is None or not _type:
            if len(kwargs) > 0:
                raise ProxyConfigurationError(
                    "Invalid configuration for dashboard auth. There should not be additional arguments if no auth "
                    f"type is provided. Available types: {', '.join(available_types)}."
                )
            return None

        if _type == "basic":
            return DashboardAuthBasicSettings(**kwargs)

        raise ProxyConfigurationError(
            f"Invalid dashboard auth type: {_type}. Available types: {', '.join(available_types)}."
        )


@settings_dataclass
class DashboardSettings:
    enabled = True
    port: int | str = 4080
    auth: Optional[DashboardAuthSettings] = None

    def __new__(cls, **kwargs):
        # todo generic management of disablable settings
        _enabled = kwargs.pop("enabled", True)
        # todo better parsing of falsy values
        if isinstance(_enabled, str) and _enabled.lower() in {"no", "false", "0"}:
            _enabled = False
        if not _enabled:
            return DisabledSettings()

        return super().__new__(cls)

    def __post_init__(self):
        if isinstance(self.auth, str):
            raise ProxyConfigurationError(
                "Invalid configuration for dashboard auth: string configuration is not supported anymore."
            )

        if isinstance(self.auth, dict):
            object.__setattr__(self, "auth", DashboardAuthSettings(**self.auth))
