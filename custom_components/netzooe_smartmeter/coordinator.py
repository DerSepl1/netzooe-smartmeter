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
            _LOGGER.warning("=== START NETZ OÖ ABFRAGE ===")
            
            login_success = await self.api.login()
            if not login_success:
                _LOGGER.error("=== FEHLER: Login fehlgeschlagen! ===")
                raise UpdateFailed("Login fehlgeschlagen.")

            _LOGGER.warning("=== Login erfolgreich. Hole Zählerprofile... ===")
            profiles = await self.api.get_profiles()
            
            if not profiles or len(profiles) == 0:
                _LOGGER.error(f"=== FEHLER: Keine Profile gefunden! Antwort war: {profiles} ===")
                raise UpdateFailed("Keine Zählerprofile gefunden.")

            # Falls das Portal ein Dictionary statt einer Liste schickt
            if isinstance(profiles, dict) and "data" in profiles:
                profiles = profiles["data"]

            first_profile = profiles[0]
            contract_account = first_profile.get("contractAccountNumber")
            meter_point = first_profile.get("meterPointAdministrationNumber")
            
            _LOGGER.warning(f"=== Zähler gefunden! Vertrag: {contract_account}, Zählpunkt: {meter_point} ===")

            today_str = datetime.now().strftime("%Y-%m-%d")
            _LOGGER.warning(f"=== Hole 15-Min-Werte für {today_str}... ===")
            
            readings = await self.api.get_15min_readings(contract_account, meter_point, today_str)

            if not readings:
                _LOGGER.error("=== FEHLER: Keine Verbrauchsdaten erhalten! ===")
                raise UpdateFailed("Keine Verbrauchsdaten erhalten.")

            _LOGGER.warning("=== DATEN ERFOLGREICH GELADEN ===")
            return readings

        except Exception as err:
            _LOGGER.error(f"=== SYSTEMFEHLER: {err} ===")
            raise UpdateFailed(f"Fehler bei Netz OÖ API: {err}")
