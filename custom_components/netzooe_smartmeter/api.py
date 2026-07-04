from __future__ import annotations

import logging
from datetime import date, timedelta

import aiohttp

from .const import BASE_URL

_LOGGER = logging.getLogger(__name__)


class NetzOOEApi:
    """API Client für Netz OÖ."""

    def __init__(self, username: str, password: str):
        self._username = username
        self._password = password

        self._session: aiohttp.ClientSession | None = None

        self._contract_account = None
        self._meter_point = None

    async def connect(self):
        if self._session is None:
            self._session = aiohttp.ClientSession()

    async def close(self):
        if self._session:
            await self._session.close()
            self._session = None

    async def login(self) -> bool:
        """Login ins Netz OÖ Portal."""

        await self.connect()

        # Session initialisieren
        await self._session.get(
            f"{BASE_URL}/service/v1.0/session"
        )

        payload = {
            "j_username": self._username,
            "j_password": self._password,
        }

        response = await self._session.post(
            f"{BASE_URL}/service/j_security_check",
            json=payload,
        )

        if response.status != 200:
            _LOGGER.error("Login fehlgeschlagen (%s)", response.status)
            return False

        _LOGGER.info("Login erfolgreich")

        return True

    async def set_meter(
        self,
        contract_account: str,
        meter_point: str,
    ):
        self._contract_account = contract_account
        self._meter_point = meter_point

    async def quarter_values(self):
        """15-Minuten-Werte laden."""

        today = date.today()
        start = today - timedelta(days=2)

        payload = {
            "dimension": "ENERGY",
            "pods": [
                {
                    "contractAccountNumber": self._contract_account,
                    "meterPointAdministrationNumber": self._meter_point,
                    "type": "ACTIVE_CURRENT",
                    "timerange": {
                        "from": start.isoformat(),
                        "to": today.isoformat(),
                    },
                    "bestAvailableGranularity": "QUARTER_OF_AN_HOUR",
                }
            ],
        }

        response = await self._session.post(
            f"{BASE_URL}/service/v1.0/consumptions/profile/active",
            json=payload,
        )

        response.raise_for_status()

        return await response.json()
