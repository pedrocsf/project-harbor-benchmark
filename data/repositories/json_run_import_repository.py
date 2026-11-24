import json
from pathlib import Path

from data.contexts_payload import ContextsFormatError, parse_contexts
from domain.entities.imported_answer import ImportedAnswer
from domain.errors import RunImportError
from domain.repositories.run_import_repository import RunImportRepository

JSONL_SUFFIX = ".jsonl"
EXPORTED_SCORES_KEY = "scores"
IDENTIFIER_KEY = "id"
ANSWER_KEYS = ("answer", "given_answer")
CONTEXTS_KEY = "contexts"
RESPONSE_SECONDS_KEY = "response_seconds"


class JsonRunImportRepository(RunImportRepository):
    def load(self, source: Path) -> list[ImportedAnswer]:
        entries = self._read_entries(source)
        return [self._build_answer(position, entry) for position, entry in enumerate(entries, start=1)]

    def _read_entries(self, source: Path) -> list:
        try:
            text = source.read_text(encoding="utf-8-sig")
        except OSError as error:
            raise RunImportError(f"Could not read the run file {source}: {error}") from error
        if source.suffix.lower() == JSONL_SUFFIX:
            return self._parse_json_lines(text)
        return self._parse_json_document(text)

    def _parse_json_lines(self, text: str) -> list:
        entries = []
        for line_number, line in enumerate(text.splitlines(), start=1):
            if not line.strip():
                continue
            try:
                entries.append(json.loads(line))
            except ValueError as error:
                raise RunImportError(f"Line {line_number} of the run file is not valid JSON: {error}") from error
        return entries

    def _parse_json_document(self, text: str) -> list:
        try:
            content = json.loads(text)
        except ValueError as error:
            raise RunImportError(f"The run file is not valid JSON: {error}") from error
        if isinstance(content, dict) and isinstance(content.get(EXPORTED_SCORES_KEY), list):
            return content[EXPORTED_SCORES_KEY]
        if not isinstance(content, list):
            raise RunImportError(
                "The run file must contain a list of answers, one JSON object per line (.jsonl), "
                "or a result exported by this app."
            )
        return content

    def _build_answer(self, position: int, entry: object) -> ImportedAnswer:
        if not isinstance(entry, dict):
            raise RunImportError(f"Answer {position} must be a JSON object.")
        identifier = entry.get(IDENTIFIER_KEY)
        if identifier is None or isinstance(identifier, (bool, dict, list)):
            raise RunImportError(f"Answer {position} is missing the field 'id' of its question.")
        return ImportedAnswer(
            question_identifier=str(identifier),
            answer=self._read_answer(position, entry),
            contexts=self._read_contexts(position, entry),
            response_seconds=self._read_response_seconds(position, entry),
        )

    def _read_answer(self, position: int, entry: dict) -> str:
        for key in ANSWER_KEYS:
            if key in entry:
                answer = entry[key]
                if answer is None:
                    return ""
                if isinstance(answer, str):
                    return answer
                raise RunImportError(f"The field '{key}' of answer {position} must be text.")
        raise RunImportError(f"Answer {position} is missing the field 'answer'.")

    def _read_contexts(self, position: int, entry: dict):
        if entry.get(CONTEXTS_KEY) is None:
            return None
        try:
            return parse_contexts(entry[CONTEXTS_KEY])
        except ContextsFormatError as error:
            raise RunImportError(f"Answer {position}: {error}") from error

    def _read_response_seconds(self, position: int, entry: dict) -> float:
        seconds = entry.get(RESPONSE_SECONDS_KEY, 0.0)
        if seconds is None:
            return 0.0
        if isinstance(seconds, bool) or not isinstance(seconds, (int, float)) or seconds < 0:
            raise RunImportError(f"The field 'response_seconds' of answer {position} must be a positive number.")
        return float(seconds)
