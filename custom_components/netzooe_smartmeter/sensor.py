from homeassistant.components.sensor import SensorEntity

from .const import DOMAIN


async def async_setup_entry(
    hass,
    entry,
    async_add_entities,
):

    coordinator = hass.data[DOMAIN][entry.entry_id]

    async_add_entities(
        [
            NetzOOERawSensor(coordinator),
        ]
    )


class NetzOOERawSensor(SensorEntity):

    _attr_name = "Netz OÖ Rohdaten"

    _attr_unique_id = "netzooe_raw"

    def __init__(self, coordinator):
        self.coordinator = coordinator

    @property
    def native_value(self):

        if self.coordinator.data is None:
            return None

        return len(
            self.coordinator.data.get(
                "profileValues",
                [],
            )
        )

    async def async_update(self):
        await self.coordinator.async_request_refresh()
