from threading import Lock
from typing import Optional

from detoxify import Detoxify


def fetch_models() -> None:
    ToxicityModelLoader.get()
    ToxicityModelLoader.release()


class ToxicityModelLoader:
    model: Optional[Detoxify] = None
    reference_count: int = 0
    lock: Lock = Lock()

    @classmethod
    def get(cls) -> Detoxify:
        with cls.lock:
            if cls.model is None:
                cls.model = Detoxify("multilingual")
            cls.reference_count += 1
            return cls.model

    @classmethod
    def release(cls) -> None:
        with cls.lock:
            cls.reference_count -= 1
            if cls.reference_count == 0:
                cls.model = None
