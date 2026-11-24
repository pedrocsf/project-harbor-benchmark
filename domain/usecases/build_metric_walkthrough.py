import math
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field

from domain.errors import DomainError
from domain.explanations.lexical_walkthroughs import (
    PERFECT_SCORE,
    ZERO_SCORE,
    contains_answer_details,
    exact_match_details,
    lcs_details,
    ngram_overlap_details,
    token_f1_score,
    token_overlap_details,
    token_recall_score,
)
from domain.explanations.metric_walkthrough import MetricWalkthrough
from domain.explanations.translation_statistics import TranslationStatisticsProvider
from domain.explanations.walkthrough_details import EmbeddingDetails, LlmJudgeDetails
from domain.gateways.text_encoder import TextEncoder
from domain.scoring.contains_answer_scoring_method import ContainsAnswerScoringMethod
from domain.scoring.embedding_scoring_method import EmbeddingScoringMethod
from domain.scoring.exact_match_scoring_method import ExactMatchScoringMethod
from domain.scoring.llm_judge_scoring_method import LlmJudgeScoringMethod, build_judge_prompt
from domain.scoring.metric_parameters import ParameterSpec, default_parameters
from domain.scoring.rouge_scoring_methods import ROUGE_PARAMETER_SPECS
from domain.scoring.text_normalization import normalization_options_from
from domain.scoring.token_f1_scoring_method import TokenF1ScoringMethod
from domain.scoring.token_recall_scoring_method import TokenRecallScoringMethod
from domain.scoring.vector_similarity import measure_similarity

UNKNOWN_METRIC_MESSAGE = "There is no walkthrough for the metric {identifier!r}."
MISSING_KNOWN_SCORE_MESSAGE = "The metric {identifier!r} needs a known score to build its walkthrough."
DEFAULT_BETA = 1.0
UNIGRAM_ORDER = 1
BIGRAM_ORDER = 2


class UnknownWalkthroughMetricError(DomainError):
    pass


@dataclass(frozen=True)
class WalkthroughRequest:
    identifier: str
    expected_answer: str
    given_answer: str
    known_score: float | None = None
    parameters: Mapping[str, object] = field(default_factory=dict)


