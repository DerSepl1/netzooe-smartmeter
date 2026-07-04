import logging
from datetime import datetime
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.helpers.aiohttp_client import async_get_clientsession

# Hier importieren wir unsere neue API-Klasse
from .api import NetzOOeAPI

_LOGGER = logging.getLogger(__name__)

class NetzOOeDataUpdateCoordinator(DataUpdateCoordinator):
    def __init__(self, hass, username, password):
        """Initialisierung."""
        super().__init__(
            hass,
            _LOGGER,
            name="Netz OÖ Smart Meter",
            # Aktualisierungsintervall, z.B. alle 60 Minuten
            update_interval=timedelta(minutes=60),
        )
        self.username = username
        self.password = password
        
        # Hole die aiohttp session von Home Assistant
        session = async_get_clientsession(hass)
        
        # Initialisiere unsere API
        self.api = NetzOOeAPI(self.username, self.password, session)

    async def _async_update_data(self):
        """Diese Funktion wird von Home Assistant periodisch aufgerufen."""
        try:
            # 1. Login ausführen
            login_success = await self.api.login()
            if not login_success:
                raise UpdateFailed("Login bei Netz OÖ fehlgeschlagen.")

            # 2. Zähler-Profile abrufen
            profiles = await self.api.get_profiles()
            if not profiles or len(profiles) == 0:
                raise UpdateFailed("Keine Zählerprofile gefunden.")

            # Extrahiere die Nummern des ersten Zählers
            first_profile = profiles[0]
            contract_account = first_profile.get("contractAccountNumber")
            meter_point = first_profile.get("meterPointAdministrationNumber")

            # 3. 15-Minuten Werte abrufen (z.B. für den gestrigen oder heutigen Tag)
            # Das Netz OÖ Portal liefert die finalen Daten oft einen Tag verzögert
            today_str = datetime.now().strftime("%Y-%m-%d")
            
            readings = await self.api.get_15min_readings(
                contract_account, 
                meter_point, 
                today_str
            )

            if not readings:
                raise UpdateFailed("Keine Verbrauchsdaten erhalten.")

            # Gib die Daten zurück an Home Assistant (sensor.py greift darauf zu)
            return readings

        except Exception as err:
            raise UpdateFailed(f"Fehler bei der Kommunikation mit Netz OÖ: {err}")
