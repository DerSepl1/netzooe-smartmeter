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
        _LOGGER.warning("=== Suche Cookies in der Cookie-Jar ===")
        found = False
        for cookie in self.session.cookie_jar:
            _LOGGER.warning(f"Gefundenes Cookie: {cookie.key}")
            if cookie.key == "XSRF-TOKEN":
                self.xsrf_token = unquote(cookie.value)
                found = True
        
        if found:
            _LOGGER.warning(f"=== XSRF-TOKEN erfolgreich geladen: {self.xsrf_token[:5]}... ===")
        else:
            _LOGGER.error("=== FEHLER: Kein XSRF-TOKEN vom Server erhalten! ===")

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
        _LOGGER.warning("=== START LÖSUNG V4 ===")
        
        # 1. Startseite abrufen (MUSS gelesen werden, damit Cookies gespeichert werden)
        async with self.session.get(f"{BASE_URL}/app/login", headers={"User-Agent": USER_AGENT}) as resp:
            await resp.read()
        
        self._extract_token_from_cookies()

        # 2. Login
        login_url = f"{BASE_URL}/service/j_security_check"
        payload = {
            "j_username": self.username,
            "j_password": self.password
        }
        
        _LOGGER.warning("=== Sende Login-Daten ===")
        async with self.session.post(login_url, data=payload, headers=self._get_headers(is_json=False), allow_redirects=False) as response:
            _LOGGER.warning(f"=== Login HTTP Status: {response.status} ===")
            if response.status in (302, 303):
                loc = response.headers.get("Location", "")
                if "error" in loc:
                    _LOGGER.error("=== FEHLER: Login abgewiesen (Passwort falsch?) ===")
                    return False
        
        self._extract_token_from_cookies()
        return True

    async def get_profiles(self):
        url = f"{BASE_URL}/service/v1.0/consumptions/profiles"
        async with self.session.get(url, headers=self._get_headers(is_json=True)) as response:
            if response.status == 200:
                return await response.json()
            
            # Fallback: Token explizit über API anfordern (falls Cookie-Weg scheitert)
            _LOGGER.warning(f"=== Profilabruf gescheitert ({response.status}). Versuche Token-Refresh über API... ===")
            csrf_url = f"{BASE_URL}/service/v1.0/session/csrf"
            async with self.session.get(csrf_url, headers=self._get_headers(is_json=True)) as csrf_resp:
                if csrf_resp.status == 200:
                    data = await csrf_resp.json()
                    if "token" in data:
                        self.xsrf_token = data["token"]
                        _LOGGER.warning("=== Token über API erneuert. 2. Versuch... ===")
                        
            async with self.session.get(url, headers=self._get_headers(is_json=True)) as retry_resp:
                if retry_resp.status == 200:
                    return await retry_resp.json()
                
                text = await retry_resp.text()
                _LOGGER.error(f"=== ENDGÜLTIGER FEHLER PROFILABRUF: {retry_resp.status} - Antwort: {text} ===")
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
            return None
