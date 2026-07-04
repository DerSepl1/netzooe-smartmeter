class NetzOOEError(Exception):
    """Basisfehler."""


class CannotConnect(NetzOOEError):
    """Keine Verbindung."""


class InvalidAuth(NetzOOEError):
    """Ungültige Zugangsdaten."""
