from __future__ import annotations

import logging
import time

from .case_finder import CaseRepository, OpenAIService
from .config import Settings
from .job_store import JobNotFoundError, JobStore
from .logging_config import configure_logging

logger = logging.getLogger(__name__)


class JobCancelled(Exception):
    pass


class Worker:
    def __init__(
        self,
        settings: Settings,
        store: JobStore | None = None,
        openai_service: OpenAIService | None = None,
        repository: CaseRepository | None = None,
    ):
        self.settings = settings
        self.store = store or JobStore(settings.storage_path)
        self.openai = openai_service or OpenAIService(settings)
        self.repository = repository or CaseRepository(
            settings.train_index_path, settings.train_cases_path
        )

    def _checkpoint(self, process_id: str, status: str, progress: int) -> None:
        if self.store.deletion_requested(process_id):
            raise JobCancelled
        self.store.update_status(process_id, status, progress)

    def process(self, process_id: str) -> None:
        try:
            request = self.store.read_json(process_id, "request.json")
            text = (
                self.store.job_dir(process_id) / "input" / "combined.txt"
            ).read_text(encoding="utf-8")
            count = request["question_count"]
            language = request["language"]

            self._checkpoint(process_id, "generating_baseline", 10)
            baseline = self.openai.questions(text, count, language)
            self.store.write_json(process_id, "baseline_questions.json", baseline)

            self._checkpoint(process_id, "summarizing", 30)
            summary = self.openai.summarize(text)
            (self.store.job_dir(process_id) / "retrieval").mkdir(exist_ok=True)
            (self.store.job_dir(process_id) / "retrieval" / "summary.txt").write_text(
                summary, encoding="utf-8"
            )

            self._checkpoint(process_id, "embedding", 45)
            embedding = self.openai.embed(summary)

            self._checkpoint(process_id, "retrieving", 60)
            candidates = self.repository.nearest(embedding, self.settings.top_k)
            self.store.write_json(
                process_id,
                "retrieval/candidates.json",
                [candidate.__dict__ for candidate in candidates],
            )

            self._checkpoint(process_id, "filtering", 75)
            positions = self.openai.relevant_positions(summary, candidates)
            references, case_ids = self.repository.references(candidates, positions)
            self.store.write_json(
                process_id, "retrieval/relevant_cases.json", {"case_ids": case_ids}
            )

            self._checkpoint(process_id, "generating_enriched", 90)
            enriched = self.openai.questions(text, count, language, references)
            self.store.write_json(process_id, "enriched_questions.json", enriched)
            self._checkpoint(process_id, "completed", 100)
            logger.info("job_completed", extra={"process_id": process_id})
        except JobCancelled:
            self.store.delete_claimed(process_id)
            logger.info("job_deleted", extra={"process_id": process_id})
            return
        except Exception as exc:
            logger.exception("job_failed", extra={"process_id": process_id})
            try:
                if self.store.deletion_requested(process_id):
                    self.store.delete_claimed(process_id)
                    return
                self.store.update_status(
                    process_id,
                    "failed",
                    self.store.read_status(process_id)["progress"],
                    {"code": type(exc).__name__, "message": str(exc)},
                )
            except JobNotFoundError:
                pass
        finally:
            self.store.finish(process_id)

    def run_forever(self, poll_seconds: float = 1.0) -> None:
        self.store.recover_running()
        logger.info("worker_started")
        while True:
            process_id = self.store.claim_next()
            if process_id is None:
                time.sleep(poll_seconds)
                continue
            self.process(process_id)


def main() -> None:
    configure_logging()
    Worker(Settings.from_env()).run_forever()


if __name__ == "__main__":
    main()
