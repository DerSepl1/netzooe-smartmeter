from __future__ import annotations

import logging
from datetime import date, timedelta

import aiohttp

from .const import BASE_URL

_LOGGER = logging.getLogger(__name__)


class NetzOOEApi:
    """Netz OÖ API."""

    def __init__(self, username: str, password: str):
        self._username = username
        self._password = password

        self._session: aiohttp.ClientSession | None = None

        self.contract_account = None
        self.meter_point = None

    async def connect(self):
        if self._session is None:
            self._session = aiohttp.ClientSession()

    async def close(self):
        if self._session:
            await self._session.close()

    async def login(self):

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

        return True

    async def load_meter(self):

        response = await self._session.get(
            f"{BASE_URL}/service/v1.0/consumptions/profiles?branch=STROM&activeOnly=true"
        )

        response.raise_for_status()

        data = await response.json()

        if not data:
            raise RuntimeError("Kein Zählpunkt gefunden.")

        meter = data[0]

        self.contract_account = meter["contractAccountNumber"]
        self.meter_point = meter["meterPointAdministrationNumber"]

        _LOGGER.info(
            "Gefundener Zählpunkt %s",
            self.meter_point,
        )

        return meter

    async def quarter_values(self):

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

        return await response.json()

    async def async_update(self):

        await self.login()

        if self.contract_account is None:
            await self.load_meter()

        data = await self.quarter_values()

        if isinstance(data, list):

            if len(data):

                return data[0]

        return data
