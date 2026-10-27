"""Samsung EHS test helpers."""

from collections.abc import Callable

from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er

type Report = Callable[[str, int, str | None], None]

DOMAIN = "samsungehs"
DEVICE_URL = "socket://192.0.2.1:8888"


def entity_id(
    hass: HomeAssistant, platform: str, key: str, address: str = "200000"
) -> str:
    """Find a real registered entity by its stable unique ID."""
    result = er.async_get(hass).async_get_entity_id(
        platform, DOMAIN, f"{address}_{address}_{key}"
    )
    assert result is not None
    return result
