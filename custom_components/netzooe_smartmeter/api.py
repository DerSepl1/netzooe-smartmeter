import logging
import aiohttp
from urllib.parse import unquote
import json

_LOGGER = logging.getLogger(__name__)
BASE_URL = "https://eservice.netzooe.at"

class NetzOOeAPI:
    def __init__(self, username, password, session: aiohttp.ClientSession):
        self.username = username
        self.password = password
        self.session = session
        # Wir speichern das Token jetzt als String, wie VarChar42 es macht
        self.xsrf_token = ""

    def _extract_token_from_cookies(self):
        """Versucht, das Token aus der internen Cookie-Jar von aiohttp zu lesen."""
        for cookie in self.session.cookie_jar:
            if cookie.key == "XSRF-TOKEN":
                self.xsrf_token = unquote(cookie.value)
                return True
        return False

    async def _update_csrf_token(self):
        """Holt das Token explizit über die API (VarChar42 Ansatz)."""
        url = f"{BASE_URL}/service/v1.0/session/csrf"
        # Ohne Token anfragen
        headers = {
            "Accept": "application/json, text/plain, */*",
        }
        if self.xsrf_token:
            headers["X-XSRF-TOKEN"] = self.xsrf_token
            
        async with self.session.get(url, headers=headers) as response:
            if response.status == 200:
                data = await response.json()
                if "token" in data:
                    self.xsrf_token = data["token"]

    def _get_headers(self, is_json=True):
        headers = {
            "Accept": "application/json, text/plain, */*",
            "Origin": BASE_URL,
            "Referer": f"{BASE_URL}/app/login",
        }
        if is_json:
            headers["Content-Type"] = "application/json"
        else:
            headers["Content-Type"] = "application/x-www-form-urlencoded"
            
        if self.xsrf_token:
            headers["X-XSRF-TOKEN"] = self.xsrf_token
            
        return headers

    async def login(self):
        _LOGGER.warning("=== VarChar42 Login-Methode Start ===")
        
        # 1. Startseite aufrufen, um die Session-ID (JSESSIONID) zu bekommen
        await self.session.get(f"{BASE_URL}/app/login")
        self._extract_token_from_cookies()
        
        # 2. Token explizit über die API anfordern (wichtiger VarChar42 Schritt)
        await self._update_csrf_token()
        
        if not self.xsrf_token:
             _LOGGER.warning("=== WARNUNG: Immer noch kein Token vor dem Login! ===")

        # 3. Login-Daten senden
        login_url = f"{BASE_URL}/service/j_security_check"
        payload = {
            "j_username": self.username,
            "j_password": self.password
        }
        
        # WICHTIG: allow_redirects=True (Standard), damit wir im Portal landen!
        async with self.session.post(login_url, data=payload, headers=self._get_headers(is_json=False)) as response:
            _LOGGER.warning(f"=== Login-Antwort Status: {response.status} ===")
            
            # Bei einem Fehler (falsches Passwort) landen wir wieder auf der Login-Seite
            final_url = str(response.url)
            if "error" in final_url or "login" in final_url:
                _LOGGER.error("=== FEHLER: Login abgewiesen (Passwort falsch oder Bot-Schutz) ===")
                return False

        # 4. Nach dem erfolgreichen Login MUSS das Token zwingend erneuert werden
        await self._update_csrf_token()
        self._extract_token_from_cookies()
        
        _LOGGER.warning(f"=== Login durch. Neues Token ist: {self.xsrf_token[:5]}... ===")
        return True

    async def get_profiles(self):
        url = f"{BASE_URL}/service/v1.0/consumptions/profiles"
        async with self.session.get(url, headers=self._get_headers(is_json=True)) as response:
            if response.status == 200:
                return await response.json()
            else:
                _LOGGER.error(f"=== FEHLER Profilabruf: Status {response.status} ===")
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
