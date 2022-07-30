import os
from typing import Any, Dict

from pydantic import BaseModel

from kilroy_face_twitter.types import PostType, ScoringType, ScrapingType


class FaceConfig(BaseModel):
    consumer_key: str
    consumer_secret: str
    access_token: str
    access_token_secret: str
    post_type: PostType
    processors_params: Dict[str, Dict[str, Any]] = {}
    default_scoring_type: ScoringType
    scorers_params: Dict[str, Dict[str, Any]] = {}
    default_scraping_type: ScrapingType
    scrapers_params: Dict[str, Dict[str, Any]] = {}

    @classmethod
    def build(cls, **kwargs) -> "FaceConfig":
        return cls(
            consumer_key=kwargs.get(
                "consumer_key", os.getenv("KILROY_FACE_TWITTER_CONSUMER_KEY")
            ),
            consumer_secret=kwargs.get(
                "consumer_secret",
                os.getenv("KILROY_FACE_TWITTER_CONSUMER_SECRET"),
            ),
            access_token=kwargs.get(
                "access_token", os.getenv("KILROY_FACE_TWITTER_ACCESS_TOKEN")
            ),
            access_token_secret=kwargs.get(
                "access_token_secret",
                os.getenv("KILROY_FACE_TWITTER_ACCESS_TOKEN_SECRET"),
            ),
            post_type=kwargs.get(
                "post_type",
                os.getenv("KILROY_FACE_TWITTER_POST_TYPE", "text"),
            ),
            default_scoring_type=kwargs.get(
                "scoring_type",
                os.getenv("KILROY_FACE_TWITTER_DEFAULT_SCORING_TYPE", "likes"),
            ),
            default_scraping_type=kwargs.get(
                "scraping_type",
                os.getenv(
                    "KILROY_FACE_TWITTER_DEFAULT_SCRAPING_TYPE", "timeline"
                ),
            ),
        )


class ServerConfig(BaseModel):
    host: str
    port: int

    @classmethod
    def build(cls, **kwargs) -> "ServerConfig":
        return cls(
            host=kwargs.get(
                "host", os.getenv("KILROY_FACE_TWITTER_HOST", "localhost")
            ),
            port=kwargs.get(
                "port", os.getenv("KILROY_FACE_TWITTER_PORT", 10001)
            ),
        )
