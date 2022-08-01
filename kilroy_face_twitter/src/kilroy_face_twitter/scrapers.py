from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import AsyncIterable, Generic, Iterable, Optional, Tuple

from kilroy_face_server_py_sdk import (
    BaseState,
    Categorizable,
    ConfigurableWithLoadableState,
    Parameter,
    StateType,
)
from tweepy import Tweet

from kilroy_face_twitter.client import TwitterClient
from kilroy_face_twitter.models import TweetFields, TweetIncludes


class Scraper(
    ConfigurableWithLoadableState[StateType],
    Categorizable,
    Generic[StateType],
    ABC,
):
    @abstractmethod
    def scrap(
        self,
        client: TwitterClient,
        fields: TweetFields,
        before: Optional[datetime] = None,
        after: Optional[datetime] = None,
    ) -> AsyncIterable[Tuple[Tweet, TweetIncludes]]:
        pass


# Timeline


@dataclass
class TimelineScraperState(BaseState):
    pass


class TimelineScraper(Scraper[TimelineScraperState]):
    @classmethod
    def category(cls) -> str:
        return "timeline"

    async def scrap(
        self,
        client: TwitterClient,
        fields: TweetFields,
        before: Optional[datetime] = None,
        after: Optional[datetime] = None,
    ) -> AsyncIterable[Tuple[Tweet, TweetIncludes]]:
        response = await client.v2.get_me(user_fields=["id"])
        me = response.data

        fields = fields + TweetFields(
            expansions=["author_id"], tweet_fields=["author_id"]
        )

        params = {}
        if after is not None:
            params["start_time"] = after
        if before is not None:
            params["end_time"] = before
        for name, values in fields.to_kwargs().items():
            if values is not None:
                params[name] = values

        while True:
            response = await client.v2.get_home_timeline(**params)
            includes = TweetIncludes.from_response(response)

            for tweet in response.data or []:
                if tweet.author_id != me.id:
                    yield tweet, includes

            if "next_token" not in response.meta:
                break

            params["pagination_token"] = response.meta["next_token"]

    async def _create_initial_state(self) -> TimelineScraperState:
        return TimelineScraperState()

    async def _get_parameters(self) -> Iterable[Parameter]:
        return []
