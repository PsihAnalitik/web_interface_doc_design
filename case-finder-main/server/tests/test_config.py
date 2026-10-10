import json

import pytest
from app.config import Settings


def test_settings_support_multiple_basic_auth_users(monkeypatch):
    monkeypatch.setenv("API_USERS", json.dumps({"alice": "one", "bob": "two"}))

    settings = Settings.from_env()

    assert settings.api_users == {"alice": "one", "bob": "two"}


def test_documents_archive_path_is_optional(monkeypatch):
    monkeypatch.delenv("DOCUMENTS_ARCHIVE_PATH", raising=False)
    assert Settings.from_env().documents_archive_path is None
    monkeypatch.setenv("DOCUMENTS_ARCHIVE_PATH", "/app/documents")
    assert Settings.from_env().documents_archive_path.as_posix() == "/app/documents"


def test_settings_reject_invalid_users(monkeypatch):
    monkeypatch.setenv("API_USERS", "[]")

    with pytest.raises(ValueError, match="API_USERS"):
        Settings.from_env()
