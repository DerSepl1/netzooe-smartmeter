import logging
import aiohttp
from urllib.parse import unquote

_LOGGER = logging.getLogger(__name__)
BASE_URL = "https://eservice.netzooe.at"
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

class NetzOOeAPI:
    def __init__(self, username, password, session: aiohttp.ClientSession):
        self.username = username
        self.password = password
        self.session = session
        self.xsrf_token = ""

    def _extract_token_from_cookies(self):
        for cookie in self.session.cookie_jar:
            if cookie.key == "XSRF-TOKEN":
                self.xsrf_token = unquote(cookie.value)
                return True
        return False

    def _get_headers(self, is_json=True):
        headers = {
            "User-Agent": USER_AGENT,
            "Accept": "application/json, text/plain, */*",
            "Origin": BASE_URL,
            "Referer": f"{BASE_URL}/app/login",
            "X-Requested-With": "XMLHttpRequest"
        }
        if is_json:
            headers["Content-Type"] = "application/json"
        else:
            headers["Content-Type"] = "application/x-www-form-urlencoded"
            
        if self.xsrf_token:
            headers["X-XSRF-TOKEN"] = self.xsrf_token
        return headers

    async def login(self):
        _LOGGER.warning("=== START LÖSUNG V6 (Der HAR-Pfad) ===")
        
        # 1. Die von dir bewährte Methode: GET /session um das allererste Token zu holen!
        _LOGGER.warning("=== 1. GET /service/v1.0/session (Pre-Login) ===")
        session_url = f"{BASE_URL}/service/v1.0/session"
        async with self.session.get(session_url, headers=self._get_headers(is_json=True)) as resp1:
            await resp1.read()
            _LOGGER.warning(f"Status: {resp1.status}")
        
        self._extract_token_from_cookies()
        
        # Falls das nicht reicht (laut deiner HAR-Datei), rufen wir noch Refresh auf
        if not self.xsrf_token:
            _LOGGER.warning("=== 1b. POST /service/j_security_check/refresh ===")
            refresh_url = f"{BASE_URL}/service/j_security_check/refresh"
            async with self.session.post(refresh_url, headers=self._get_headers(is_json=True)) as rr:
                await rr.read()
            self._extract_token_from_cookies()

        if not self.xsrf_token:
            _LOGGER.error("=== HILFE: Immer noch kein initiales Token. Login wird scheitern! ===")
            return False

        # 2. Login ausführen
        _LOGGER.warning("=== 2. POST /service/j_security_check ===")
        login_url = f"{BASE_URL}/service/j_security_check"
        payload = {
            "j_username": self.username,
            "j_password": self.password
        }
        
        async with self.session.post(login_url, data=payload, headers=self._get_headers(is_json=False), allow_redirects=False) as resp2:
            _LOGGER.warning(f"Status: {resp2.status}")
            loc = resp2.headers.get("Location", "")
            if resp2.status in (302, 303) and "error" in loc:
                _LOGGER.error("=== Login abgewiesen (Passwort falsch?) ===")
                return False

        # 3. NACH dem Login: Post-Login Token Refresh (Das hat dir am Anfang für die Zähler gefehlt!)
        _LOGGER.warning("=== 3. POST /service/j_security_check/refresh ===")
        refresh_url = f"{BASE_URL}/service/j_security_check/refresh"
        async with self.session.post(refresh_url, headers=self._get_headers(is_json=True)) as resp3:
            await resp3.read()

        _LOGGER.warning("=== 4. GET /service/v1.0/session (Post-Login Backend-Aktivierung) ===")
        async with self.session.get(session_url, headers=self._get_headers(is_json=True)) as resp4:
            await resp4.read()

        _LOGGER.warning("=== 5. GET /service/v1.0/session/csrf (Hole frisches Token für Zählerabruf) ===")
        csrf_url = f"{BASE_URL}/service/v1.0/session/csrf"
        async with self.session.get(csrf_url, headers=self._get_headers(is_json=True)) as resp5:
            if resp5.status == 200:
                data = await resp5.json()
                if "token" in data:
                    self.xsrf_token = data["token"]
                    _LOGGER.warning(f"=== NEUES TOKEN ERHALTEN: {self.xsrf_token[:5]}... ===")

        self._extract_token_from_cookies()
        
        if not self.xsrf_token:
            _LOGGER.error("=== Login abgeschlossen, aber das CSRF-Token für den Zählerabruf fehlt! ===")
            return False

        return True

    async def get_profiles(self):
        url = f"{BASE_URL}/service/v1.0/consumptions/profiles?branch=STROM&activeOnly=true"
        async with self.session.get(url, headers=self._get_headers(is_json=True)) as response:
            if response.status == 200:
                _LOGGER.warning("=== ZÄHLERPROFILE ERFOLGREICH GELADEN! ===")
                return await response.json()
            else:
                text = await response.text()
                _LOGGER.error(f"=== FEHLER PROFILABRUF: {response.status} - Antwort: {text} ===")
                return None

    async def get_15min_readings(self, contract_account, meter_point, date_str):
        url = f"{BASE_URL}/service/v1.0/consumptions/profile/active"
        payload = {
            "dimension": "ENERGY",
            "pods": [{
                "contractAccountNumber": contract_account,
                "meterPointAdministrationNumber": meter_point,
                "type": "ACTIVE_CURRENT",
                "timerange": {"from": date_str, "to": date_str},
                "bestAvailableGranularity": "QUARTER_OF_AN_HOUR"
            }]
        }
        
        async with self.session.post(url, json=payload, headers=self._get_headers(is_json=True)) as response:
            if response.status == 200:
                _LOGGER.warning("=== 15-MINUTEN WERTE ERFOLGREICH GELADEN! ===")
                return await response.json()
            return None
