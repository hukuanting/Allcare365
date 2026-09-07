from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_tracked_settings_do_not_embed_an_oidc_private_key():
    settings_source = (PROJECT_ROOT / "medical_system" / "settings.py").read_text(encoding="utf-8")

    assert "-----BEGIN RSA PRIVATE KEY-----" not in settings_source
    assert "-----BEGIN PRIVATE KEY-----" not in settings_source
