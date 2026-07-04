from datetime import timedelta

from homeassistant.helpers.update_coordinator import (
    DataUpdateCoordinator,
    UpdateFailed,
)

from .const import DEFAULT_SCAN_INTERVAL


class NetzOOECoordinator(DataUpdateCoordinator):
    """Netz OÖ Data Coordinator."""

    def __init__(self, hass, api):
        super().__init__(
            hass,
            logger=__import__("logging").getLogger(__name__),
            name="NetzOOE",
            update_interval=timedelta(seconds=DEFAULT_SCAN_INTERVAL),
        )

        self.api = api

    async def _async_update_data(self):
        try:
            return await self.api.async_update()
        except Exception as err:
            raise UpdateFailed(err) from err
