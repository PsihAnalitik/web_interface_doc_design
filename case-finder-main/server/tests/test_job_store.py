from pathlib import Path

import pytest
from app.job_store import JobNotFoundError, JobStore


def create_job(store: JobStore) -> str:
    return store.create_job(
        text="case",
        files=[("notes.md", b"details", "details")],
        combined_text="case\n\ndetails",
        question_count=3,
        language="English",
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


def test_delete_running_job_requests_cancellation(tmp_path: Path):
    store = JobStore(tmp_path)
    process_id = create_job(store)
    store.claim_next()

    assert store.delete(process_id) == "deletion_requested"
    assert store.deletion_requested(process_id)
    assert store.read_status(process_id)["status"] == "deletion_requested"
