from collections.abc import Iterable

from presentation.views.metric_explorer.scenes.base_scene import WalkthroughScene
from presentation.views.metric_explorer.scenes.bleu_scene import BleuScene
from presentation.views.metric_explorer.scenes.chrf_scene import ChrfScene
from presentation.views.metric_explorer.scenes.contains_answer_scene import ContainsAnswerScene
from presentation.views.metric_explorer.scenes.embedding_scene import EmbeddingScene
from presentation.views.metric_explorer.scenes.exact_match_scene import ExactMatchScene
from presentation.views.metric_explorer.scenes.llm_judge_scene import LlmJudgeScene
from presentation.views.metric_explorer.scenes.rouge_l_scene import RougeLScene
from presentation.views.metric_explorer.scenes.rouge_n_scene import RougeNScene
from presentation.views.metric_explorer.scenes.token_f1_scene import TokenF1Scene
from presentation.views.metric_explorer.scenes.token_recall_scene import TokenRecallScene

UNKNOWN_SCENE_MESSAGE = "There is no scene for the metric {identifier!r}."
UNIGRAM_ORDER = 1
BIGRAM_ORDER = 2


class SceneRegistry:
    def __init__(self, scenes: Iterable[WalkthroughScene]):
        self._scenes = {scene.identifier: scene for scene in scenes}

    @property
    def identifiers(self) -> tuple[str, ...]:
        return tuple(self._scenes)

    def scene_for(self, identifier: str) -> WalkthroughScene:
        scene = self._scenes.get(identifier)
        if scene is None:
            raise KeyError(UNKNOWN_SCENE_MESSAGE.format(identifier=identifier))
        return scene

    def step_durations(self, identifier: str) -> tuple[float, ...]:
        return self.scene_for(identifier).step_durations


def build_scene_registry() -> SceneRegistry:
    return SceneRegistry(
        (
            EmbeddingScene(),
            ExactMatchScene(),
            TokenF1Scene(),
            TokenRecallScene(),
            ContainsAnswerScene(),
            RougeNScene(UNIGRAM_ORDER),
            RougeNScene(BIGRAM_ORDER),
            RougeLScene(),
            BleuScene(),
            ChrfScene(),
            LlmJudgeScene(),
        )
    )
