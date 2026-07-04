from datetime import timedelta
import logging

from homeassistant.helpers.update_coordinator import (
    DataUpdateCoordinator,
    UpdateFailed,
)

from .api import NetzOOEApi
from .const import DEFAULT_SCAN_INTERVAL

_LOGGER = logging.getLogger(__name__)


class NetzOOECoordinator(DataUpdateCoordinator):
    """Netz OÖ Coordinator."""

    def __init__(self, hass, username: str, password: str):
        self.api = NetzOOEApi(username, password)

        super().__init__(
            hass,
            _LOGGER,
            name="Netz OÖ",
            update_interval=timedelta(seconds=DEFAULT_SCAN_INTERVAL),
        )

    async def _async_update_data(self):
        try:
            return await self.api.async_update()
        except Exception as err:
            raise UpdateFailed(str(err)) from err
