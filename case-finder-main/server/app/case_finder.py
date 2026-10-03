from __future__ import annotations

import csv
import json
import re
from dataclasses import dataclass
from pathlib import Path

import numpy as np
from openai import OpenAI

from .config import Settings
from .prompts import (
    ENRICHED_QUESTION_SYSTEM_TEMPLATE,
    ENRICHED_QUESTION_USER_TEMPLATE,
    QUESTION_SYSTEM_TEMPLATE,
    QUESTION_USER_TEMPLATE,
    RELEVANCE_SYSTEM_PROMPT,
    RELEVANCE_USER_TEMPLATE,
    SUMMARY_SYSTEM_PROMPT,
    SUMMARY_USER_TEMPLATE,
)


def parse_json_array(raw_text: str) -> list:
    text = raw_text.strip()
    fenced = re.fullmatch(
        r"```(?:json)?\s*(.*?)\s*```", text, re.DOTALL | re.IGNORECASE
    )
    if fenced:
        text = fenced.group(1)
    value = json.loads(text)
    if not isinstance(value, list):
        raise ValueError("The model response must be a JSON array")
    return value


@dataclass(frozen=True)
class Candidate:
    case_id: str
    summary: str
    similarity: float


class OpenAIService:
    def __init__(self, settings: Settings):
        if not settings.openai_api_key:
            raise ValueError("OPENAI_API_KEY is required")
        self.settings = settings
        self.client = OpenAI(
            api_key=settings.openai_api_key,
            timeout=settings.openai_timeout_seconds,
            max_retries=3,
        )

    def _array(self, system_prompt: str, user_prompt: str) -> list:
        response = self.client.responses.create(
            model=self.settings.openai_llm_model,
            instructions=system_prompt,
            input=user_prompt,
        )
        return parse_json_array(response.output_text)

    def summarize(self, text: str) -> str:
        response = self.client.responses.create(
            model=self.settings.openai_llm_model,
            instructions=SUMMARY_SYSTEM_PROMPT,
            input=SUMMARY_USER_TEMPLATE.format(case_text=text),
        )
        summary = " ".join(response.output_text.strip().splitlines())
        if not summary:
            raise ValueError("OpenAI returned an empty summary")
        return summary

    def embed(self, text: str) -> np.ndarray:
        response = self.client.embeddings.create(
            model=self.settings.openai_embedding_model, input=text
        )
        return np.asarray(response.data[0].embedding, dtype=float)

    def questions(
        self,
        text: str,
        question_count: int,
        language: str,
        references: str | None = None,
    ) -> list[str]:
        if references is None:
            system = QUESTION_SYSTEM_TEMPLATE.format(
                question_count=question_count, language=language
            )
            user = QUESTION_USER_TEMPLATE.format(case_text=text)
        else:
            system = ENRICHED_QUESTION_SYSTEM_TEMPLATE.format(
                question_count=question_count, language=language
            )
            user = ENRICHED_QUESTION_USER_TEMPLATE.format(
                case_text=text, reference_cases=references
            )
        questions = self._array(system, user)
        if len(questions) != question_count or not all(
            isinstance(question, str) and question.strip() for question in questions
        ):
            raise ValueError(
                f"OpenAI must return exactly {question_count} non-empty question strings"
            )
        return [question.strip() for question in questions]

    def relevant_positions(
        self, summary: str, candidates: list[Candidate]
    ) -> list[int]:
        payload = "\n\n".join(
            f"Candidate {position}: {candidate.summary}"
            for position, candidate in enumerate(candidates, start=1)
        )
        positions = self._array(
            RELEVANCE_SYSTEM_PROMPT,
            RELEVANCE_USER_TEMPLATE.format(target_summary=summary, candidates=payload),
        )
        valid = set(range(1, len(candidates) + 1))
        if any(
            type(position) is not int or position not in valid for position in positions
        ):
            raise ValueError(
                "The relevance response contains an invalid candidate position"
            )
        return list(dict.fromkeys(positions))


class CaseRepository:
    def __init__(self, index_path: Path, cases_path: Path):
        if not index_path.exists():
            raise FileNotFoundError(f"Training index not found: {index_path}")
        with index_path.open(encoding="utf-8", newline="") as stream:
            rows = list(csv.DictReader(stream))
        if not rows:
            raise ValueError("Training index is empty")
        required = {"id", "summary", "embedding"}
        if not required.issubset(rows[0]):
            raise ValueError(f"Training index must contain columns: {sorted(required)}")
        self.ids = [row["id"] for row in rows]
        self.summaries = [row["summary"] for row in rows]
        vectors = [
            np.asarray(json.loads(row["embedding"]), dtype=float) for row in rows
        ]
        dimensions = {vector.size for vector in vectors if vector.ndim == 1}
        if len(dimensions) != 1 or len(vectors) != len(rows):
            raise ValueError(
                "Training embeddings must be non-empty one-dimensional vectors"
            )
        self.matrix = np.vstack(vectors)
        self.case_paths = {path.stem: path for path in cases_path.glob("*.md")}
        missing = sorted(set(self.ids) - set(self.case_paths))
        if missing:
            raise FileNotFoundError(f"Full training case files are missing: {missing}")

    def nearest(self, query: np.ndarray, top_k: int) -> list[Candidate]:
        if query.ndim != 1 or query.size != self.matrix.shape[1]:
            raise ValueError(
                "Query embedding dimension differs from the training index"
            )
        query_norm = np.linalg.norm(query)
        row_norms = np.linalg.norm(self.matrix, axis=1)
        if query_norm == 0 or np.any(row_norms == 0):
            raise ValueError("Cannot compute cosine similarity for a zero vector")
        scores = (self.matrix @ query) / (row_norms * query_norm)
        positions = np.argsort(scores)[::-1][: min(top_k, len(scores))]
        return [
            Candidate(self.ids[index], self.summaries[index], float(scores[index]))
            for index in positions
        ]

    def references(
        self, candidates: list[Candidate], positions: list[int]
    ) -> tuple[str, list[str]]:
        chosen = [candidates[position - 1] for position in positions]
        sections = []
        for candidate in chosen:
            text = self.case_paths[candidate.case_id].read_text(encoding="utf-8")
            sections.append(
                f"<reference id={json.dumps(candidate.case_id)}>\n{text}\n</reference>"
            )
        return (
            "\n\n".join(sections)
            if sections
            else "No relevant reference cases were found.",
            [candidate.case_id for candidate in chosen],
        )
