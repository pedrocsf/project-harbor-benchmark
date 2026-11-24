from abc import ABC, abstractmethod
from collections.abc import Sequence
from enum import Enum

from domain.entities.evaluation_sample import EvaluationSample
from domain.entities.language_model_settings import LanguageModelSettings
from domain.errors import DomainError
from domain.scoring.metric_parameters import (
    ParameterSpec,
    ParameterValue,
    ParameterValues,
    default_parameters,
    validate_parameters,
)
from domain.scoring.sample_requirements import MetricGroup, SampleRequirement

PARAMETER_STORAGE_KEY = "_parameter_values"


class ScoreKind(Enum):
    CONTINUOUS = "continuous"
    BINARY = "binary"


class ScoringMethod(ABC):
    identifier: str
    display_name: str
    column_header: str
    score_kind: ScoreKind
    uses_language_model: bool = False
    parameter_specs: tuple[ParameterSpec, ...] = ()
    requirements: frozenset[SampleRequirement] = frozenset()
    metric_group: MetricGroup = MetricGroup.ANSWER

    @property
    def parameters(self) -> dict[str, ParameterValue]:
        stored = self.__dict__.get(PARAMETER_STORAGE_KEY)
        if stored is None:
            return default_parameters(self.parameter_specs)
        return dict(stored)

    def parameter(self, key: str) -> ParameterValue:
        return self.parameters[key]

    def update_parameters(self, values: ParameterValues) -> None:
        validated = validate_parameters(self.parameter_specs, {**self.parameters, **values})
        self._check_parameters(validated)
        self.__dict__[PARAMETER_STORAGE_KEY] = validated

    def reset_parameters(self) -> None:
        self.__dict__.pop(PARAMETER_STORAGE_KEY, None)

    def _check_parameters(self, values: ParameterValues) -> None:
        return None

    def configure(self, settings: LanguageModelSettings | None) -> None:
        return None

    def prepare(self) -> None:
        return None

    def judge_calls_per_question(self) -> int | None:
        return 0

    @abstractmethod
    def score(self, expected_answer: str, given_answer: str) -> float:
        ...

    def score_sample(self, sample: EvaluationSample) -> float:
        return self.score(sample.expected_answer, sample.given_answer)

    def corpus_score(self, answer_pairs: Sequence[tuple[str, str]]) -> float | None:
        return None


class SampleOnlyMetricError(DomainError):
    pass


SAMPLE_ONLY_MESSAGE = "{name} needs the question and the retrieved contexts, not only two answers."


class SampleScoringMethod(ScoringMethod):
    def score(self, expected_answer: str, given_answer: str) -> float:
        raise SampleOnlyMetricError(SAMPLE_ONLY_MESSAGE.format(name=self.display_name))

    @abstractmethod
    def score_sample(self, sample: EvaluationSample) -> float:
        ...
