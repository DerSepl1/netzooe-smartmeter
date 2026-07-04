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
        self._logged_in = False
        self._xsrf_token = None

        self.contract_account = None
        self.meter_point = None
        self.profile = None

    async def connect(self):
        """Create HTTP session."""
        if self._session is None:
            timeout = aiohttp.ClientTimeout(total=30)
            self._session = aiohttp.ClientSession(timeout=timeout)

    async def close(self):
        """Close HTTP session."""
        if self._session:
            await self._session.close()
            self._session = None

    async def login(self):
        """Login."""

        if self._logged_in:
            return

        await self.connect()

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

        response.raise_for_status()

        await self._session.get(
            f"{BASE_URL}/service/v1.0/session"
        )

        self._logged_in = True

        _LOGGER.info("Login erfolgreich")

    async def load_meter(self):
        """Load first meter."""

        await self.login()

        response = await self._session.get(
            f"{BASE_URL}/service/v1.0/consumptions/profiles?branch=STROM&activeOnly=true"
        )

        response.raise_for_status()

        data = await response.json()

        if len(data) == 0:
            raise RuntimeError("Kein Zählpunkt gefunden")

        self.profile = data[0]

        self.contract_account = self.profile[
            "contractAccountNumber"
        ]

        self.meter_point = self.profile[
            "meterPointAdministrationNumber"
        ]

    async def quarter_values(self):
        """Load 15 minute values."""

        await self.login()

        if self.contract_account is None:
            await self.load_meter()

        today = date.today()
        start = today - timedelta(days=2)

        payload = {
            "dimension": "ENERGY",
            "pods": [
                {
                    "contractAccountNumber": self.contract_account,
                    "meterPointAdministrationNumber": self.meter_point,
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

        data = await response.json()

        if isinstance(data, list):
            if data:
                return data[0]

        return data

    async def async_update(self):
        """Update."""

        return await self.quarter_values()
