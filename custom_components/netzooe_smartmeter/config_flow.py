import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import HomeAssistant

# Importiere deine DOMAIN aus der const.py
from .const import DOMAIN 

# WICHTIG: Das 'domain=DOMAIN' am Ende der Zeile darf nicht fehlen!
class NetzOOeConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Netz OÖ Smart Meter."""

    VERSION = 1

    async def async_step_user(self, user_input=None):
        """Handle the initial step."""
        errors = {}

        if user_input is not None:
            # Hier passiert später dein Login-Test
            # Wenn alles klappt:
            return self.async_create_entry(title="Netz OÖ", data=user_input)

        # Das Formular, das in Home Assistant angezeigt wird
        data_schema = vol.Schema({
            vol.Required("username"): str,
            vol.Required("password"): str,
        })

        return self.async_show_form(
            step_id="user", data_schema=data_schema, errors=errors
        )
