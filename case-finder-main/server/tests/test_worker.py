from pathlib import Path

import numpy as np
from app.case_finder import Candidate
from app.config import Settings
from app.job_store import JobStore
from app.worker import Worker


class FakeOpenAI:
    def questions(self, text, question_count, language, references=None):
        prefix = "enriched" if references is not None else "baseline"
        return [f"{prefix}-{number}-{language}" for number in range(question_count)]

    def summarize(self, text):
        return "summary"

    def embed(self, text):
        return np.asarray([1.0, 0.0])

    def relevant_positions(self, summary, candidates):
        return [1]


class FakeRepository:
    def nearest(self, embedding, top_k):
        return [Candidate("case_a", "summary", 1.0)]

    def references(self, candidates, positions):
        return ("<reference>A</reference>", ["case_a"])


def settings(tmp_path: Path) -> Settings:
    return Settings(
        openai_api_key="test",
        openai_llm_model="test",
        openai_embedding_model="test",
        top_k=5,
        storage_path=tmp_path,
        train_cases_path=tmp_path,
        train_index_path=tmp_path / "index.csv",
        api_users={"user": "password"},
        max_files=10,
        max_file_size_bytes=1024,
        max_total_upload_bytes=2048,
        max_question_count=10,
        openai_timeout_seconds=10,
    )


def test_worker_generates_both_question_sets_and_retrieval_files(tmp_path: Path):
    store = JobStore(tmp_path)
    process_id = store.create_job(
        text="case",
        files=[],
        combined_text="case",
        question_count=2,
        language="Russian",
    )
    assert store.claim_next() == process_id
    worker = Worker(
        settings(tmp_path),
        store=store,
        openai_service=FakeOpenAI(),
        repository=FakeRepository(),
    )

    worker.process(process_id)

    assert store.read_status(process_id)["status"] == "completed"
    assert store.read_json(process_id, "baseline_questions.json") == [
        "baseline-0-Russian",
        "baseline-1-Russian",
    ]
    assert store.read_json(process_id, "enriched_questions.json") == [
        "enriched-0-Russian",
        "enriched-1-Russian",
    ]
    assert store.read_json(process_id, "retrieval/relevant_cases.json") == {
        "case_ids": ["case_a"]
    }
