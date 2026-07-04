import logging
import aiohttp
from urllib.parse import unquote
from yarl import URL

_LOGGER = logging.getLogger(__name__)
BASE_URL = "https://eservice.netzooe.at"
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

class NetzOOeAPI:
    def __init__(self, username, password, session: aiohttp.ClientSession):
        self.username = username
        self.password = password
        self.session = session

    def _get_csrf_token(self):
        """Liest das XSRF-Token direkt und immer frisch aus den Cookies."""
        cookies = self.session.cookie_jar.filter_cookies(URL(BASE_URL))
        if "XSRF-TOKEN" in cookies:
            return unquote(cookies["XSRF-TOKEN"].value)
        return ""

    def _get_headers(self, is_json=True):
        """Generiert die Header und nutzt immer das aktuellste Token."""
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

        # Das frische Token wird hier dynamisch eingesetzt
        token = self._get_csrf_token()
        if token:
            headers["X-XSRF-TOKEN"] = token
        return headers

    async def login(self):
        _LOGGER.warning("=== 1. Hole Initiale Cookies ===")
        await self.session.get(f"{BASE_URL}/app/login", headers={"User-Agent": USER_AGENT})

        _LOGGER.warning("=== 2. Sende Login-Daten ===")
        login_url = f"{BASE_URL}/service/j_security_check"
        payload = {
            "j_username": self.username,
            "j_password": self.password
        }

        async with self.session.post(login_url, data=payload, headers=self._get_headers(is_json=False), allow_redirects=False) as response:
            if response.status in (302, 303):
                location = response.headers.get("Location", "")
                if "error" in location or "login" in location:
                    _LOGGER.error("=== FEHLER: Login fehlgeschlagen (Passwort falsch?) ===")
                    return False
            elif response.status == 401:
                _LOGGER.error("=== FEHLER: Login direkt abgewiesen ===")
                return False

        _LOGGER.warning("=== 3. Aktiviere Benutzer-Session (Der fehlende Schritt!) ===")
        # WICHTIG: Das Portal braucht diesen Aufruf zwingend, sonst kommt danach Fehler 401
        session_url = f"{BASE_URL}/service/v1.0/session"
        async with self.session.get(session_url, headers=self._get_headers(is_json=True)) as response:
            if response.status != 200:
                _LOGGER.warning(f"Session-Aktivierung gab Status {response.status} zurück.")

        return True

    async def get_profiles(self):
        url = f"{BASE_URL}/service/v1.0/consumptions/profiles"
        async with self.session.get(url, headers=self._get_headers(is_json=True)) as response:
            if response.status == 200:
                return await response.json()

            raw_error = await response.text()
            _LOGGER.error(f"=== FEHLER: Profil-Abruf 401. Token: {self._get_csrf_token()} - Antwort: {raw_error} ===")
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
                return await response.json()
            raw_error = await response.text()
            _LOGGER.error(f"=== FEHLER: 15-Min-Werte fehlgeschlagen: {raw_error} ===")
            return None
