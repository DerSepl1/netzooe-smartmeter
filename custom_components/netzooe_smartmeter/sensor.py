from homeassistant.components.sensor import SensorEntity, SensorDeviceClass, SensorStateClass
from homeassistant.const import UnitOfEnergy
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from .const import DOMAIN

async def async_setup_entry(hass, entry, async_add_entities):
    domain_data = hass.data.get(DOMAIN)
    if not domain_data or entry.entry_id not in domain_data:
        return
    
    coordinator = domain_data[entry.entry_id]
    async_add_entities([NetzOOeEnergySensor(coordinator)])

class NetzOOeEnergySensor(CoordinatorEntity, SensorEntity):
    _attr_has_entity_name = True
    _attr_name = "Tagesverbrauch (15-Min-Summe)"
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
        data = self.coordinator.data
        if not data:
            return None
        
        total_kwh = 0.0
        try:
            if isinstance(data, list):
                for pod in data:
                    values = pod.get("profileValues", pod.get("values", []))
                    for entry in values:
                        val = entry.get("value", entry.get("amount", 0.0))
                        total_kwh += float(val)
            elif isinstance(data, dict):
                values = data.get("profileValues", data.get("values", []))
                for entry in values:
                    val = entry.get("value", entry.get("amount", 0.0))
                    total_kwh += float(val)
        except Exception:
            pass
            
        return round(total_kwh, 3)
        
    @property
    def extra_state_attributes(self):
        return {"raw_data": self.coordinator.data}
