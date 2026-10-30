"""Configuração local sem expor ou depender do token real."""

from src import config


def test_reload_local_env_replaces_previous_token(tmp_path, monkeypatch):
    (tmp_path / ".env").write_text("SPTRANS_API_TOKEN=new-test-token\n", encoding="utf-8")
    monkeypatch.setattr(config, "PROJECT_ROOT", tmp_path)
    monkeypatch.setenv("SPTRANS_API_TOKEN", "old-test-token")

    assert config.reload_local_env()
    assert config.get_settings().api_token == "new-test-token"
