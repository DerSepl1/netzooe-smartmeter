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
        url = f"{BASE_URL}/service/v1.0/session/csrf"
        headers = {}
        if self.xsrf_token:
            headers["X-XSRF-TOKEN"] = self.xsrf_token
            
        async with self.session.get(url, headers=headers) as response:
            if response.status == 200:
                data = await response.json()
                self.xsrf_token = data.get("token")
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
        await self._update_csrf_token()
        login_url = f"{BASE_URL}/service/j_security_check"
        payload = {"j_username": self.username, "j_password": self.password}
        
        async with self.session.post(login_url, json=payload, headers=self._get_headers()) as response:
            if response.status not in (200, 204):
                return False
            
        await self._update_csrf_token() # WICHTIG: Token nach Login erneuern
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
