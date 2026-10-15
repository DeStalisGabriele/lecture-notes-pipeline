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


def test_a_refused_recording_is_replaced_by_its_whisper_transcript(monkeypatch, tmp_path):
    audio = tmp_path / "EA - Lezione 7 - Parte 1.m4a"
    audio.write_bytes(b"")
    calls = []

    def wait(nb, sid):
        if sid == "audio-id":
            raise notebooklm.NotebookLMError("Source processing failed: audio-id")

    def fake_transcribe(src, dest, model, language):
        dest.write_text("testo", encoding="utf-8")
        return dest

    monkeypatch.setattr(notebooklm, "wait", wait)
    monkeypatch.setattr(notebooklm, "delete", lambda nb, sid: calls.append(("delete", sid)))
    monkeypatch.setattr(notebooklm, "add_file", lambda nb, path, title=None: calls.append(("add", path.name, title)) or "text-id")
    monkeypatch.setattr(cli.transcribe, "transcribe", fake_transcribe)

    class Cfg:
        whisper_model, language = "large-v3", "it"

    assert cli._whisper_instead(Cfg, "nb", "audio-id", audio, tmp_path) == "text-id"
    assert calls == [("delete", "audio-id"), ("add", "whisper - EA - Lezione 7 - Parte 1.txt", audio.name)]
