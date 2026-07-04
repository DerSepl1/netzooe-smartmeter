from homeassistant.components.sensor import SensorEntity


async def async_setup_entry(hass, entry, async_add_entities):

    async_add_entities(
        [
            NetzOOERawSensor(),
        ]
    )


class NetzOOERawSensor(SensorEntity):

    _attr_name = "Netz OÖ Rohdaten"

    _attr_unique_id = "netzooe_raw"

    @property
    def native_value(self):
        return "API bereit"
