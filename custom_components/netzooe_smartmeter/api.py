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
        # 1. Token sicher aus den Cookies lesen (Beste Methode bei Netz OÖ)
        cookies = self.session.cookie_jar.filter_cookies(BASE_URL)
        if "XSRF-TOKEN" in cookies:
            self.xsrf_token = cookies["XSRF-TOKEN"].value

        # 2. Token über die API prüfen (Ignoriert 401 vor dem Login lautlos)
        url = f"{BASE_URL}/service/v1.0/session/csrf"
        headers = {
            "Accept": "application/json, text/plain, */*",
            "Origin": BASE_URL,
            "Referer": f"{BASE_URL}/app/login",
        }
        if self.xsrf_token:
            headers["X-XSRF-TOKEN"] = self.xsrf_token
            
        async with self.session.get(url, headers=headers) as response:
            if response.status == 200:
                data = await response.json()
                self.xsrf_token = data.get("token", self.xsrf_token)

    def _get_headers(self, is_json=True):
        headers = {
            "Accept": "application/json, text/plain, */*",
            "Origin": BASE_URL,
            "Referer": f"{BASE_URL}/app/login",
        }
        # Unterscheidung zwischen API-Requests (JSON) und dem Login-Request (Formular)
        if is_json:
            headers["Content-Type"] = "application/json"
        else:
            headers["Content-Type"] = "application/x-www-form-urlencoded"
            
        if self.xsrf_token:
            headers["X-XSRF-TOKEN"] = self.xsrf_token
        return headers

    async def login(self):
        # 1. Login-Seite aufrufen, um Session-Cookies zu generieren
        await self.session.get(f"{BASE_URL}/app/login")
        await self._update_csrf_token()

        # 2. Login-Daten senden (WICHTIG: Als Form-Data, nicht als JSON!)
        login_url = f"{BASE_URL}/service/j_security_check"
        payload = {
            "j_username": self.username,
            "j_password": self.password
        }
        
        # 'data=payload' anstelle von 'json=payload' macht hier den Unterschied
        async with self.session.post(login_url, data=payload, headers=self._get_headers(is_json=False)) as response:
            if response.status not in (200, 204, 302):
                _LOGGER.error(f"Login fehlgeschlagen! Status: {response.status}")
                return False
            
        # 3. Token nach erfolgreichem Login aktualisieren
        await self._update_csrf_token()
        return True

    async def get_profiles(self):
        url = f"{BASE_URL}/service/v1.0/consumptions/profiles?branch=STROM&activeOnly=true"
        async with self.session.get(url, headers=self._get_headers(is_json=True)) as response:
            if response.status == 401:
                await self._update_csrf_token()
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
