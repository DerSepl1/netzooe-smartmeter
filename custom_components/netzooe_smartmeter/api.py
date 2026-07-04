from __future__ import annotations

import aiohttp

from .const import BASE_URL


class NetzOOEApi:

    def __init__(self, username: str, password: str):
        self._username = username
        self._password = password

        self._session = aiohttp.ClientSession()

        self._csrf = None

        self._contract = None
        self._meterpoint = None

    async def close(self):
        await self._session.close()
