from collections.abc import Mapping
from dataclasses import dataclass, field


@dataclass(frozen=True)
class MetricWalkthrough:
    identifier: str
    expected_answer: str
    given_answer: str
    final_score: float
    details: object
    parameters: Mapping[str, object] = field(default_factory=dict)
