import pytest

from domain.scoring.metric_parameters import (
    InvalidParameterError,
    ParameterChoice,
    ParameterKind,
    ParameterSpec,
    default_parameters,
    validate_parameters,
)
from domain.scoring.scoring_method import ScoreKind, ScoringMethod

FLAG = ParameterSpec("flag", "Flag", "A flag", ParameterKind.BOOLEAN, True)
COUNT = ParameterSpec("count", "Count", "A count", ParameterKind.INTEGER, 2, minimum=1, maximum=5)
RATIO = ParameterSpec("ratio", "Ratio", "A ratio", ParameterKind.DECIMAL, 0.5, minimum=0.0, maximum=1.0)
MODE = ParameterSpec(
    "mode",
    "Mode",
    "A mode",
    ParameterKind.CHOICE,
    "a",
    choices=(ParameterChoice("a", "A"), ParameterChoice("b", "B")),
)
NAME = ParameterSpec("name", "Name", "A name", ParameterKind.TEXT, "x")
ALL_SPECS = (FLAG, COUNT, RATIO, MODE, NAME)
MAXIMUM_COUNT = 5
BELOW_MINIMUM_COUNT = 0
ABOVE_MAXIMUM_COUNT = 6


class SampleMethod(ScoringMethod):
    identifier = "sample"
    display_name = "Sample"
    column_header = "Sample"
    score_kind = ScoreKind.CONTINUOUS
    parameter_specs = ALL_SPECS

    def score(self, expected_answer: str, given_answer: str) -> float:
        return 0.0

    def _check_parameters(self, values):
        if values["count"] == MAXIMUM_COUNT and not values["flag"]:
            raise InvalidParameterError("Count of five requires the flag.")


def test_defaults_are_collected_from_specs():
    assert default_parameters(ALL_SPECS) == {
        "flag": True,
        "count": 2,
        "ratio": 0.5,
        "mode": "a",
        "name": "x",
    }


def test_missing_keys_use_defaults():
    assert validate_parameters(ALL_SPECS, {}) == default_parameters(ALL_SPECS)


def test_unknown_key_is_rejected():
    with pytest.raises(InvalidParameterError):
        validate_parameters(ALL_SPECS, {"other": 1})


@pytest.mark.parametrize(
    "key,value",
    [
        ("flag", 1),
        ("count", True),
        ("count", 1.5),
        ("ratio", True),
        ("ratio", "0.5"),
        ("mode", "c"),
        ("mode", 1),
        ("name", 3),
    ],
)
def test_wrong_types_are_rejected(key, value):
    with pytest.raises(InvalidParameterError):
        validate_parameters(ALL_SPECS, {key: value})


def test_error_message_names_the_label():
    with pytest.raises(InvalidParameterError, match="Count"):
        validate_parameters(ALL_SPECS, {"count": ABOVE_MAXIMUM_COUNT})


@pytest.mark.parametrize("value", [BELOW_MINIMUM_COUNT, ABOVE_MAXIMUM_COUNT])
def test_integer_range_is_enforced(value):
    with pytest.raises(InvalidParameterError):
        validate_parameters(ALL_SPECS, {"count": value})


def test_decimal_range_is_enforced():
    with pytest.raises(InvalidParameterError):
        validate_parameters(ALL_SPECS, {"ratio": 1.5})


def test_decimal_accepts_int_and_returns_float():
    result = validate_parameters(ALL_SPECS, {"ratio": 1})
    assert result["ratio"] == 1.0
    assert isinstance(result["ratio"], float)


def test_valid_values_are_returned():
    values = {"flag": False, "count": 3, "ratio": 0.25, "mode": "b", "name": "y"}
    assert validate_parameters(ALL_SPECS, values) == values


def test_method_exposes_defaults():
    method = SampleMethod()
    assert method.parameters == default_parameters(ALL_SPECS)
    assert method.parameter("count") == 2


def test_parameters_returns_new_dict():
    method = SampleMethod()
    method.parameters["count"] = 4
    assert method.parameter("count") == 2


def test_update_merges_with_current_values():
    method = SampleMethod()
    method.update_parameters({"count": 3})
    method.update_parameters({"mode": "b"})
    assert method.parameter("count") == 3
    assert method.parameter("mode") == "b"


def test_invalid_update_keeps_previous_values():
    method = SampleMethod()
    method.update_parameters({"count": 3})
    with pytest.raises(InvalidParameterError):
        method.update_parameters({"count": ABOVE_MAXIMUM_COUNT})
    assert method.parameter("count") == 3


def test_reset_restores_defaults():
    method = SampleMethod()
    method.update_parameters({"count": 3})
    method.reset_parameters()
    assert method.parameters == default_parameters(ALL_SPECS)


def test_check_hook_can_reject_update():
    method = SampleMethod()
    with pytest.raises(InvalidParameterError):
        method.update_parameters({"count": MAXIMUM_COUNT, "flag": False})
    assert method.parameter("count") == 2


def test_instances_are_independent():
    first = SampleMethod()
    second = SampleMethod()
    first.update_parameters({"count": 4})
    assert second.parameter("count") == 2
