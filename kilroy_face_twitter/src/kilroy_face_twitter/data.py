from dataclasses import dataclass
from typing import Any, Dict, List, Literal, Optional, TypeVar

from pydantic import BaseModel
from tweepy import (
    List as TwitterList,
    Media,
    Place,
    Poll,
    Response,
    Space,
    User,
)

T = TypeVar("T")

Expansion = Literal[
    "attachments.poll_ids",
    "attachments.media_keys",
    "author_id",
    "entities.mentions.username",
    "geo.place_id",
    "in_reply_to_user_id",
    "referenced_tweets.id",
    "referenced_tweets.id.author_id",
]

MediaField = Literal[
    "duration_ms",
    "height",
    "media_key",
    "preview_image_url",
    "type",
    "url",
    "width",
    "public_metrics",
    "non_public_metrics",
    "organic_metrics",
    "promoted_metrics",
    "alt_text",
    "variants",
]

PlaceField = Literal[
    "contained_within",
    "country",
    "country_code",
    "full_name",
    "geo",
    "id",
    "name",
    "place_type",
]

PollField = Literal[
    "duration_minutes", "end_datetime", "id", "options", "voting_status"
]

TweetField = Literal[
    "attachments",
    "author_id",
    "context_annotations",
    "conversation_id",
    "created_at",
    "entities",
    "geo",
    "id",
    "in_reply_to_user_id",
    "lang",
    "non_public_metrics",
    "public_metrics",
    "organic_metrics",
    "promoted_metrics",
    "possibly_sensitive",
    "referenced_tweets",
    "reply_settings",
    "source",
    "text",
    "withheld",
]

UserField = Literal[
    "created_at",
    "description",
    "entities",
    "id",
    "location",
    "name",
    "pinned_tweet_id",
    "profile_image_url",
    "protected",
    "public_metrics",
    "url",
    "username",
    "verified",
    "withheld",
]


class TweetFields(BaseModel):
    expansions: Optional[List[Expansion]] = None
    media_fields: Optional[List[MediaField]] = None
    place_fields: Optional[List[PlaceField]] = None
    poll_fields: Optional[List[PollField]] = None
    tweet_fields: Optional[List[TweetField]] = None
    user_fields: Optional[List[UserField]] = None

    def __add__(self, other):
        def merge(
            a: Optional[List[T]], b: Optional[List[T]]
        ) -> Optional[List[T]]:
            return list(set((a or []) + (b or []))) or None

        if isinstance(other, TweetFields):
            return TweetFields(
                expansions=merge(self.expansions, other.expansions),
                media_fields=merge(self.media_fields, other.media_fields),
                place_fields=merge(self.place_fields, other.place_fields),
                poll_fields=merge(self.poll_fields, other.poll_fields),
                tweet_fields=merge(self.tweet_fields, other.tweet_fields),
                user_fields=merge(self.user_fields, other.user_fields),
            )
        else:
            raise ValueError(f"Can't add TweetFields to {type(other)}")

    def to_kwargs(self) -> Dict[str, Any]:
        return self.dict(exclude_none=True)


@dataclass
class TweetIncludes:
    lists: Optional[List[TwitterList]] = None
    media: Optional[List[Media]] = None
    places: Optional[List[Place]] = None
    polls: Optional[List[Poll]] = None
    spaces: Optional[List[Space]] = None
    users: Optional[List[User]] = None

    @staticmethod
    def from_response(response: Response) -> "TweetIncludes":
        return TweetIncludes(**(response.includes or {}))
