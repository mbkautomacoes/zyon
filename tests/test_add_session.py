"""Tests for add_session wizard."""
import sys
from unittest.mock import patch


def _seed(tmp_workdir, sessions_block):
    cfg = f'''CMD_TOKEN = "tok"
SIGNATURE = "*Claude Code*"
API_HOST = "https://mbkchat.com.br"
SESSIONS = {{
{sessions_block}
}}
ALLOWED_PHONE = "111"
ALLOWED_LID = ""
API_TOKEN = "t1"
OPENAI_API_KEY = ""
'''
    (tmp_workdir / "config.py").write_text(cfg, encoding="utf-8")


def test_appends_second_session(fake_config, tmp_workdir):
    sys.modules.pop("whatsapp_agent.add_session", None)
    _seed(tmp_workdir, '    "1": {"token": "t1", "phone": "111", "lid": ""},')
    from whatsapp_agent import add_session

    inputs = iter(["tok2", "5511888888888"])
    with patch("builtins.input", lambda *a, **k: next(inputs)):
        rc = add_session.main()

    assert rc == 0
    content = (tmp_workdir / "config.py").read_text(encoding="utf-8")
    assert '"2":' in content
    assert "5511888888888" in content
    assert '"1":' in content


def test_picks_next_free_id(fake_config, tmp_workdir):
    sys.modules.pop("whatsapp_agent.add_session", None)
    _seed(tmp_workdir,
          '    "1": {"token": "t1", "phone": "111", "lid": ""},\n'
          '    "2": {"token": "t2", "phone": "222", "lid": ""},')
    from whatsapp_agent import add_session

    inputs = iter(["t3", "5511777777777"])
    with patch("builtins.input", lambda *a, **k: next(inputs)):
        rc = add_session.main()
    assert rc == 0
    content = (tmp_workdir / "config.py").read_text(encoding="utf-8")
    assert '"3":' in content
