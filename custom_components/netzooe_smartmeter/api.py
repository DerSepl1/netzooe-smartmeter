import logging
import aiohttp
from urllib.parse import unquote

_LOGGER = logging.getLogger(__name__)
BASE_URL = "https://eservice.netzooe.at"

# WICHTIG: Täuscht einen echten Browser vor, um die Cloudflare-Firewall zu passieren
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

class NetzOOeAPI:
    def __init__(self, username, password, session: aiohttp.ClientSession):
        self.username = username
        self.password = password
        self.session = session
        self.xsrf_token = None

    def _extract_token_from_cookies(self):
        """Liest das XSRF-Token geräuschlos aus den Cookies aus, um 401-Fehler zu vermeiden."""
        cookies = self.session.cookie_jar.filter_cookies(BASE_URL)
        if "XSRF-TOKEN" in cookies:
            # Cookies sind oft URL-codiert (z.B. %2D statt -). Das muss zwingend decodiert werden!
            self.xsrf_token = unquote(cookies["XSRF-TOKEN"].value)

    async def _update_csrf_token_api(self):
        """Holt das Token über die API (wird nur NACH dem Login verwendet)."""
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
            "X-Requested-With": "XMLHttpRequest" # Signalisiert dem Server einen modernen Background-Request
        }
        if is_json:
            headers["Content-Type"] = "application/json"
        else:
            headers["Content-Type"] = "application/x-www-form-urlencoded"
            
        if self.xsrf_token:
            headers["X-XSRF-TOKEN"] = self.xsrf_token
        return headers

    async def login(self):
        _LOGGER.debug("Rufe Login-Seite auf für initiale Session-Cookies...")
        
        # 1. Startseite aufrufen (gibt uns unsichtbar die JSESSIONID und das XSRF-TOKEN)
        await self.session.get(f"{BASE_URL}/app/login", headers={"User-Agent": USER_AGENT})
        
        # 2. Token lautlos aus den soeben erhaltenen Cookies extrahieren
        self._extract_token_from_cookies()

        # 3. Login Request senden
        login_url = f"{BASE_URL}/service/j_security_check"
        payload = {
            "j_username": self.username,
            "j_password": self.password
        }
        
        async with self.session.post(login_url, data=payload, headers=self._get_headers(is_json=False)) as response:
            if response.status not in (200, 204, 302):
                _LOGGER.error(f"Login fehlgeschlagen. Status: {response.status}")
                return False
            
        # 4. Nach Login das Token aktualisieren (jetzt erlaubt der Server das auch über die API)
        await self._update_csrf_token_api()
        self._extract_token_from_cookies()
        return True

    async def get_profiles(self):
        url = f"{BASE_URL}/service/v1.0/consumptions/profiles?branch=STROM&activeOnly=true"
        async with self.session.get(url, headers=self._get_headers(is_json=True)) as response:
            if response.status == 401:
                await self._update_csrf_token_api()
                async with self.session.get(url, headers=self._get_headers(is_json=True)) as retry_response:
                    if retry_response.status == 200:
                        return await retry_response.json()
                    return None
            elif response.status == 200:
                return await response.json()
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
