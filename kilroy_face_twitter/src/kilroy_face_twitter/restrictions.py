import json
from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Any

from detoxify import Detoxify
from kilroy_face_py_shared import SerializableModel
from kilroy_face_server_py_sdk import Categorizable, classproperty, normalize
from kilroy_server_py_utils import Configurable, Parameter, background

from kilroy_face_twitter.models import ToxicityModelLoader
from kilroy_face_twitter.post import PostData


class Restriction(Categorizable, ABC):
    # noinspection PyMethodParameters
    @classproperty
    def category(cls) -> str:
        name: str = cls.__name__
        return normalize(name.removesuffix("Restriction"))

    @abstractmethod
    async def check(self, data: PostData) -> bool:
        pass


# Toxicity


class ToxicityRestrictionParams(SerializableModel):
    threshold: float = 0.8


@dataclass
class ToxicityRestrictionState:
    detoxify: Detoxify
    threshold: float


class ToxicityRestriction(Restriction, Configurable[ToxicityRestrictionState]):
    class ThresholdParameter(Parameter[ToxicityRestrictionState, float]):
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

    async def _build_default_state(self) -> ToxicityRestrictionState:
        params = ToxicityRestrictionParams(**self._kwargs)
        return ToxicityRestrictionState(
            detoxify=await background(ToxicityModelLoader.get),
            threshold=params.threshold,
        )

    @classmethod
    async def _save_state(
        cls, state: ToxicityRestrictionState, directory: Path
    ) -> None:
        state_dict = {"threshold": state.threshold}
        with open(directory / "state.json", "w") as f:
            json.dump(state_dict, f)

    async def _load_saved_state(
        self, directory: Path
    ) -> ToxicityRestrictionState:
        params = ToxicityRestrictionState(**self._kwargs)
        with open(directory / "state.json", "r") as f:
            state_dict = json.load(f)
        return ToxicityRestrictionState(
            detoxify=await background(ToxicityModelLoader.get),
            threshold=state_dict.get("threshold", params.threshold),
        )

    async def cleanup(self) -> None:
        await background(ToxicityModelLoader.release)

    async def check(self, data: PostData) -> bool:
        if data.text is None:
            return True
        async with self.state.read_lock() as state:
            toxicity = state.detoxify.predict(data.text.content)["toxicity"]
            return toxicity < state.threshold
