from detoxify import Detoxify


def fetch_model() -> None:
    load_model()


def load_model() -> Detoxify:
    return Detoxify("multilingual")
