from abc import ABC, abstractmethod
from collections.abc import Mapping

from domain.explanations.walkthrough_details import BleuDetails, ChrfDetails


class TranslationStatisticsProvider(ABC):
    @abstractmethod
    def bleu_details(
        self, answer: str, reference: str, parameters: Mapping[str, object] | None = None
    ) -> BleuDetails:
        ...

    @abstractmethod
    def chrf_details(
        self, answer: str, reference: str, parameters: Mapping[str, object] | None = None
    ) -> ChrfDetails:
        ...
