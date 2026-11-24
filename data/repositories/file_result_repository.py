import csv
import json
from pathlib import Path

from data.contexts_payload import contexts_to_payload
from domain.entities.evaluation_metrics import EvaluationMetrics
from domain.entities.evaluation_result import EvaluationResult
from domain.entities.question_score import QuestionScore
from domain.errors import ResultExportError
from domain.repositories.result_repository import CompanionScores, ResultRepository

JSON_SUFFIX = ".json"
CSV_SUFFIX = ".csv"
CSV_COLUMNS = ("id", "question", "expected_answer", "given_answer", "method", "score", "response_seconds")
CSV_CONTEXT_COLUMNS = ("context_count", "context_ids")
CONTEXT_ID_SEPARATOR = " | "
MISSING_CONTEXT_ID = "?"


def _score_to_row(score: QuestionScore, method_identifier: str) -> dict:
    return {
        "id": score.question.identifier,
        "question": score.question.text,
        "expected_answer": score.question.expected_answer,
        "given_answer": score.given_answer,
        "method": method_identifier,
        "score": score.score,
        "response_seconds": score.response_seconds,
    }


def _metrics_to_dict(metrics: EvaluationMetrics) -> dict:
    return {
        "question_count": metrics.question_count,
        "median_score": metrics.median_score,
        "highest_score": metrics.highest.score,
        "highest_score_question_id": metrics.highest.question.identifier,
        "lowest_score": metrics.lowest.score,
        "lowest_score_question_id": metrics.lowest.question.identifier,
        "correct_count": metrics.correct_count,
        "corpus_score": metrics.corpus_score,
        "average_response_seconds": metrics.average_response_seconds,
        "fastest_response_seconds": metrics.fastest_response_seconds,
        "slowest_response_seconds": metrics.slowest_response_seconds,
        "total_response_seconds": metrics.total_response_seconds,
        "empty_answer_count": metrics.empty_answer_count,
        "average_answer_length": metrics.average_answer_length,
    }


def _context_ids_text(score: QuestionScore) -> str:
    return CONTEXT_ID_SEPARATOR.join(context.identifier or MISSING_CONTEXT_ID for context in score.contexts)


def _companion_values(companion_scores: CompanionScores, position: int) -> dict:
    return {identifier: scores[position] for identifier, scores in companion_scores.items()}


class FileResultRepository(ResultRepository):
    def save(
        self, result: EvaluationResult, destination: Path, companion_scores: CompanionScores | None = None
    ) -> None:
        writers = {JSON_SUFFIX: self._write_json, CSV_SUFFIX: self._write_csv}
        writer = writers.get(destination.suffix.lower())
        if writer is None:
            raise ResultExportError(f"Unsupported file format: '{destination.suffix}'. Use .json or .csv.")
        try:
            writer(result, destination, companion_scores or {})
        except OSError as error:
            raise ResultExportError(f"Could not save the result to {destination}: {error}") from error

    def _write_json(self, result: EvaluationResult, destination: Path, companion_scores: CompanionScores) -> None:
        document = {
            "evaluated_at": result.evaluated_at.isoformat(timespec="seconds"),
            "method": result.method.identifier,
            "method_name": result.method.display_name,
            "method_parameters": result.method.parameters,
            "average_score": result.average_score,
            "metrics": _metrics_to_dict(result.metrics),
            "scores": [
                self._json_row(result, score, _companion_values(companion_scores, position))
                for position, score in enumerate(result.scores)
            ],
        }
        if companion_scores:
            document["companion_averages"] = {
                identifier: sum(scores) / len(scores) for identifier, scores in companion_scores.items() if scores
            }
        destination.write_text(json.dumps(document, ensure_ascii=False, indent=2), encoding="utf-8")

    def _json_row(self, result: EvaluationResult, score: QuestionScore, companions: dict) -> dict:
        row = _score_to_row(score, result.method.identifier)
        if score.contexts is not None:
            row["contexts"] = contexts_to_payload(score.contexts)
        if companions:
            row["companion_scores"] = companions
        return row

    def _write_csv(self, result: EvaluationResult, destination: Path, companion_scores: CompanionScores) -> None:
        has_contexts = any(score.contexts is not None for score in result.scores)
        columns = CSV_COLUMNS + (CSV_CONTEXT_COLUMNS if has_contexts else ()) + tuple(companion_scores)
        with destination.open("w", encoding="utf-8-sig", newline="") as output:
            writer = csv.DictWriter(output, fieldnames=columns)
            writer.writeheader()
            for position, score in enumerate(result.scores):
                row = _score_to_row(score, result.method.identifier)
                if has_contexts:
                    row.update(self._context_columns(score))
                row.update(_companion_values(companion_scores, position))
                writer.writerow(row)

    def _context_columns(self, score: QuestionScore) -> dict:
        if score.contexts is None:
            return {"context_count": "", "context_ids": ""}
        return {"context_count": len(score.contexts), "context_ids": _context_ids_text(score)}
