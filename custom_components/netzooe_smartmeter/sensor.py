from homeassistant.components.sensor import SensorEntity, SensorDeviceClass, SensorStateClass
from homeassistant.const import UnitOfEnergy
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from .const import DOMAIN

async def async_setup_entry(hass, entry, async_add_entities):
    coordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([NetzOOeEnergySensor(coordinator)])

class NetzOOeEnergySensor(CoordinatorEntity, SensorEntity):
    _attr_has_entity_name = True
    _attr_name = "Netz OÖ Tagesverbrauch"
    _attr_device_class = SensorDeviceClass.ENERGY
    _attr_state_class = SensorStateClass.TOTAL_INCREASING
    _attr_native_unit_of_measurement = UnitOfEnergy.KILO_WATT_HOUR

    def __init__(self, coordinator):
        super().__init__(coordinator)
        self._attr_unique_id = f"netzooe_{coordinator.username}_energy_daily"

    @property
    def device_info(self):
        return {
            "identifiers": {(DOMAIN, self.coordinator.username)},
            "name": "Netz OÖ Smart Meter",
            "manufacturer": "Netz Oberösterreich",
        }

    @property
    def native_value(self):
        # Zeigt vorerst 0.0 an, bis wir genau wissen, wie wir die JSON der 15-Min-Werte summieren müssen
        return 0.0
        
    @property
    def extra_state_attributes(self):
        # Speichert die gesamte Original-Antwort von Netz OÖ ab, damit du sie im Home Assistant ansehen kannst!
        return {"raw_data": self.coordinator.data}
