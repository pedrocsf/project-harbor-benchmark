from abc import ABC, abstractmethod

from domain.entities.rag_answer import RagAnswer
from domain.entities.rag_endpoint_settings import RagEndpointSettings


class RagGateway(ABC):
    @abstractmethod
    def ask(self, settings: RagEndpointSettings, question_text: str) -> RagAnswer:
        ...
