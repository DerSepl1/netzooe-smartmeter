from homeassistant.components.sensor import SensorEntity

from .const import DOMAIN


async def async_setup_entry(hass, entry, async_add_entities):
    async_add_entities(
        [
            NetzOOETestSensor(),
        ]
    )


class NetzOOETestSensor(SensorEntity):
    _attr_name = "Netz OÖ Test"
    _attr_unique_id = "netzooe_test"

    @property
    def native_value(self):
        return "Integration geladen"
