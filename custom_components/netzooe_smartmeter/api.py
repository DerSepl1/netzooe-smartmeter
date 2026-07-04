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

    def _update_token_from_cookies(self):
        """Sucht nach dem aktuellsten Token in der Cookie-Dose."""
        for cookie in self.session.cookie_jar:
            if cookie.key == "XSRF-TOKEN":
                self.xsrf_token = unquote(cookie.value)

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
        _LOGGER.warning("=== START LÖSUNG V9 (Der echte Erfolg) ===")
        
        # 1. Startseite für die initialen Cookies
        async with self.session.get(f"{BASE_URL}/app/login", headers={"User-Agent": USER_AGENT}) as resp:
            await resp.read()
            
        self._update_token_from_cookies()

        # 2. Login-Daten senden
        login_url = f"{BASE_URL}/service/j_security_check"
        payload = {
            "j_username": self.username,
            "j_password": self.password
        }
        
        _LOGGER.warning("=== Sende Login-Daten... ===")
        # Wir lassen Weiterleitungen (allow_redirects=True) einfach zu und werten den Status nicht mehr künstlich als Fehler.
        async with self.session.post(login_url, data=payload, headers=self._get_headers(is_json=False), allow_redirects=True) as resp:
            await resp.read()
            _LOGGER.warning(f"=== Login-Antwort erhalten (Status {resp.status}) ===")

        # WICHTIG: Nach dem Login rotiert der Server das Token! Wir müssen es neu auslesen.
        self._update_token_from_cookies()

        # 3. VERIFIKATION: Sind wir wirklich drin?
        _LOGGER.warning("=== Prüfe Session-Status... ===")
        session_url = f"{BASE_URL}/service/v1.0/session"
        async with self.session.get(session_url, headers=self._get_headers(is_json=True)) as resp:
            if resp.status == 200:
                _LOGGER.warning("=== Login ERFOLGREICH vom Server bestätigt! ===")
            else:
                text = await resp.text()
                _LOGGER.error(f"=== FEHLER: Login fehlgeschlagen! (Passwort falsch?) Status: {resp.status} - Antwort: {text[:100]} ===")
                return False

        # Token nochmals auf den aktuellsten Stand bringen für die Zählerabfrage
        self._update_token_from_cookies()
        return True

    async def get_profiles(self):
        url = f"{BASE_URL}/service/v1.0/consumptions/profiles?branch=STROM&activeOnly=true"
        async with self.session.get(url, headers=self._get_headers(is_json=True)) as response:
            if response.status == 200:
                _LOGGER.warning("=== ZÄHLERPROFILE ERFOLGREICH GELADEN! ===")
                return await response.json()
            else:
                text = await response.text()
                _LOGGER.error(f"=== FEHLER PROFILABRUF: {response.status} - {text[:200]} ===")
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
