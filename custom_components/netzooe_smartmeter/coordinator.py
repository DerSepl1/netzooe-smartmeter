import logging
from datetime import datetime, timedelta
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from .api import NetzOOeAPI

_LOGGER = logging.getLogger(__name__)

class NetzOOeDataUpdateCoordinator(DataUpdateCoordinator):
    def __init__(self, hass, username, password):
        super().__init__(
            hass,
            _LOGGER,
            name="Netz OÖ Smart Meter",
            update_interval=timedelta(minutes=60),
        )
        self.username = username
        self.password = password
        session = async_get_clientsession(hass)
        self.api = NetzOOeAPI(self.username, self.password, session)

    async def _async_update_data(self):
        try:
            login_success = await self.api.login()
            if not login_success:
                raise UpdateFailed("Login bei Netz OÖ fehlgeschlagen.")

            profiles = await self.api.get_profiles()
            if not profiles or len(profiles) == 0:
                raise UpdateFailed("Keine Zählerprofile gefunden.")

            first_profile = profiles[0]
            contract_account = first_profile.get("contractAccountNumber")
            meter_point = first_profile.get("meterPointAdministrationNumber")

            today_str = datetime.now().strftime("%Y-%m-%d")
            
            readings = await self.api.get_15min_readings(contract_account, meter_point, today_str)

            if not readings:
                raise UpdateFailed("Keine Verbrauchsdaten erhalten.")

            return readings
        except Exception as err:
            raise UpdateFailed(f"Fehler bei Netz OÖ API: {err}")
