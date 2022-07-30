from typing import Literal, TypeVar

from kilroy_face_twitter.utils import Deepcopyable

StateType = TypeVar("StateType", bound=Deepcopyable)
PostType = Literal["text", "image", "text+image"]
ScoringType = Literal["likes", "retweets", "impressions"]
ScrapingType = Literal["timeline"]
