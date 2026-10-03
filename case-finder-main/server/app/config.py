from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Settings:
    openai_api_key: str
    openai_llm_model: str
    openai_embedding_model: str
    top_k: int
    storage_path: Path
    train_cases_path: Path
    train_index_path: Path
    api_users: dict[str, str]
    max_files: int
    max_file_size_bytes: int
    max_total_upload_bytes: int
    max_question_count: int
    openai_timeout_seconds: float

    @classmethod
    def from_env(cls) -> "Settings":
        users_raw = os.getenv("API_USERS")
        if users_raw:
            try:
                users = json.loads(users_raw)
            except json.JSONDecodeError as exc:
                raise ValueError("API_USERS must be a JSON object") from exc
            if (
                not isinstance(users, dict)
                or not users
                or not all(
                    isinstance(key, str) and isinstance(value, str) and key and value
                    for key, value in users.items()
                )
            ):
                raise ValueError("API_USERS must map non-empty usernames to passwords")
        else:
            username = os.getenv("API_USERNAME", "case-finder")
            password = os.getenv("API_PASSWORD", "")
            users = {username: password} if username and password else {}

        return cls(
            openai_api_key=os.getenv("OPENAI_API_KEY", ""),
            openai_llm_model=os.getenv("OPENAI_LLM_MODEL", "gpt-4.1-mini"),
            openai_embedding_model=os.getenv(
                "OPENAI_EMBEDDING_MODEL", "text-embedding-3-small"
            ),
            top_k=_positive_int("CASE_FINDER_TOP_K", 5),
            storage_path=Path(os.getenv("STORAGE_PATH", "/app/storage")),
            train_cases_path=Path(
                os.getenv("TRAIN_CASES_PATH", "/app/data/train/files")
            ),
            train_index_path=Path(
                os.getenv("TRAIN_INDEX_PATH", "/app/data/train/train_index.csv")
            ),
            api_users=users,
            max_files=_positive_int("MAX_FILES", 10),
            max_file_size_bytes=_positive_int("MAX_FILE_SIZE_MB", 20) * 1024 * 1024,
            max_total_upload_bytes=_positive_int("MAX_TOTAL_UPLOAD_SIZE_MB", 100)
            * 1024
            * 1024,
            max_question_count=_positive_int("MAX_QUESTION_COUNT", 50),
            openai_timeout_seconds=float(os.getenv("OPENAI_TIMEOUT_SECONDS", "120")),
        )


def _positive_int(name: str, default: int) -> int:
    value = int(os.getenv(name, str(default)))
    if value < 1:
        raise ValueError(f"{name} must be a positive integer")
    return value
