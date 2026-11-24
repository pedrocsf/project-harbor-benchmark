from collections.abc import Sequence

from domain.explanations.walkthrough_details import (
    ContainsAnswerDetails,
    ExactMatchDetails,
    LcsDetails,
    NgramOverlapDetails,
    NormalizationDetails,
    TokenOverlapDetails,
)
from domain.scoring.contains_answer_scoring_method import MATCH_MODE_SUBSTRING
from domain.scoring.rouge_scoring_methods import SCORE_TYPE_PRECISION, SCORE_TYPE_RECALL
from domain.scoring.text_normalization import (
    DEFAULT_NORMALIZATION,
    NormalizationOptions,
    active_normalization_stages,
    normalization_stages,
    normalized_tokens,
    word_tokens,
)
from domain.scoring.token_f1_scoring_method import f_beta_score

PERFECT_SCORE = 1.0
ZERO_SCORE = 0.0


def _ratio(numerator: int, denominator: int) -> float:
    if denominator == 0:
        return ZERO_SCORE
    return numerator / denominator


DEFAULT_BETA = 1.0
WHOLE_WORDS_MODE = "whole_words"
F_MEASURE_TYPE = "f_measure"


def _selected_score(score_type: str, precision: float, recall: float, f_measure: float) -> float:
    if score_type == SCORE_TYPE_PRECISION:
        return precision
    if score_type == SCORE_TYPE_RECALL:
        return recall
    return f_measure


def _match_items(expected_items: Sequence, answer_items: Sequence) -> tuple[tuple[int, int], ...]:
    used_answer_indexes: set[int] = set()
    matches = []
    for expected_index, expected_item in enumerate(expected_items):
        for answer_index, answer_item in enumerate(answer_items):
            if answer_index in used_answer_indexes or answer_item != expected_item:
                continue
            used_answer_indexes.add(answer_index)
            matches.append((expected_index, answer_index))
            break
    return tuple(matches)


def _expected_indexes(matches: tuple[tuple[int, int], ...]) -> tuple[int, ...]:
    return tuple(sorted(expected_index for expected_index, _ in matches))


def _answer_indexes(matches: tuple[tuple[int, int], ...]) -> tuple[int, ...]:
    return tuple(sorted(answer_index for _, answer_index in matches))


def token_overlap_details(
    expected_answer: str,
    given_answer: str,
    options: NormalizationOptions = DEFAULT_NORMALIZATION,
    beta: float = DEFAULT_BETA,
) -> TokenOverlapDetails:
    expected_tokens = tuple(normalized_tokens(expected_answer, options))
    answer_tokens = tuple(normalized_tokens(given_answer, options))
    matches = _match_items(expected_tokens, answer_tokens)
    precision = _ratio(len(matches), len(answer_tokens))
    recall = _ratio(len(matches), len(expected_tokens))
    f_score = f_beta_score(precision, recall, beta)
    return TokenOverlapDetails(
        expected_tokens=expected_tokens,
        answer_tokens=answer_tokens,
        common_count=len(matches),
        matched_expected_indexes=_expected_indexes(matches),
        matched_answer_indexes=_answer_indexes(matches),
        matches=matches,
        precision=precision,
        recall=recall,
        f1=f_score,
        beta=beta,
        f_score=f_score,
    )


def token_f1_score(details: TokenOverlapDetails) -> float:
    if not details.expected_tokens or not details.answer_tokens:
        return PERFECT_SCORE if details.expected_tokens == details.answer_tokens else ZERO_SCORE
    return details.f1


def token_recall_score(details: TokenOverlapDetails) -> float:
    if not details.expected_tokens:
        return PERFECT_SCORE if not details.answer_tokens else ZERO_SCORE
    return details.recall


def normalization_details(
    expected_answer: str, given_answer: str, options: NormalizationOptions = DEFAULT_NORMALIZATION
) -> NormalizationDetails:
    expected_stages = normalization_stages(expected_answer, options)
    answer_stages = normalization_stages(given_answer, options)
    return NormalizationDetails(
        expected_stages=expected_stages,
        answer_stages=answer_stages,
        stage_names=tuple(name for name, _ in active_normalization_stages(options)),
        normalized_expected=expected_stages[-1],
        normalized_answer=answer_stages[-1],
        lowercase=options.lowercase,
        strip_accents=options.strip_accents,
        remove_punctuation=options.remove_punctuation,
        articles=options.articles,
    )


def exact_match_details(
    expected_answer: str, given_answer: str, options: NormalizationOptions = DEFAULT_NORMALIZATION
) -> ExactMatchDetails:
    normalization = normalization_details(expected_answer, given_answer, options)
    return ExactMatchDetails(normalization, normalization.normalized_expected == normalization.normalized_answer)


def _token_index_at(text: str, position: int) -> int:
    tokens_before = len(text[:position].split())
    inside_token = position > 0 and not text[position - 1].isspace()
    return tokens_before - 1 if inside_token else tokens_before


