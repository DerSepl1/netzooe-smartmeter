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
        # Versuche zuerst, das Token automatisch aus den Cookies von Home Assistant zu lesen
        cookies = self.session.cookie_jar.filter_cookies(BASE_URL)
        if "XSRF-TOKEN" in cookies:
            self.xsrf_token = cookies["XSRF-TOKEN"].value

        # Hole das Token sicherheitshalber auch noch über die API ab
        url = f"{BASE_URL}/service/v1.0/session/csrf"
        headers = self._get_headers()
        
        async with self.session.get(url, headers=headers) as response:
            if response.status == 200:
                data = await response.json()
                self.xsrf_token = data.get("token")
            elif response.status == 401:
                _LOGGER.warning("Token-Endpoint gab 401 zurück, nutze Cookie-Token.")
            else:
                _LOGGER.error(f"Fehler CSRF-Token: {response.status}")

    def _get_headers(self):
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
        # 1. WICHTIG: Zuerst die Login-Seite "besuchen", um die Session-Cookies zu erhalten!
        await self.session.get(f"{BASE_URL}/app/login")
        
        # 2. Jetzt das Token abrufen (funktioniert nun, da wir eine Session haben)
        await self._update_csrf_token()

        # 3. Login Request senden
        login_url = f"{BASE_URL}/service/j_security_check"
        payload = {"j_username": self.username, "j_password": self.password}
        
        async with self.session.post(login_url, json=payload, headers=self._get_headers()) as response:
            if response.status not in (200, 204):
                _LOGGER.error(f"Login fehlgeschlagen. HTTP Status: {response.status}")
                return False
            
        # 4. Nach dem erfolgreichen Login das Token zwingend noch einmal erneuern
        await self._update_csrf_token()
        return True

    async def get_profiles(self):
        url = f"{BASE_URL}/service/v1.0/consumptions/profiles?branch=STROM&activeOnly=true"
        async with self.session.get(url, headers=self._get_headers()) as response:
            if response.status == 401:
                await self._update_csrf_token()
                async with self.session.get(url, headers=self._get_headers()) as retry_response:
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
        
        async with self.session.post(url, json=payload, headers=self._get_headers()) as response:
            if response.status == 200:
                return await response.json()
            return None
