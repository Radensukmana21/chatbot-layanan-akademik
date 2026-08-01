from app.core.config import get_settings


def test_auto_retrain_is_disabled_by_default() -> None:
    settings = get_settings()
    assert settings.auto_retrain_enabled is False


def test_default_port_is_9000() -> None:
    settings = get_settings()
    assert settings.app_port == 9000
