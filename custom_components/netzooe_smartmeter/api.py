import logging
import aiohttp

_LOGGER = logging.getLogger(__name__)

BASE_URL = "https://eservice.netzooe.at"

class NetzOOeAPI:
    def __init__(self, username, password, session: aiohttp.ClientSession):
        self.username = username
        self.password = password
        self.session = session
        self.xsrf_token = None

    async def _update_csrf_token(self):
        """Holt das aktuelle CSRF-Token vom Server."""
        url = f"{BASE_URL}/service/v1.0/session/csrf"
        headers = {}
        if self.xsrf_token:
            headers["X-XSRF-TOKEN"] = self.xsrf_token
            
        async with self.session.get(url, headers=headers) as response:
            if response.status == 200:
                data = await response.json()
                self.xsrf_token = data.get("token")
                _LOGGER.debug(f"CSRF-Token aktualisiert: {self.xsrf_token}")
            else:
                _LOGGER.error(f"Fehler beim Abrufen des CSRF-Tokens: {response.status}")

    def _get_headers(self):
        """Generiert die Standard-Header inklusive dem rotierenden Token."""
        headers = {
            "Accept": "application/json, text/plain, */*",
            "Content-Type": "application/json",
            "Origin": BASE_URL,
            "Referer": f"{BASE_URL}/app/login",
        }
        if self.xsrf_token:
            headers["X-XSRF-TOKEN"] = self.xsrf_token
        return headers

    async def login(self):
        """Führt den korrekten Login-Ablauf durch."""
        _LOGGER.debug("Starte Login bei Netz OÖ...")
        
        # 1. Initiales Token holen (Sonst schlägt der Login fehl)
        await self._update_csrf_token()

        # 2. Login Request
        login_url = f"{BASE_URL}/service/j_security_check"
        payload = {
            "j_username": self.username,
            "j_password": self.password
        }
        
        async with self.session.post(login_url, json=payload, headers=self._get_headers()) as response:
            if response.status not in (200, 204):
                _LOGGER.error(f"Login fehlgeschlagen. HTTP Status: {response.status}")
                return False
            
        # 3. WICHTIG: Neues Token nach Login holen (Verhindert Fehler 401!)
        await self._update_csrf_token()
        _LOGGER.debug("Login erfolgreich.")
        return True

    async def get_profiles(self):
        """Holt die Vertrags- und Zählpunktdaten."""
        url = f"{BASE_URL}/service/v1.0/consumptions/profiles?branch=STROM&activeOnly=true"
        async with self.session.get(url, headers=self._get_headers()) as response:
            if response.status == 401:
                _LOGGER.warning("401 erhalten, erneuere Token und versuche es erneut...")
                await self._update_csrf_token()
                async with self.session.get(url, headers=self._get_headers()) as retry_response:
                    if retry_response.status == 200:
                        return await retry_response.json()
                    return None
            elif response.status == 200:
                return await response.json()
            else:
                _LOGGER.error(f"Fehler beim Abrufen der Profile: {response.status}")
            return None

    async def get_15min_readings(self, contract_account, meter_point, date_str):
        """Holt die Viertelstundenwerte für einen bestimmten Tag (Format: YYYY-MM-DD)."""
        url = f"{BASE_URL}/service/v1.0/consumptions/profile/active"
        payload = {
            "dimension": "ENERGY",
            "pods": [{
                "contractAccountNumber": contract_account,
                "meterPointAdministrationNumber": meter_point,
                "type": "ACTIVE_CURRENT",
                "timerange": {
                    "from": date_str,
                    "to": date_str
                },
                "bestAvailableGranularity": "QUARTER_OF_AN_HOUR"
            }]
        }
        
        async with self.session.post(url, json=payload, headers=self._get_headers()) as response:
            if response.status == 200:
                return await response.json()
            _LOGGER.error(f"Fehler beim Abruf der 15-Min-Werte: {response.status}")
            return None
