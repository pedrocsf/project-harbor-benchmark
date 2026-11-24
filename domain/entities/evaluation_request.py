from dataclasses import dataclass

from domain.entities.language_model_settings import LanguageModelSettings
from domain.entities.question import Question
from domain.entities.rag_endpoint_settings import RagEndpointSettings
from domain.scoring.scoring_method import ScoringMethod


@dataclass(frozen=True)
class EvaluationRequest:
    settings: LanguageModelSettings | None
    questions: tuple[Question, ...]
    method: ScoringMethod
    rag_settings: RagEndpointSettings | None = None
