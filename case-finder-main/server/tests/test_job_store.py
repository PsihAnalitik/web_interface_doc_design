import json
from pathlib import Path

import pytest
from app.job_store import ArchiveError, JobNotFoundError, JobStore


def create_job(store: JobStore) -> str:
    return store.create_job(
        text="case",
        files=[("notes.md", b"details", "details")],
        combined_text="case\n\ndetails",
        question_count=3,
        language="English",
        username="alice",
    )


def test_job_persists_original_parsed_text_and_queue(tmp_path: Path):
    store = JobStore(tmp_path)

    process_id = create_job(store)
    job_dir = store.job_dir(process_id)

    assert (job_dir / "input/original/001.md").read_bytes() == b"details"
    assert (job_dir / "input/parsed/001.txt").read_text() == "details"
    assert store.read_status(process_id)["status"] == "queued"
    assert (store.pending_dir / f"{process_id}.json").exists()


def test_claim_and_recover_running_job(tmp_path: Path):
    store = JobStore(tmp_path)
    process_id = create_job(store)

    assert store.claim_next() == process_id
    assert (store.running_dir / f"{process_id}.json").exists()

    store.recover_running()

    assert (store.pending_dir / f"{process_id}.json").exists()
    assert store.read_status(process_id)["status"] == "queued"


def test_delete_queued_job_removes_everything(tmp_path: Path):
    store = JobStore(tmp_path)
    process_id = create_job(store)

    assert store.delete(process_id) == "deleted"
    assert not (store.jobs_dir / process_id).exists()
    with pytest.raises(JobNotFoundError):
        store.read_status(process_id)


def test_archive_survives_job_deletion(tmp_path: Path):
    archive = tmp_path / "archive"
    store = JobStore(tmp_path / "jobs", archive)
    process_id = create_job(store)

    meta_path = archive / process_id / "meta.json"
    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    assert meta["username"] == "alice"
    assert meta["files"][0]["sha256"]
    assert (archive / process_id / "input" / "original" / "001.md").read_bytes() == b"details"
    assert store.read_json(process_id, "request.json")["username"] == "alice"

    assert store.delete(process_id) == "deleted"
    assert meta_path.exists()
    assert not (store.jobs_dir / process_id).exists()


def test_archive_failure_does_not_enqueue_the_job(tmp_path: Path, monkeypatch):
    archive = tmp_path / "archive"
    store = JobStore(tmp_path / "jobs", archive)

    def deny_copy(*_args, **_kwargs):
        raise PermissionError("denied")

    monkeypatch.setattr("app.job_store.shutil.copytree", deny_copy)

    with pytest.raises(ArchiveError) as caught:
        create_job(store)

    assert caught.value.process_id
    assert list(store.pending_dir.iterdir()) == []
    assert list(store.jobs_dir.iterdir()) == []
    assert list(archive.iterdir()) == []


def test_delete_running_job_requests_cancellation(tmp_path: Path):
    store = JobStore(tmp_path)
    process_id = create_job(store)
    store.claim_next()

    assert store.delete(process_id) == "deletion_requested"
    assert store.deletion_requested(process_id)
    assert store.read_status(process_id)["status"] == "deletion_requested"
