from homeassistant.helpers.update_coordinator import CoordinatorEntity


class NetzOOEEntity(CoordinatorEntity):
    """Basis-Entity für alle Netz OÖ Sensoren."""

    _attr_has_entity_name = True

    def __init__(self, coordinator):
        super().__init__(coordinator)
