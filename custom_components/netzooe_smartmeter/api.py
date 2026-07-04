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

    async def _fetch_csrf_token(self, phase=""):
        """Holt das Token zwingend über den API-Endpunkt, da Cookies hier nicht ausreichen."""
        url = f"{BASE_URL}/service/v1.0/session/csrf"
        headers = {
            "User-Agent": USER_AGENT,
            "Accept": "application/json, text/plain, */*",
            "Origin": BASE_URL,
            "Referer": f"{BASE_URL}/app/login",
            "X-Requested-With": "XMLHttpRequest"
        }
        if self.xsrf_token:
            headers["X-XSRF-TOKEN"] = self.xsrf_token

        try:
            async with self.session.get(url, headers=headers) as response:
                if response.status == 200:
                    data = await response.json()
                    if "token" in data:
                        self.xsrf_token = data["token"]
                        _LOGGER.warning(f"=== [{phase}] CSRF-Token via API erhalten: {self.xsrf_token[:5]}... ===")
                        return
        except Exception as e:
            _LOGGER.error(f"Fehler beim Token-Abruf: {e}")

        # Fallback auf Cookies, falls die API zickt
        for cookie in self.session.cookie_jar:
            if cookie.key == "XSRF-TOKEN":
                self.xsrf_token = unquote(cookie.value)
                _LOGGER.warning(f"=== [{phase}] CSRF-Token via Cookie erhalten: {self.xsrf_token[:5]}... ===")
                return
                
        _LOGGER.error(f"=== [{phase}] FEHLER: Konnte absolut kein CSRF-Token erhalten! ===")

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
        _LOGGER.warning("=== START LÖSUNG V5 ===")
        
        # 1. Startseite abrufen (JSESSIONID generieren lassen)
        async with self.session.get(f"{BASE_URL}/app/login", headers={"User-Agent": USER_AGENT}) as resp:
            await resp.read()
        
        # 2. WICHTIG: Token noch VOR dem Login generieren lassen
        await self._fetch_csrf_token(phase="PRE-LOGIN")

        if not self.xsrf_token:
            _LOGGER.error("=== ABBRUCH: Ohne initiales Token wird der Login zu 100% scheitern! ===")
            return False

        # 3. Login ausführen
        login_url = f"{BASE_URL}/service/j_security_check"
        payload = {
            "j_username": self.username,
            "j_password": self.password
        }
        
        _LOGGER.warning("=== Sende Login-Daten inkl. Token ===")
        async with self.session.post(login_url, data=payload, headers=self._get_headers(is_json=False), allow_redirects=False) as response:
            _LOGGER.warning(f"=== Login HTTP Status: {response.status} ===")
            if response.status == 302:
                loc = response.headers.get("Location", "")
                _LOGGER.warning(f"=== Login leitet weiter nach: {loc} ===")
                if "error" in loc:
                    _LOGGER.error("=== FEHLER: Login abgewiesen (Passwort falsch?) ===")
                    return False
        
        # 4. Token NACH dem Login zwingend erneuern (Spring Security rotiert das Token hier!)
        await self._fetch_csrf_token(phase="POST-LOGIN")

        # 5. Benutzer-Session im Backend aktivieren
        session_url = f"{BASE_URL}/service/v1.0/session"
        async with self.session.get(session_url, headers=self._get_headers(is_json=True)) as resp:
            _LOGGER.warning(f"=== Session Aktivierung HTTP Status: {resp.status} ===")

        return True

    async def get_profiles(self):
        url = f"{BASE_URL}/service/v1.0/consumptions/profiles"
        async with self.session.get(url, headers=self._get_headers(is_json=True)) as response:
            if response.status == 200:
                _LOGGER.warning("=== Profile erfolgreich geladen! ===")
                return await response.json()
            
            text = await response.text()
            _LOGGER.error(f"=== ENDGÜLTIGER FEHLER PROFILABRUF: {response.status} - Antwort: {text} ===")
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
                _LOGGER.warning("=== 15-Minuten-Werte erfolgreich geladen! ===")
                return await response.json()
            return None
