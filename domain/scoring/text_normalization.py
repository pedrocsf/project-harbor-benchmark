import re
import string
import unicodedata
from collections.abc import Callable, Mapping
from dataclasses import dataclass

from domain.scoring.metric_parameters import ParameterChoice, ParameterKind, ParameterSpec

ARTICLE_SETS: dict[str, tuple[str, ...]] = {
    "english": ("a", "an", "the"),
    "portuguese": ("o", "a", "os", "as", "um", "uma", "uns", "umas"),
    "english_portuguese": ("a", "an", "the", "o", "os", "as", "um", "uma", "uns", "umas"),
    "none": (),
}
DEFAULT_ARTICLE_SET = "english"
ASCII_PUNCTUATION = frozenset(string.punctuation)
WORD_PATTERN = re.compile(r"\w+")
COMBINING_MARK_CATEGORY = "Mn"
DECOMPOSITION_FORM = "NFKD"

STAGE_LOWERCASE = "Lowercase"
STAGE_STRIP_ACCENTS = "Strip accents"
STAGE_REMOVE_PUNCTUATION = "Remove punctuation"
STAGE_REMOVE_ARTICLES = "Remove articles"
STAGE_COLLAPSE_WHITESPACE = "Collapse whitespace"

UNKNOWN_ARTICLE_SET_MESSAGE = "Unknown article set {name!r}."


@dataclass(frozen=True)
class NormalizationOptions:
    lowercase: bool = True
    strip_accents: bool = False
    remove_punctuation: bool = True
    articles: str = DEFAULT_ARTICLE_SET


DEFAULT_NORMALIZATION = NormalizationOptions()


def _is_punctuation(character: str) -> bool:
    return character in ASCII_PUNCTUATION or unicodedata.category(character).startswith("P")


def lowercase_text(text: str) -> str:
    return text.lower()


def strip_accents(text: str) -> str:
    decomposed = unicodedata.normalize(DECOMPOSITION_FORM, text)
    return "".join(
        character
        for character in decomposed
        if unicodedata.category(character) != COMBINING_MARK_CATEGORY
    )


def remove_punctuation(text: str) -> str:
    return "".join(character for character in text if not _is_punctuation(character))


def _article_remover(article_set_name: str) -> Callable[[str], str]:
    if article_set_name not in ARTICLE_SETS:
        raise ValueError(UNKNOWN_ARTICLE_SET_MESSAGE.format(name=article_set_name))
    articles = ARTICLE_SETS[article_set_name]
    pattern = re.compile(r"\b(" + "|".join(articles) + r")\b", re.IGNORECASE)

    def remove(text: str) -> str:
        return pattern.sub(" ", text)

    return remove


def remove_articles(text: str) -> str:
    return _article_remover(DEFAULT_ARTICLE_SET)(text)


def collapse_whitespace(text: str) -> str:
    return " ".join(text.split())


def active_normalization_stages(
    options: NormalizationOptions = DEFAULT_NORMALIZATION,
) -> tuple[tuple[str, Callable[[str], str]], ...]:
    stages: list[tuple[str, Callable[[str], str]]] = []
    if options.lowercase:
        stages.append((STAGE_LOWERCASE, lowercase_text))
    if options.strip_accents:
        stages.append((STAGE_STRIP_ACCENTS, strip_accents))
    if options.remove_punctuation:
        stages.append((STAGE_REMOVE_PUNCTUATION, remove_punctuation))
    if ARTICLE_SETS.get(options.articles, None) != ():
        stages.append((STAGE_REMOVE_ARTICLES, _article_remover(options.articles)))
    stages.append((STAGE_COLLAPSE_WHITESPACE, collapse_whitespace))
    return tuple(stages)


NORMALIZATION_STAGES = active_normalization_stages()


def normalization_stages(
    text: str, options: NormalizationOptions = DEFAULT_NORMALIZATION
) -> tuple[str, ...]:
    outputs = []
    current_text = text
    for _, transform in active_normalization_stages(options):
        current_text = transform(current_text)
        outputs.append(current_text)
    return tuple(outputs)


def normalize_answer(text: str, options: NormalizationOptions = DEFAULT_NORMALIZATION) -> str:
    return normalization_stages(text, options)[-1]


def normalized_tokens(text: str, options: NormalizationOptions = DEFAULT_NORMALIZATION) -> list[str]:
    return normalize_answer(text, options).split()


def word_tokens(text: str, lowercase: bool = True) -> list[str]:
    return WORD_PATTERN.findall(text.lower() if lowercase else text)


NORMALIZATION_PARAMETER_SPECS: tuple[ParameterSpec, ...] = (
    ParameterSpec(
        key="lowercase",
        label="Lowercase",
        description="Convert all text to lowercase, so 'Paris' and 'paris' count as the same word.",
        kind=ParameterKind.BOOLEAN,
        default=True,
    ),
    ParameterSpec(
        key="strip_accents",
        label="Strip accents",
        description="Remove accents from letters, so 'avó' and 'avo' count as the same word.",
        kind=ParameterKind.BOOLEAN,
        default=False,
    ),
    ParameterSpec(
        key="remove_punctuation",
        label="Remove punctuation",
        description="Delete punctuation marks before comparing, so 'yes!' matches 'yes'.",
        kind=ParameterKind.BOOLEAN,
        default=True,
    ),
    ParameterSpec(
        key="remove_articles",
        label="Remove articles",
        description="Drop the selected articles as whole words, so 'the cat' matches 'cat'.",
        kind=ParameterKind.CHOICE,
        default=DEFAULT_ARTICLE_SET,
        choices=(
            ParameterChoice("english", "English (a, an, the)"),
            ParameterChoice("portuguese", "Portuguese (o, a, os, as, um, uma, uns, umas)"),
            ParameterChoice("english_portuguese", "English and Portuguese"),
            ParameterChoice("none", "Keep all articles"),
        ),
    ),
)


def normalization_options_from(parameters: Mapping) -> NormalizationOptions:
    return NormalizationOptions(
        lowercase=parameters["lowercase"],
        strip_accents=parameters["strip_accents"],
        remove_punctuation=parameters["remove_punctuation"],
        articles=parameters["remove_articles"],
    )
