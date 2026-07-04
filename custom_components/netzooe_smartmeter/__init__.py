from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from .const import DOMAIN, CONF_USERNAME, CONF_PASSWORD
from .coordinator import NetzOOeDataUpdateCoordinator

PLATFORMS = ["sensor"]

async def async_setup(hass: HomeAssistant, config: dict):
    # Erstellt den Speicherplatz sicherheitshalber schon beim HA Start
    hass.data.setdefault(DOMAIN, {})
    return True

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry):
    coordinator = NetzOOeDataUpdateCoordinator(
        hass,
        entry.data.get(CONF_USERNAME, ""),
        entry.data.get(CONF_PASSWORD, ""),
    )
    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry):
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)
    return unload_ok
