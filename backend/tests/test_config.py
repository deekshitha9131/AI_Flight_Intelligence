import importlib

import app.core.config as config_module


def test_get_settings_uses_safe_defaults_when_env_missing(monkeypatch) -> None:
    monkeypatch.setenv("APP_NAME", " ")
    monkeypatch.setenv("APP_VERSION", " ")
    monkeypatch.setenv("ENVIRONMENT", " ")
    monkeypatch.setenv("DATABASE_URL", " ")
    monkeypatch.setenv("SECRET_KEY", " ")
    monkeypatch.setenv("JWT_ALGORITHM", " ")
    monkeypatch.setenv("ACCESS_TOKEN_EXPIRE_MINUTES", " ")

    importlib.reload(config_module)
    settings = config_module.get_settings(reload=True)

    assert settings.app_name == "AI Flight Intelligence"
    assert settings.database_url == "sqlite:///./app.db"
    assert settings.secret_key.startswith("change-me")
    assert "http://localhost:5173" in settings.cors_origins_list
