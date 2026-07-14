from app.core.config import get_settings


def create_secret_key() -> str:
    """Create a fallback secret key for local development."""
    return get_settings().secret_key
