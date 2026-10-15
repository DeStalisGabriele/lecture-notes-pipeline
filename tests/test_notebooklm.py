import pytest

from lecture_notes import cli, notebooklm


def fake_run(output=None, error=None):
    def run(*args, timeout=900):
        if error:
            raise notebooklm.NotebookLMError(error)
        return output
    return run


def test_auth_status_counts_notebooks_when_signed_in(monkeypatch):
    monkeypatch.setattr(notebooklm, "run", fake_run('{"notebooks": [{"id": "a"}, {"id": "b"}]}'))
    assert notebooklm.auth_status() == (True, "Signed in to NotebookLM (2 notebooks).")


def test_auth_status_reports_an_expired_session(monkeypatch):
    monkeypatch.setattr(notebooklm, "run", fake_run(error='{"code": "AUTH_ERROR", "message": "expired"}'))
    ok, message = notebooklm.auth_status()
    assert not ok and "notebooklm login" in message


def test_auth_command_exits_with_1_without_a_config(monkeypatch, capsys):
    monkeypatch.setattr(notebooklm, "run", fake_run(error="Authentication expired or invalid"))
    with pytest.raises(SystemExit) as exit_info:
        cli.main(["--config", "does-not-exist.toml", "auth"])
    assert exit_info.value.code == 1
    assert "expired" in capsys.readouterr().out
