import csv
import json
from datetime import datetime

import pytest

from data.repositories.file_result_repository import FileResultRepository
from domain.entities.evaluation_result import EvaluationResult
from domain.entities.question import Question
from domain.entities.question_score import QuestionScore
from domain.errors import ResultExportError
from domain.scoring.token_f1_scoring_method import TokenF1ScoringMethod


@pytest.fixture
def result():
    scores = (
        QuestionScore(Question("1", "Capital?", "Brasília"), "Brasília, claro", 0.9, 1.5),
        QuestionScore(Question("2", "Autor?", "Machado"), "Não sei", 0.1, 0.5),
    )
    return EvaluationResult(scores, datetime(2026, 10, 28, 12, 0, 0), TokenF1ScoringMethod())


def test_writes_json(tmp_path, result):
    destination = tmp_path / "out.json"

    FileResultRepository().save(result, destination)

    document = json.loads(destination.read_text(encoding="utf-8"))
    assert document["method"] == "token_f1"
    assert document["method_name"] == "Token F1"
    assert document["average_score"] == pytest.approx(0.5)
    assert document["evaluated_at"] == "2026-10-28T12:00:00"
    assert document["scores"][0]["given_answer"] == "Brasília, claro"
    assert document["scores"][0]["score"] == 0.9
    assert document["scores"][0]["response_seconds"] == 1.5
    assert document["metrics"]["highest_score_question_id"] == "1"
    assert document["metrics"]["lowest_score_question_id"] == "2"
    assert document["metrics"]["corpus_score"] is None
    assert document["metrics"]["average_response_seconds"] == pytest.approx(1.0)


def test_writes_csv_readable_with_accents(tmp_path, result):
    destination = tmp_path / "out.csv"

    FileResultRepository().save(result, destination)

    with destination.open(encoding="utf-8-sig", newline="") as source:
        rows = list(csv.DictReader(source))
    assert [row["expected_answer"] for row in rows] == ["Brasília", "Machado"]
    assert [row["method"] for row in rows] == ["token_f1", "token_f1"]
    assert rows[1]["score"] == "0.1"
    assert rows[1]["response_seconds"] == "0.5"


def test_rejects_unsupported_suffix(tmp_path, result):
    with pytest.raises(ResultExportError, match="Unsupported file format"):
        FileResultRepository().save(result, tmp_path / "out.txt")


def test_reports_unwritable_destination(tmp_path, result):
    with pytest.raises(ResultExportError):
        FileResultRepository().save(result, tmp_path / "missing" / "out.json")


def test_json_includes_method_parameters(tmp_path, result):
    destination = tmp_path / "out.json"

    FileResultRepository().save(result, destination)

    document = json.loads(destination.read_text(encoding="utf-8"))
    assert document["method_parameters"] == result.method.parameters


def build_rag_result():
    from datetime import datetime

    from domain.entities.evaluation_result import EvaluationResult
    from domain.entities.retrieved_context import RetrievedContext
    from domain.scoring.token_f1_scoring_method import TokenF1ScoringMethod

    contexts = (RetrievedContext("doc-1", "Brasília é a capital.", 0.9), RetrievedContext(None, "outro"))
    scores = (
        QuestionScore(Question("1", "Capital?", "Brasília", ("doc-1",)), "Brasília", 1.0, 1.0, contexts),
        QuestionScore(Question("2", "Autor?", "Machado", ("doc-9",)), "Não sei", 0.0, 2.0, ()),
    )
    return EvaluationResult(scores, datetime(2026, 11, 24, 10, 0, 0), TokenF1ScoringMethod())


def test_json_includes_contexts_and_companion_scores(tmp_path):
    destination = tmp_path / "rag.json"

    FileResultRepository().save(build_rag_result(), destination, {"hit_rate": (1.0, 0.0)})

    document = json.loads(destination.read_text(encoding="utf-8"))
    assert document["scores"][0]["contexts"][0] == {"id": "doc-1", "text": "Brasília é a capital.", "score": 0.9}
    assert document["scores"][1]["contexts"] == []
    assert document["scores"][1]["companion_scores"] == {"hit_rate": 0.0}
    assert document["companion_averages"] == {"hit_rate": 0.5}


def test_csv_adds_context_and_companion_columns(tmp_path):
    destination = tmp_path / "rag.csv"

    FileResultRepository().save(build_rag_result(), destination, {"hit_rate": (1.0, 0.0)})

    with destination.open(encoding="utf-8-sig", newline="") as source:
        rows = list(csv.DictReader(source))
    assert [row["context_count"] for row in rows] == ["2", "0"]
    assert rows[0]["context_ids"] == "doc-1 | ?"
    assert [row["hit_rate"] for row in rows] == ["1.0", "0.0"]


def test_results_without_contexts_keep_the_old_csv_columns(tmp_path, result):
    destination = tmp_path / "out.csv"

    FileResultRepository().save(result, destination)

    header = destination.read_text(encoding="utf-8-sig").splitlines()[0]
    assert header == "id,question,expected_answer,given_answer,method,score,response_seconds"
