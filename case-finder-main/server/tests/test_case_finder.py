import csv
import json
from pathlib import Path

import numpy as np
import pytest
from app.case_finder import CaseRepository, normalize_questions, parse_json_array


def test_parse_json_array_accepts_json_fence():
    assert parse_json_array('```json\n["question"]\n```') == ["question"]


def test_normalize_questions_requires_three_fields():
    raw = [
        {
            "question": " Какие данные? ",
            "understanding": " Не указано. ",
            "importance": " Без них нельзя оценить решение. ",
        }
    ]
    assert normalize_questions(raw, 1) == [
        {
            "question": "Какие данные?",
            "understanding": "Не указано.",
            "importance": "Без них нельзя оценить решение.",
        }
    ]
    with pytest.raises(ValueError, match="question objects"):
        normalize_questions(["Какие данные?"], 1)
    with pytest.raises(ValueError, match="question objects"):
        normalize_questions(
            [{"question": "Какие данные?", "understanding": " ", "importance": "Важно."}],
            1,
        )


def test_parse_json_array_rejects_object():
    with pytest.raises(ValueError, match="JSON array"):
        parse_json_array('{"question": "value"}')


def test_repository_orders_nearest_cases(tmp_path: Path):
    cases = tmp_path / "cases"
    cases.mkdir()
    (cases / "case_a.md").write_text("A", encoding="utf-8")
    (cases / "case_b.md").write_text("B", encoding="utf-8")
    index = tmp_path / "index.csv"
    with index.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=["id", "summary", "embedding"])
        writer.writeheader()
        writer.writerow(
            {"id": "case_a", "summary": "A", "embedding": json.dumps([1, 0])}
        )
        writer.writerow(
            {"id": "case_b", "summary": "B", "embedding": json.dumps([0, 1])}
        )

    repository = CaseRepository(index, cases)
    candidates = repository.nearest(np.asarray([0.9, 0.1]), 2)

    assert [candidate.case_id for candidate in candidates] == ["case_a", "case_b"]


def test_repository_rejects_embedding_dimension_mismatch(tmp_path: Path):
    cases = tmp_path / "cases"
    cases.mkdir()
    (cases / "case_a.md").write_text("A", encoding="utf-8")
    index = tmp_path / "index.csv"
    index.write_text('id,summary,embedding\ncase_a,A,"[1, 0]"\n', encoding="utf-8")
    repository = CaseRepository(index, cases)

    with pytest.raises(ValueError, match="dimension"):
        repository.nearest(np.asarray([1, 0, 0]), 1)
