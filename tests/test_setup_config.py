"""Tests for setup_config wizard."""
from unittest.mock import patch


def test_writes_config_with_openai_key(fake_config, tmp_workdir):
    import sys
    sys.modules.pop("whatsapp_agent.setup_config", None)
    (tmp_workdir / "config.py").unlink()

    from whatsapp_agent import setup_config

    inputs = iter([
        "meutoken",
        "https://mbkchat.com.br",
        "abc123",
        "5511999999999",
        "sk-test123",
    ])
    with patch("builtins.input", lambda *a, **k: next(inputs)):
        rc = setup_config.main()

    assert rc == 0
    content = (tmp_workdir / "config.py").read_text(encoding="utf-8")
    assert "'meutoken'" in content
    assert "'sk-test123'" in content
    assert "OPENAI_API_KEY" in content
    assert "'https://mbkchat.com.br'" in content
    # No more MEGA_* vars
    assert "MEGA_HOST" not in content
    assert "MEGA_INSTANCE" not in content


def test_blank_openai_key_allowed(fake_config, tmp_workdir):
    import sys
    sys.modules.pop("whatsapp_agent.setup_config", None)
    (tmp_workdir / "config.py").unlink()
    from whatsapp_agent import setup_config

    inputs = iter([
        "meutoken",
        "https://mbkchat.com.br",
        "abc123",
        "5511999999999",
        "",
    ])
    with patch("builtins.input", lambda *a, **k: next(inputs)):
        rc = setup_config.main()
    assert rc == 0
    content = (tmp_workdir / "config.py").read_text(encoding="utf-8")
    assert "OPENAI_API_KEY = ''" in content


def test_host_validation_rejects_then_accepts(fake_config, tmp_workdir):
    import sys
    sys.modules.pop("whatsapp_agent.setup_config", None)
    (tmp_workdir / "config.py").unlink()
    from whatsapp_agent import setup_config

    inputs = iter([
        "",                                # cmd_token skip
        "not-a-url",                       # invalid host -> retry
        "https://mbkchat.com.br/",         # trailing slash, valid -> stripped
        "tok-x",
        "5511988888888",
        "",
    ])
    with patch("builtins.input", lambda *a, **k: next(inputs)):
        rc = setup_config.main()
    assert rc == 0
    content = (tmp_workdir / "config.py").read_text(encoding="utf-8")
    assert "'https://mbkchat.com.br'" in content
    assert "mbkchat.com.br/'" not in content  # trailing slash stripped


def test_no_instance_field_in_generated_config(fake_config, tmp_workdir):
    import sys
    sys.modules.pop("whatsapp_agent.setup_config", None)
    (tmp_workdir / "config.py").unlink()
    from whatsapp_agent import setup_config

    inputs = iter([
        "",
        "https://mbkchat.com.br",
        "meu-token-123",
        "5511999999999",
        "",
    ])
    with patch("builtins.input", lambda *a, **k: next(inputs)):
        rc = setup_config.main()
    assert rc == 0
    content = (tmp_workdir / "config.py").read_text(encoding="utf-8")
    assert "instance" not in content.lower()
    assert "API_HOST" in content
    assert "API_TOKEN" in content
