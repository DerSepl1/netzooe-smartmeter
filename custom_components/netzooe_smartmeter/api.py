import logging
import aiohttp
from urllib.parse import unquote
from yarl import URL

_LOGGER = logging.getLogger(__name__)
BASE_URL = "https://eservice.netzooe.at"

# WICHTIG: Täuscht einen echten Browser vor
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

class NetzOOeAPI:
    def __init__(self, username, password, session: aiohttp.ClientSession):
        self.username = username
        self.password = password
        self.session = session
        self.xsrf_token = None

    def _extract_token_from_cookies(self):
        cookies = self.session.cookie_jar.filter_cookies(URL(BASE_URL))
        if "XSRF-TOKEN" in cookies:
            self.xsrf_token = unquote(cookies["XSRF-TOKEN"].value)

    async def _update_csrf_token_api(self):
        url = f"{BASE_URL}/service/v1.0/session/csrf"
        async with self.session.get(url, headers=self._get_headers(is_json=True)) as response:
            if response.status == 200:
                data = await response.json()
                self.xsrf_token = data.get("token", self.xsrf_token)

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
        # 1. Startseite aufrufen für Cookies
        await self.session.get(f"{BASE_URL}/app/login", headers={"User-Agent": USER_AGENT})
        self._extract_token_from_cookies()

        # 2. Login-Daten senden
        login_url = f"{BASE_URL}/service/j_security_check"
        payload = {
            "j_username": self.username,
            "j_password": self.password
        }
        
        # WICHTIG: allow_redirects=False zwingt aiohttp, die Antwort des Servers nicht zu überspringen!
        async with self.session.post(login_url, data=payload, headers=self._get_headers(is_json=False), allow_redirects=False) as response:
            if response.status == 302:
                location = response.headers.get("Location", "")
                # Prüfen, ob wir wirklich ins Portal dürfen oder auf die Fehler-Seite abgewiesen wurden
                if "error" in location or "login" in location:
                    _LOGGER.error(f"=== FEHLER: Login vom Netz OÖ Portal abgewiesen! Falsches Passwort oder Bot-Schutz. ===")
                    return False
            elif response.status not in (200, 204, 302):
                _LOGGER.error(f"=== FEHLER: Unerwarteter Login-Status {response.status} ===")
                return False
            
        # 3. Token nach echtem Erfolg erneuern
        await self._update_csrf_token_api()
        self._extract_token_from_cookies()
        return True

    async def get_profiles(self):
        # VarChar42 ruft die Profile ohne die Parameter ab, was oft stabiler ist
        url = f"{BASE_URL}/service/v1.0/consumptions/profiles"
        async with self.session.get(url, headers=self._get_headers(is_json=True)) as response:
            if response.status == 200:
                return await response.json()
            elif response.status == 401:
                # Token abgelaufen, erneuter Versuch
                await self._update_csrf_token_api()
                async with self.session.get(url, headers=self._get_headers(is_json=True)) as retry_response:
                    if retry_response.status == 200:
                        return await retry_response.json()
                    raw_error = await retry_response.text()
                    _LOGGER.error(f"=== FEHLER: Profil-Abruf (Retry) fehlgeschlagen: {retry_response.status} - Server meldet: {raw_error} ===")
                    return None
            else:
                # Gibt den exakten Klartext aus, falls das Portal wieder zickt
                raw_error = await response.text()
                _LOGGER.error(f"=== FEHLER: Profil-Abruf fehlgeschlagen. Status {response.status} - Server meldet: {raw_error} ===")
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
            _LOGGER.error(f"=== FEHLER: 15-Min-Abruf fehlgeschlagen. Status {response.status} - Server meldet: {raw_error} ===")
            return None
