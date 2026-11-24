import json

import pytest

from data.contexts_payload import ContextsFormatError, contexts_to_payload, parse_contexts
from data.repositories.json_run_import_repository import JsonRunImportRepository
from domain.entities.imported_answer import ImportedAnswer
from domain.entities.imported_run import ImportedRun
from domain.entities.question import Question
from domain.entities.retrieved_context import RetrievedContext
from domain.errors import EvaluationCancelledError, RunImportError
from domain.scoring.exact_match_scoring_method import ExactMatchScoringMethod
from domain.usecases.load_imported_run import LoadImportedRun
from domain.usecases.score_imported_run import ScoreImportedRun, ScoreImportedRunRequest


def write(tmp_path, name, text):
    path = tmp_path / name
    path.write_text(text, encoding="utf-8")
    return path


def test_parses_string_and_object_contexts():
    contexts = parse_contexts(["plain text", {"doc_id": 7, "content": "obj", "score": 0.5}])

    assert contexts == (
        RetrievedContext(None, "plain text"),
        RetrievedContext("7", "obj", 0.5),
    )


@pytest.mark.parametrize("raw", ["text", [1], [{"id": "a"}]])
def test_rejects_unreadable_contexts(raw):
    with pytest.raises(ContextsFormatError):
        parse_contexts(raw)


def test_contexts_round_trip_through_the_payload():
    contexts = (RetrievedContext("a", "x", 0.25), RetrievedContext(None, "y"))

    assert parse_contexts(contexts_to_payload(contexts)) == contexts
    assert contexts_to_payload(None) is None


def test_reads_a_json_list(tmp_path):
    path = write(
        tmp_path,
        "run.json",
        json.dumps(
            [
                {"id": 1, "answer": "Paris", "contexts": ["Paris é a capital."], "response_seconds": 1.5},
                {"id": "2", "answer": None},
            ]
        ),
    )

    first, second = JsonRunImportRepository().load(path)

    assert first == ImportedAnswer("1", "Paris", (RetrievedContext(None, "Paris é a capital."),), 1.5)
    assert second == ImportedAnswer("2", "", None, 0.0)


def test_reads_json_lines_and_skips_blank_lines(tmp_path):
    path = write(tmp_path, "run.jsonl", '{"id": "1", "answer": "a"}\n\n{"id": "2", "answer": "b", "contexts": []}\n')

    answers = JsonRunImportRepository().load(path)

    assert [(answer.question_identifier, answer.contexts) for answer in answers] == [("1", None), ("2", ())]


def test_reads_a_result_exported_by_the_app(tmp_path):
    exported = {"method": "exact_match", "scores": [{"id": "1", "given_answer": "a", "contexts": None}]}
    path = write(tmp_path, "result.json", json.dumps(exported))

    assert JsonRunImportRepository().load(path) == [ImportedAnswer("1", "a")]


@pytest.mark.parametrize(
    ("name", "text", "message"),
    [
        ("run.json", "{bad", "not valid JSON"),
        ("run.jsonl", '{"id": 1, "answer": "a"}\n{bad', "Line 2"),
        ("run.json", '{"answers": 1}', "list of answers"),
        ("run.json", '[{"answer": "a"}]', "'id'"),
        ("run.json", '[{"id": 1}]', "'answer'"),
        ("run.json", '[{"id": 1, "answer": 3}]', "must be text"),
        ("run.json", '[{"id": 1, "answer": "a", "contexts": "x"}]', "contexts must be a list"),
        ("run.json", '[{"id": 1, "answer": "a", "response_seconds": -1}]', "response_seconds"),
    ],
)
def test_rejects_malformed_runs(tmp_path, name, text, message):
    with pytest.raises(RunImportError, match=message):
        JsonRunImportRepository().load(write(tmp_path, name, text))


def test_rejects_a_missing_file(tmp_path):
    with pytest.raises(RunImportError):
        JsonRunImportRepository().load(tmp_path / "missing.json")


class FakeRunImportRepository:
    def __init__(self, answers):
        self._answers = answers

    def load(self, source):
        return list(self._answers)


def test_load_imported_run_rejects_empty_and_duplicated_runs(tmp_path):
    with pytest.raises(RunImportError, match="No answers"):
        LoadImportedRun(FakeRunImportRepository([])).execute(tmp_path / "run.json")
    duplicated = [ImportedAnswer("1", "a"), ImportedAnswer("1", "b")]
    with pytest.raises(RunImportError, match="more than one answer"):
        LoadImportedRun(FakeRunImportRepository(duplicated)).execute(tmp_path / "run.json")


def test_load_imported_run_keeps_the_file_name(tmp_path):
    run = LoadImportedRun(FakeRunImportRepository([ImportedAnswer("1", "a", ())])).execute(tmp_path / "run.json")

    assert run.source_name == "run.json"
    assert run.has_contexts


QUESTIONS = (Question("1", "Capital?", "Paris"), Question("2", "Autor?", "Machado"))


def test_scores_imported_answers_in_dataset_order():
    contexts = (RetrievedContext("doc", "Paris"),)
    run = ImportedRun(
        "run.json",
        (ImportedAnswer("2", "Assis", None, 2.0), ImportedAnswer("1", "Paris", contexts, 1.0), ImportedAnswer("9", "x")),
    )
    progress = []

    result = ScoreImportedRun().execute(
        ScoreImportedRunRequest(run, QUESTIONS, ExactMatchScoringMethod()),
        on_progress=lambda done, total: progress.append((done, total)),
    )

    assert [(score.question.identifier, score.score) for score in result.scores] == [("1", 1.0), ("2", 0.0)]
    assert result.scores[0].contexts == contexts
    assert result.scores[1].response_seconds == 2.0
    assert progress == [(1, 2), (2, 2)]
    assert not result.has_contexts


def test_reports_the_questions_without_an_imported_answer():
    questions = tuple(Question(str(number), "q?", "a") for number in range(1, 9))
    run = ImportedRun("run.json", (ImportedAnswer("1", "a"),))

    with pytest.raises(RunImportError, match=r"2, 3, 4, 5, 6 and 2 more"):
        ScoreImportedRun().execute(ScoreImportedRunRequest(run, questions, ExactMatchScoringMethod()))


def test_scoring_an_imported_run_can_be_cancelled():
    run = ImportedRun("run.json", (ImportedAnswer("1", "Paris"), ImportedAnswer("2", "Machado")))

    with pytest.raises(EvaluationCancelledError):
        ScoreImportedRun().execute(
            ScoreImportedRunRequest(run, QUESTIONS, ExactMatchScoringMethod()), is_cancelled=lambda: True
        )