def _substring_details(
    normalization: NormalizationDetails, expected_tokens: tuple[str, ...], answer_tokens: tuple[str, ...]
) -> ContainsAnswerDetails:
    expected_text = normalization.normalized_expected
    answer_text = normalization.normalized_answer
    if not expected_text:
        position = 0 if not answer_text else None
        return ContainsAnswerDetails(
            normalization, expected_tokens, answer_tokens, position, (), MATCH_MODE_SUBSTRING, position
        )
    position = answer_text.find(expected_text)
    if position < 0:
        return ContainsAnswerDetails(
            normalization, expected_tokens, answer_tokens, None, (), MATCH_MODE_SUBSTRING, None
        )
    found_at = _token_index_at(answer_text, position)
    return ContainsAnswerDetails(
        normalization, expected_tokens, answer_tokens, found_at, (), MATCH_MODE_SUBSTRING, position
    )


def contains_answer_details(
    expected_answer: str,
    given_answer: str,
    options: NormalizationOptions = DEFAULT_NORMALIZATION,
    match_mode: str = WHOLE_WORDS_MODE,
) -> ContainsAnswerDetails:
    normalization = normalization_details(expected_answer, given_answer, options)
    expected_tokens = tuple(normalization.normalized_expected.split())
    answer_tokens = tuple(normalization.normalized_answer.split())
    if match_mode == MATCH_MODE_SUBSTRING:
        return _substring_details(normalization, expected_tokens, answer_tokens)
    if not expected_tokens:
        found_at = 0 if not answer_tokens else None
        return ContainsAnswerDetails(normalization, expected_tokens, answer_tokens, found_at, ())
    window_positions = []
    found_at = None
    for start in range(len(answer_tokens) - len(expected_tokens) + 1):
        window_positions.append(start)
        if answer_tokens[start : start + len(expected_tokens)] == expected_tokens:
            found_at = start
            break
    return ContainsAnswerDetails(normalization, expected_tokens, answer_tokens, found_at, tuple(window_positions))


def _ngrams(tokens: list[str], order: int) -> tuple[tuple[str, ...], ...]:
    return tuple(tuple(tokens[start : start + order]) for start in range(len(tokens) - order + 1))


def ngram_overlap_details(
    expected_answer: str,
    given_answer: str,
    order: int,
    score_type: str = F_MEASURE_TYPE,
    beta: float = DEFAULT_BETA,
    lowercase: bool = True,
) -> NgramOverlapDetails:
    expected_ngrams = _ngrams(word_tokens(expected_answer, lowercase), order)
    answer_ngrams = _ngrams(word_tokens(given_answer, lowercase), order)
    matches = _match_items(expected_ngrams, answer_ngrams)
    precision = _ratio(len(matches), len(answer_ngrams))
    recall = _ratio(len(matches), len(expected_ngrams))
    f_measure = f_beta_score(precision, recall, beta)
    return NgramOverlapDetails(
        order=order,
        expected_ngrams=expected_ngrams,
        answer_ngrams=answer_ngrams,
        overlap_count=len(matches),
        matched_expected_indexes=_expected_indexes(matches),
        matched_answer_indexes=_answer_indexes(matches),
        matches=matches,
        precision=precision,
        recall=recall,
        f_measure=f_measure,
        score_type=score_type,
        beta=beta,
        score=_selected_score(score_type, precision, recall, f_measure),
    )


def _lcs_table(expected_tokens: tuple[str, ...], answer_tokens: tuple[str, ...]) -> list[list[int]]:
    table = [[0] * (len(answer_tokens) + 1) for _ in range(len(expected_tokens) + 1)]
    for row, expected_token in enumerate(expected_tokens, start=1):
        for column, answer_token in enumerate(answer_tokens, start=1):
            if expected_token == answer_token:
                table[row][column] = table[row - 1][column - 1] + 1
            else:
                table[row][column] = max(table[row - 1][column], table[row][column - 1])
    return table


def _lcs_traceback(
    table: list[list[int]], expected_tokens: tuple[str, ...], answer_tokens: tuple[str, ...]
) -> tuple[tuple[tuple[int, int], ...], tuple[tuple[int, int], ...]]:
    row, column = len(expected_tokens), len(answer_tokens)
    path = [(row, column)]
    matched_cells = []
    while row > 0 and column > 0:
        if expected_tokens[row - 1] == answer_tokens[column - 1]:
            matched_cells.append((row - 1, column - 1))
            row, column = row - 1, column - 1
        elif table[row - 1][column] >= table[row][column - 1]:
            row -= 1
        else:
            column -= 1
        path.append((row, column))
    return tuple(path), tuple(reversed(matched_cells))


def lcs_details(
    expected_answer: str,
    given_answer: str,
    score_type: str = F_MEASURE_TYPE,
    beta: float = DEFAULT_BETA,
    lowercase: bool = True,
) -> LcsDetails:
    expected_tokens = tuple(word_tokens(expected_answer, lowercase))
    answer_tokens = tuple(word_tokens(given_answer, lowercase))
    table = _lcs_table(expected_tokens, answer_tokens)
    path, matched_cells = _lcs_traceback(table, expected_tokens, answer_tokens)
    lcs_length = table[-1][-1]
    precision = _ratio(lcs_length, len(answer_tokens))
    recall = _ratio(lcs_length, len(expected_tokens))
    f_measure = f_beta_score(precision, recall, beta)
    return LcsDetails(
        expected_tokens=expected_tokens,
        answer_tokens=answer_tokens,
        table=tuple(tuple(row) for row in table),
        path=path,
        matched_cells=matched_cells,
        lcs_length=lcs_length,
        precision=precision,
        recall=recall,
        f_measure=f_measure,
        score_type=score_type,
        beta=beta,
        score=_selected_score(score_type, precision, recall, f_measure),
    )
