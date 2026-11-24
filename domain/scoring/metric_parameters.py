from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from enum import Enum

from domain.errors import DomainError

ParameterValue = bool | int | float | str
ParameterValues = Mapping[str, ParameterValue]

UNKNOWN_PARAMETER_MESSAGE = "Unknown parameter {key!r}."
EXPECTED_TYPE_MESSAGE = "{label} must be {expected}."
INVALID_CHOICE_MESSAGE = "{label} must be one of: {options}."
BELOW_MINIMUM_MESSAGE = "{label} must be at least {minimum}."
ABOVE_MAXIMUM_MESSAGE = "{label} must be at most {maximum}."


class ParameterKind(Enum):
    BOOLEAN = "boolean"
    INTEGER = "integer"
    DECIMAL = "decimal"
    CHOICE = "choice"
    TEXT = "text"


class InvalidParameterError(DomainError):
    pass


@dataclass(frozen=True)
class ParameterChoice:
    value: str
    label: str


@dataclass(frozen=True)
class ParameterSpec:
    key: str
    label: str
    description: str
    kind: ParameterKind
    default: ParameterValue
    choices: tuple[ParameterChoice, ...] = ()
    minimum: float | None = None
    maximum: float | None = None
    step: float | None = None
    decimals: int = 2


def default_parameters(specs: Sequence[ParameterSpec]) -> dict[str, ParameterValue]:
    return {spec.key: spec.default for spec in specs}


def validate_parameters(
    specs: Sequence[ParameterSpec], values: ParameterValues
) -> dict[str, ParameterValue]:
    specs_by_key = {spec.key: spec for spec in specs}
    for key in values:
        if key not in specs_by_key:
            raise InvalidParameterError(UNKNOWN_PARAMETER_MESSAGE.format(key=key))
    validated: dict[str, ParameterValue] = {}
    for key, spec in specs_by_key.items():
        validated[key] = _validate_value(spec, values.get(key, spec.default))
    return validated


def _validate_value(spec: ParameterSpec, value: ParameterValue) -> ParameterValue:
    if spec.kind is ParameterKind.BOOLEAN:
        return _require_type(spec, value, isinstance(value, bool), "true or false")
    if spec.kind is ParameterKind.TEXT:
        return _require_type(spec, value, isinstance(value, str), "text")
    if spec.kind is ParameterKind.CHOICE:
        return _validate_choice(spec, value)
    if spec.kind is ParameterKind.INTEGER:
        is_integer = isinstance(value, int) and not isinstance(value, bool)
        _require_type(spec, value, is_integer, "a whole number")
        return _check_range(spec, value)
    is_number = isinstance(value, (int, float)) and not isinstance(value, bool)
    _require_type(spec, value, is_number, "a number")
    return _check_range(spec, float(value))


def _require_type(
    spec: ParameterSpec, value: ParameterValue, is_valid: bool, expected: str
) -> ParameterValue:
    if not is_valid:
        raise InvalidParameterError(EXPECTED_TYPE_MESSAGE.format(label=spec.label, expected=expected))
    return value


def _validate_choice(spec: ParameterSpec, value: ParameterValue) -> ParameterValue:
    options = [choice.value for choice in spec.choices]
    if not isinstance(value, str) or value not in options:
        raise InvalidParameterError(
            INVALID_CHOICE_MESSAGE.format(label=spec.label, options=", ".join(options))
        )
    return value


def _check_range(spec: ParameterSpec, value: int | float) -> int | float:
    if spec.minimum is not None and value < spec.minimum:
        raise InvalidParameterError(
            BELOW_MINIMUM_MESSAGE.format(label=spec.label, minimum=spec.minimum)
        )
    if spec.maximum is not None and value > spec.maximum:
        raise InvalidParameterError(
            ABOVE_MAXIMUM_MESSAGE.format(label=spec.label, maximum=spec.maximum)
        )
    return value
