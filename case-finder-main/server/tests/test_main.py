from pathlib import Path

from fastapi.testclient import TestClient

from app.config import Settings
from app.main import app, get_settings


def test_start_process_exposes_file_picker_in_openapi():
    schema = app.openapi()

    assert "/start_process" in schema["paths"]
    assert "/upload_info" not in schema["paths"]

    request_body = schema["paths"]["/start_process"]["post"]["requestBody"]
    multipart_schema = request_body["content"]["multipart/form-data"]["schema"]
    form_schema_name = multipart_schema["$ref"].rsplit("/", 1)[-1]
    form_schema = schema["components"]["schemas"][form_schema_name]

    files_schema = form_schema["properties"]["files"]
    assert files_schema["type"] == "array"
    assert files_schema["items"] == {"type": "string", "format": "binary"}
    assert "files" not in form_schema.get("required", [])
    assert "/whoami" in schema["paths"]
    assert "/get_input/{process_id}" in schema["paths"]


def test_job_is_private_input_is_readable_and_archive_survives_delete(tmp_path: Path):
    storage = tmp_path / "storage"
    archive = tmp_path / "archive"
    settings = Settings(
        openai_api_key="test",
        openai_llm_model="test",
        openai_embedding_model="test",
        top_k=5,
        storage_path=storage,
        train_cases_path=tmp_path,
        train_index_path=tmp_path / "index.csv",
        api_users={"alice": "secret", "bob": "other"},
        max_files=10,
        max_file_size_bytes=1024,
        max_total_upload_bytes=2048,
        max_question_count=10,
        openai_timeout_seconds=10,
        documents_archive_path=archive,
    )
    app.dependency_overrides[get_settings] = lambda: settings
    try:
        client = TestClient(app)
        assert client.get("/whoami").status_code == 401
        created = client.post(
            "/start_process",
            data={
                "text": "Классификация обращений",
                "question_count": "2",
                "language": "Russian",
            },
            auth=("alice", "secret"),
        )
        assert created.status_code == 202, created.text
        process_id = created.json()["process_id"]
        assert client.get("/whoami", auth=("alice", "secret")).json() == {
            "username": "alice"
        }
        assert (
            client.get(f"/get_progress/{process_id}", auth=("bob", "other")).status_code
            == 404
        )
        assert (
            client.get(
                f"/get_questions/{process_id}", auth=("bob", "other")
            ).status_code
            == 404
        )
        assert (
            client.get(
                f"/get_progress/{process_id}", auth=("alice", "secret")
            ).status_code
            == 200
        )
        source = client.get(f"/get_input/{process_id}", auth=("alice", "secret"))
        assert source.status_code == 200
        assert "Классификация обращений" in source.json()["text"]
        assert (archive / process_id / "meta.json").exists()
        assert (
            client.delete(f"/delete_job/{process_id}", auth=("bob", "other")).status_code
            == 404
        )
        assert (
            client.delete(
                f"/delete_job/{process_id}", auth=("alice", "secret")
            ).status_code
            == 200
        )
        assert (archive / process_id / "meta.json").exists()
    finally:
        app.dependency_overrides.clear()


def test_archive_failure_returns_json_503(tmp_path: Path, monkeypatch):
    settings = Settings(
        openai_api_key="test",
        openai_llm_model="test",
        openai_embedding_model="test",
        top_k=5,
        storage_path=tmp_path / "storage",
        train_cases_path=tmp_path,
        train_index_path=tmp_path / "index.csv",
        api_users={"alice": "secret"},
        max_files=10,
        max_file_size_bytes=1024,
        max_total_upload_bytes=2048,
        max_question_count=10,
        openai_timeout_seconds=10,
        documents_archive_path=tmp_path / "archive",
    )
    app.dependency_overrides[get_settings] = lambda: settings

    def deny_copy(*_args, **_kwargs):
        raise PermissionError("denied")

    monkeypatch.setattr("app.job_store.shutil.copytree", deny_copy)
    try:
        client = TestClient(app)
        response = client.post(
            "/start_process",
            data={"text": "Классификация обращений", "language": "Russian"},
            auth=("alice", "secret"),
        )
        assert response.status_code == 503
        assert response.json() == {
            "detail": "Не удалось сохранить документы в архив. Обратитесь к администратору."
        }
        assert response.headers["content-type"].startswith("application/json")
    finally:
        app.dependency_overrides.clear()
