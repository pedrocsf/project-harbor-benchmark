from dataclasses import dataclass


@dataclass(frozen=True)
class TokenOverlapDetails:
    expected_tokens: tuple[str, ...]
    answer_tokens: tuple[str, ...]
    common_count: int
    matched_expected_indexes: tuple[int, ...]
    matched_answer_indexes: tuple[int, ...]
    matches: tuple[tuple[int, int], ...]
    precision: float
    recall: float
    f1: float
    beta: float = 1.0
    f_score: float = 0.0


@dataclass(frozen=True)
class NormalizationDetails:
    expected_stages: tuple[str, ...]
    answer_stages: tuple[str, ...]
    stage_names: tuple[str, ...]
    normalized_expected: str
    normalized_answer: str
    lowercase: bool = True
    strip_accents: bool = False
    remove_punctuation: bool = True
    articles: str = "english"


@dataclass(frozen=True)
class ExactMatchDetails:
    normalization: NormalizationDetails
    is_match: bool


@dataclass(frozen=True)
class ContainsAnswerDetails:
    normalization: NormalizationDetails
    expected_tokens: tuple[str, ...]
    answer_tokens: tuple[str, ...]
    found_at: int | None
    window_positions: tuple[int, ...]
    match_mode: str = "whole_words"
    character_position: int | None = None


@dataclass(frozen=True)
class NgramOverlapDetails:
    order: int
    expected_ngrams: tuple[tuple[str, ...], ...]
    answer_ngrams: tuple[tuple[str, ...], ...]
    overlap_count: int
    matched_expected_indexes: tuple[int, ...]
    matched_answer_indexes: tuple[int, ...]
    matches: tuple[tuple[int, int], ...]
    precision: float
    recall: float
    f_measure: float
    score_type: str = "f_measure"
    beta: float = 1.0
    score: float = 0.0


@dataclass(frozen=True)
class LcsDetails:
    expected_tokens: tuple[str, ...]
    answer_tokens: tuple[str, ...]
    table: tuple[tuple[int, ...], ...]
    path: tuple[tuple[int, int], ...]
    matched_cells: tuple[tuple[int, int], ...]
    lcs_length: int
    precision: float
    recall: float
    f_measure: float
    score_type: str = "f_measure"
    beta: float = 1.0
    score: float = 0.0


@dataclass(frozen=True)
class BleuDetails:
    answer_tokens: tuple[str, ...]
    reference_tokens: tuple[str, ...]
    matches_by_order: tuple[int, ...]
    totals_by_order: tuple[int, ...]
    precisions: tuple[float, ...]
    smoothed_orders: tuple[int, ...]
    effective_order: int
    answer_length: int
    reference_length: int
    brevity_penalty: float
    geometric_mean: float
    score: float


@dataclass(frozen=True)
class ChrfOrderStatistics:
    order: int
    answer_count: int
    reference_count: int
    match_count: int
    precision: float
    recall: float


@dataclass(frozen=True)
class ChrfDetails:
    character_orders: tuple[ChrfOrderStatistics, ...]
    word_orders: tuple[ChrfOrderStatistics, ...]
    beta: float
    average_precision: float
    average_recall: float
    f_score: float


@dataclass(frozen=True)
class EmbeddingDetails:
    cosine: float
    angle_degrees: float
    clipped: bool
    function: str = "cosine"
    raw_value: float = 0.0
    score: float = 0.0
    negative_handling: str = "clip"
    normalize_vectors: bool = True
    expected_vector: tuple[float, ...] = ()
    given_vector: tuple[float, ...] = ()


@dataclass(frozen=True)
class LlmJudgeDetails:
    prompt_preview: str
    raw_reply: str
    judge_score_out_of_ten: int
    model_was_called: bool
    maximum_rating: int = 10
    samples: int = 1
    prompt_template: str = ""
    score: float = 0.0
