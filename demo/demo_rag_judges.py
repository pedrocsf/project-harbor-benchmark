from collections.abc import Mapping

from demo.demo_rag_data import DemoRagEntry
from domain.entities.evaluation_sample import EvaluationSample
from domain.entities.retrieved_context import RetrievedContext
from domain.errors import DomainError
from domain.gateways.text_encoder import TextEncoder
from domain.scoring.rag.answer_relevancy_scoring_method import AnswerRelevancyScoringMethod
from domain.scoring.rag.context_relevance_scoring_method import ContextRelevanceScoringMethod
from domain.scoring.rag.faithfulness_scoring_method import FaithfulnessScoringMethod

UNKNOWN_ANSWER_MESSAGE = "The demo judge has nothing recorded for the answer {answer!r}."
UNKNOWN_CONTEXT_MESSAGE = "The demo judge has no rating for the context {context!r}."


class UnknownDemoJudgeInputError(DomainError):
    pass


def entries_by_answer(entries: Mapping[str, DemoRagEntry], answers: Mapping[str, str]) -> dict[str, DemoRagEntry]:
    return {answers[identifier]: entry for identifier, entry in entries.items()}


def relevance_by_context(
    entries: Mapping[str, DemoRagEntry], questions: Mapping[str, str]
) -> dict[tuple[str, str], float]:
    return {
        (questions[identifier], context.text): fraction
        for identifier, entry in entries.items()
        for context, fraction in zip(entry.contexts, entry.context_relevance)
    }


def _entry_for(entries: Mapping[str, DemoRagEntry], answer: str) -> DemoRagEntry:
    if answer not in entries:
        raise UnknownDemoJudgeInputError(UNKNOWN_ANSWER_MESSAGE.format(answer=answer))
    return entries[answer]


class DemoFaithfulnessScoringMethod(FaithfulnessScoringMethod):
    uses_language_model = False

    def __init__(self, entries_by_given_answer: Mapping[str, DemoRagEntry]):
        super().__init__(None)
        self._entries = entries_by_given_answer
        self._verdicts = {
            statement: verdict
            for entry in entries_by_given_answer.values()
            for statement, verdict in zip(entry.statements, entry.verdicts)
        }

    def extract_statements(self, sample: EvaluationSample) -> tuple[str, ...]:
        return _entry_for(self._entries, sample.given_answer).statements

    def verify_statements(
        self, statements: tuple[str, ...], contexts: tuple[RetrievedContext, ...]
    ) -> tuple[bool, ...]:
        return tuple(self._verdicts.get(statement, False) for statement in statements)


class DemoContextRelevanceScoringMethod(ContextRelevanceScoringMethod):
    uses_language_model = False

    def __init__(self, relevance_by_question_and_context: Mapping[tuple[str, str], float]):
        super().__init__(None)
        self._relevance = relevance_by_question_and_context

    def rate_context(self, question: str, context: str, maximum_rating: int) -> int:
        key = (question, context)
        if key not in self._relevance:
            raise UnknownDemoJudgeInputError(UNKNOWN_CONTEXT_MESSAGE.format(context=context[:60]))
        return round(self._relevance[key] * maximum_rating)


class DemoAnswerRelevancyScoringMethod(AnswerRelevancyScoringMethod):
    uses_language_model = False

    def __init__(self, entries_by_given_answer: Mapping[str, DemoRagEntry], text_encoder: TextEncoder):
        super().__init__(None, text_encoder)
        self._entries = entries_by_given_answer

    def generate_questions(self, sample: EvaluationSample, question_count: int) -> tuple[str, ...]:
        return _entry_for(self._entries, sample.given_answer).generated_questions
