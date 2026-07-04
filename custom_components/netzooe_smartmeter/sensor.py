from homeassistant.components.sensor import SensorEntity
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN


async def async_setup_entry(
    hass,
    entry,
    async_add_entities,
):
    coordinator = hass.data[DOMAIN][entry.entry_id]

    async_add_entities(
        [
            NetzOOELastValueSensor(coordinator),
            NetzOOELastTimestampSensor(coordinator),
        ]
    )


class NetzOOEBaseSensor(CoordinatorEntity, SensorEntity):

    def __init__(self, coordinator):
        super().__init__(coordinator)


class NetzOOELastValueSensor(NetzOOEBaseSensor):

    _attr_name = "Netz OÖ Letzter Verbrauch"
    _attr_unique_id = "netzooe_last_value"
    _attr_native_unit_of_measurement = "kWh"

    @property
    def native_value(self):

        values = self.coordinator.data.get(
            "profileValues",
            [],
        )

        if not values:
            return None

        return values[-1]["value"]


class NetzOOELastTimestampSensor(NetzOOEBaseSensor):

    _attr_name = "Netz OÖ Letzte Messung"
    _attr_unique_id = "netzooe_last_timestamp"

    @property
    def native_value(self):

        values = self.coordinator.data.get(
            "profileValues",
            [],
        )

        if not values:
            return None

        return values[-1]["datetime"]