class BuildMetricWalkthrough:
    def __init__(
        self,
        translation_statistics: TranslationStatisticsProvider,
        text_encoder: TextEncoder | None = None,
    ):
        self._translation_statistics = translation_statistics
        self._text_encoder = text_encoder
        self._builders: dict[str, Callable[[WalkthroughRequest], tuple[float, object]]] = {
            "embedding": self._embedding,
            "exact_match": self._exact_match,
            "token_f1": self._token_f1,
            "token_recall": self._token_recall,
            "contains_answer": self._contains_answer,
            "rouge_1": self._rouge_1,
            "rouge_2": self._rouge_2,
            "rouge_l": self._rouge_l,
            "bleu": self._bleu,
            "chrf": self._chrf,
            "llm_judge": self._llm_judge,
        }

    @property
    def supported_identifiers(self) -> tuple[str, ...]:
        return tuple(self._builders)

    def execute(self, request: WalkthroughRequest) -> MetricWalkthrough:
        builder = self._builders.get(request.identifier)
        if builder is None:
            raise UnknownWalkthroughMetricError(UNKNOWN_METRIC_MESSAGE.format(identifier=request.identifier))
        final_score, details = builder(request)
        return MetricWalkthrough(
            request.identifier,
            request.expected_answer,
            request.given_answer,
            final_score,
            details,
            dict(request.parameters),
        )

    def _parameters(self, request: WalkthroughRequest, specs: Sequence[ParameterSpec]) -> dict:
        return {**default_parameters(specs), **request.parameters}

    def _exact_match(self, request: WalkthroughRequest) -> tuple[float, object]:
        parameters = self._parameters(request, ExactMatchScoringMethod.parameter_specs)
        options = normalization_options_from(parameters)
        details = exact_match_details(request.expected_answer, request.given_answer, options)
        return (PERFECT_SCORE if details.is_match else ZERO_SCORE), details

    def _token_f1(self, request: WalkthroughRequest) -> tuple[float, object]:
        parameters = self._parameters(request, TokenF1ScoringMethod.parameter_specs)
        options = normalization_options_from(parameters)
        details = token_overlap_details(
            request.expected_answer, request.given_answer, options, float(parameters["beta"])
        )
        return token_f1_score(details), details

    def _token_recall(self, request: WalkthroughRequest) -> tuple[float, object]:
        parameters = self._parameters(request, TokenRecallScoringMethod.parameter_specs)
        options = normalization_options_from(parameters)
        details = token_overlap_details(request.expected_answer, request.given_answer, options)
        return token_recall_score(details), details

    def _contains_answer(self, request: WalkthroughRequest) -> tuple[float, object]:
        parameters = self._parameters(request, ContainsAnswerScoringMethod.parameter_specs)
        options = normalization_options_from(parameters)
        details = contains_answer_details(
            request.expected_answer, request.given_answer, options, str(parameters["match_mode"])
        )
        return (ZERO_SCORE if details.found_at is None else PERFECT_SCORE), details

    def _rouge_ngram(self, request: WalkthroughRequest, order: int) -> tuple[float, object]:
        parameters = self._parameters(request, ROUGE_PARAMETER_SPECS)
        details = ngram_overlap_details(
            request.expected_answer,
            request.given_answer,
            order,
            str(parameters["score_type"]),
            float(parameters["beta"]),
            bool(parameters["lowercase"]),
        )
        return details.score, details

    def _rouge_1(self, request: WalkthroughRequest) -> tuple[float, object]:
        return self._rouge_ngram(request, UNIGRAM_ORDER)

    def _rouge_2(self, request: WalkthroughRequest) -> tuple[float, object]:
        return self._rouge_ngram(request, BIGRAM_ORDER)

    def _rouge_l(self, request: WalkthroughRequest) -> tuple[float, object]:
        parameters = self._parameters(request, ROUGE_PARAMETER_SPECS)
        details = lcs_details(
            request.expected_answer,
            request.given_answer,
            str(parameters["score_type"]),
            float(parameters["beta"]),
            bool(parameters["lowercase"]),
        )
        return details.score, details

    def _bleu(self, request: WalkthroughRequest) -> tuple[float, object]:
        details = self._translation_statistics.bleu_details(
            request.given_answer, request.expected_answer, request.parameters or None
        )
        return details.score, details

    def _chrf(self, request: WalkthroughRequest) -> tuple[float, object]:
        details = self._translation_statistics.chrf_details(
            request.given_answer, request.expected_answer, request.parameters or None
        )
        return details.f_score, details

    def _embedding(self, request: WalkthroughRequest) -> tuple[float, object]:
        parameters = self._parameters(request, EmbeddingScoringMethod.parameter_specs)
        if self._text_encoder is not None and request.given_answer.strip():
            return self._encoded_embedding(request, parameters)
        return self._known_score_embedding(request, parameters)

    def _encoded_embedding(self, request: WalkthroughRequest, parameters: dict) -> tuple[float, object]:
        expected_vector, given_vector = self._text_encoder.encode(
            [request.expected_answer, request.given_answer]
        )
        outcome = measure_similarity(expected_vector, given_vector, parameters)
        details = EmbeddingDetails(
            cosine=outcome.cosine,
            angle_degrees=outcome.angle_degrees,
            clipped=outcome.was_clipped,
            function=outcome.function,
            raw_value=outcome.raw_value,
            score=outcome.score,
            negative_handling=str(parameters["negative_handling"]),
            normalize_vectors=bool(parameters["normalize_vectors"]),
            expected_vector=tuple(expected_vector),
            given_vector=tuple(given_vector),
        )
        return outcome.score, details

    def _known_score_embedding(self, request: WalkthroughRequest, parameters: dict) -> tuple[float, object]:
        is_empty_answer = not request.given_answer.strip()
        if is_empty_answer and request.known_score is None:
            cosine = ZERO_SCORE
        else:
            cosine = self._require_known_score(request)
        clipped = not is_empty_answer and cosine <= ZERO_SCORE
        angle_degrees = math.degrees(math.acos(max(-PERFECT_SCORE, min(PERFECT_SCORE, cosine))))
        details = EmbeddingDetails(
            cosine=cosine,
            angle_degrees=angle_degrees,
            clipped=clipped,
            function=str(parameters["similarity_function"]),
            raw_value=cosine,
            score=cosine,
            negative_handling=str(parameters["negative_handling"]),
            normalize_vectors=bool(parameters["normalize_vectors"]),
        )
        return cosine, details

    def _llm_judge(self, request: WalkthroughRequest) -> tuple[float, object]:
        known_score = self._require_known_score(request)
        parameters = self._parameters(request, LlmJudgeScoringMethod.parameter_specs)
        maximum_rating = int(parameters["rating_scale_max"])
        template = str(parameters["prompt_template"])
        samples = int(parameters["samples"])
        prompt = build_judge_prompt(template, request.expected_answer, request.given_answer, maximum_rating)
        if not request.given_answer.strip():
            return ZERO_SCORE, LlmJudgeDetails(prompt, "", 0, False, maximum_rating, samples, template, ZERO_SCORE)
        rating = round(known_score * maximum_rating)
        score = rating / maximum_rating
        return score, LlmJudgeDetails(prompt, str(rating), rating, True, maximum_rating, samples, template, score)

    def _require_known_score(self, request: WalkthroughRequest) -> float:
        if request.known_score is None:
            raise ValueError(MISSING_KNOWN_SCORE_MESSAGE.format(identifier=request.identifier))
        return request.known_score
