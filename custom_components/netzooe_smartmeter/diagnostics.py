from __future__ import annotations

from homeassistant.config_entries import ConfigEntry


async def async_get_config_entry_diagnostics(hass, entry: ConfigEntry):
    return {
        "entry": {
            "title": entry.title,
            "data": {
                "username": "***"
            },
        }
    }
