import logging
import aiohttp

_LOGGER = logging.getLogger(__name__)
BASE_URL = "https://eservice.netzooe.at"

class NetzOOeAPI:
    def __init__(self, username, password, session: aiohttp.ClientSession):
        self.username = username.strip()
        self.password = password.strip()
        self.session = session
        self.xsrf_token = ""

    async def login(self):
        _LOGGER.warning("=== START LÖSUNG V16 (Stabilisiert) ===")
        
        # 1. Session-Cookies persistieren
        # WICHTIG: Das Portal braucht zwingend die JSESSIONID aus dem ersten GET
        async with self.session.get(f"{BASE_URL}/app/login") as resp:
            pass

        # 2. CSRF Token abrufen
        async with self.session.get(f"{BASE_URL}/service/v1.0/session/csrf") as resp:
            if resp.status == 200:
                data = await resp.json()
                self.xsrf_token = data.get("token", "")

        # 3. Login mit korrekten Headern
        login_url = f"{BASE_URL}/service/j_security_check"
        payload = {"j_username": self.username, "j_password": self.password}
        
        headers = {
            "X-XSRF-TOKEN": self.xsrf_token,
            "Content-Type": "application/x-www-form-urlencoded",
            "Referer": f"{BASE_URL}/app/login"
        }

        async with self.session.post(login_url, data=payload, headers=headers, allow_redirects=False) as resp:
            if resp.status == 302:
                _LOGGER.warning("=== LOGIN WAR ERFOLGREICH! ===")
            else:
                _LOGGER.error(f"=== FEHLER: Login Status {resp.status} ===")
                return False

        # 4. Token aktualisieren
        async with self.session.get(f"{BASE_URL}/service/v1.0/session/csrf") as resp:
            if resp.status == 200:
                data = await resp.json()
                self.xsrf_token = data.get("token", self.xsrf_token)

        return True

    # ... get_profiles und get_15min_readings bleiben gleich ...

    async def get_profiles(self):
        url = f"{BASE_URL}/service/v1.0/consumptions/profiles?branch=STROM&activeOnly=true"
        headers = {"X-XSRF-TOKEN": self.xsrf_token}
        
        async with self.session.get(url, headers=headers) as resp:
            if resp.status == 200:
                _LOGGER.warning("=== ZÄHLERPROFILE ERFOLGREICH GELADEN! ===")
                return await resp.json()
            else:
                _LOGGER.error(f"=== FEHLER ZÄHLERPROFILE: {resp.status} ===")
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
        headers = {
            "X-XSRF-TOKEN": self.xsrf_token,
            "Content-Type": "application/json"
        }
        
        async with self.session.post(url, json=payload, headers=headers) as resp:
            if resp.status == 200:
                _LOGGER.warning("=== 15-MINUTEN WERTE ERFOLGREICH GELADEN! ===")
                return await resp.json()
            return None
