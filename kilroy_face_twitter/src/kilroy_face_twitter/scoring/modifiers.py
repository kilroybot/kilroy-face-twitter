import json
from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Any

import numpy as np
from detoxify import Detoxify
from kilroy_face_py_shared import SerializableModel
from kilroy_face_server_py_sdk import Categorizable, classproperty, normalize
from kilroy_server_py_utils import Configurable, Parameter, background
from tweepy import Tweet

from kilroy_face_twitter.data import TweetFields, TweetIncludes
from kilroy_face_twitter.models import ToxicityModelLoader


class ScoreModifier(Categorizable, ABC):
    # noinspection PyMethodParameters
    @classproperty
    def category(cls) -> str:
        name: str = cls.__name__
        return normalize(name.removesuffix("ScoreModifier"))

    # noinspection PyMethodParameters
    @classproperty
    @abstractmethod
    def needed_fields(cls) -> TweetFields:
        pass

    @abstractmethod
    async def modify(
        self, tweet: Tweet, includes: TweetIncludes, score: float
    ) -> float:
        pass


# Toxicity


class ToxicityScoreModifierParams(SerializableModel):
    threshold: float = 0.8
    alpha: float = 0.9


@dataclass
class ToxicityScoreModifierState:
    detoxify: Detoxify
    threshold: float
    alpha: float


class ToxicityScoreModifier(
    ScoreModifier, Configurable[ToxicityScoreModifierState]
):
    class ThresholdParameter(Parameter[ToxicityScoreModifierState, float]):
        # noinspection PyMethodParameters
        @classproperty
        def schema(cls) -> Dict[str, Any]:
            return {
                "type": "number",
                "minimum": 0,
                "maximum": 1,
                "title": cls.pretty_name,
                "default": 0.8,
            }

    class AlphaParameter(Parameter[ToxicityScoreModifierState, float]):
        # noinspection PyMethodParameters
        @classproperty
        def schema(cls) -> Dict[str, Any]:
            return {
                "type": "number",
                "minimum": 0,
                "maximum": 1,
                "title": cls.pretty_name,
                "default": 0.9,
            }

    async def _build_default_state(self) -> ToxicityScoreModifierState:
        params = ToxicityScoreModifierParams(**self._kwargs)
        return ToxicityScoreModifierState(
            detoxify=await background(ToxicityModelLoader.get),
            threshold=params.threshold,
            alpha=params.alpha,
        )

    @classmethod
    async def _save_state(
        cls, state: ToxicityScoreModifierState, directory: Path
    ) -> None:
        state_dict = {
            "threshold": state.threshold,
            "alpha": state.alpha,
        }
        with open(directory / "state.json", "w") as f:
            json.dump(state_dict, f)

    async def _load_saved_state(
        self, directory: Path
    ) -> ToxicityScoreModifierState:
        params = ToxicityScoreModifierParams(**self._kwargs)
        with open(directory / "state.json", "r") as f:
            state_dict = json.load(f)
        return ToxicityScoreModifierState(
            detoxify=await background(ToxicityModelLoader.get),
            threshold=state_dict.get("threshold", params.threshold),
            alpha=state_dict.get("alpha", params.alpha),
        )

    async def cleanup(self) -> None:
        await background(ToxicityModelLoader.release)

    # noinspection PyMethodParameters
    @classproperty
    def needed_fields(cls) -> TweetFields:
        return TweetFields(tweet_fields=["text"])

    async def modify(
        self, tweet: Tweet, includes: TweetIncludes, score: float
    ) -> float:
        async with self.state.read_lock() as state:
            toxicity = state.detoxify.predict(tweet.text)["toxicity"]
            threshold = state.threshold
            alpha = state.alpha
        return self.modifier(toxicity, threshold, alpha) * score

    @staticmethod
    def modifier(x: float, threshold: float, alpha: float) -> float:
        x = np.clip(x, 0, 1).item()
        threshold = np.clip(threshold, 0, 1).item()
        alpha = np.clip(alpha, 0, 1).item()

        if x == 0 or x == 1:
            return 1 - x
        if threshold == 0:
            return 0
        if threshold == 1:
            return 1
        if alpha == 1 and x == threshold:
            return 1

        inner_exponent = (-np.log(2) / np.log(threshold)).item()
        outer_exponent = 1 / (1 - alpha)
        inner_value = x**inner_exponent
        denominator = 1 + (inner_value / (1 - inner_value)) ** outer_exponent
        return 1 / denominator
