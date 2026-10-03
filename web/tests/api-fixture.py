"""Real FastAPI + Worker, with the server's existing test doubles for OpenAI/retrieval."""
import os
import sys
import threading
from pathlib import Path

import uvicorn

root = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(root / "case-finder-main" / "server"))
sys.path.insert(0, str(root / "case-finder-main" / "server" / "tests"))

from app.config import Settings
from app.job_store import JobStore
from app.main import app, get_settings
from app.worker import Worker
from test_worker import FakeOpenAI, FakeRepository


if __name__ == "__main__":
    storage = Path(os.environ["STORAGE_PATH"]).resolve()
    if not storage.is_relative_to(root / ".agent"):
        raise ValueError("Fixture storage must be inside this project's .agent directory")
    settings = Settings.from_env()
    app.dependency_overrides[get_settings] = lambda: settings
    worker = Worker(settings, store=JobStore(storage), openai_service=FakeOpenAI(), repository=FakeRepository())
    threading.Thread(target=worker.run_forever, kwargs={"poll_seconds": 0.05}, daemon=True).start()
    uvicorn.run(app, host="127.0.0.1", port=int(os.environ.get("FIXTURE_PORT", "0")))
