from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import (
    DOMAIN,
    CONF_USERNAME,
    CONF_PASSWORD,
)
from .coordinator import NetzOOECoordinator

PLATFORMS = ["sensor"]


async def async_setup(hass: HomeAssistant, config):
    return True


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
):

    coordinator = NetzOOECoordinator(
        hass,
        entry.data[CONF_USERNAME],
        entry.data[CONF_PASSWORD],
    )

    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = coordinator

    await hass.config_entries.async_forward_entry_setups(
        entry,
        PLATFORMS,
    )

    return True


async def async_unload_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
):

    await hass.config_entries.async_unload_platforms(
        entry,
        PLATFORMS,
    )

    return True
