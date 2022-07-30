from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import AsyncIterable, Generic, Optional, Tuple, Type

from tweepy import Tweet

from kilroy_face_twitter.client import TwitterClient
from kilroy_face_twitter.face.models import TweetFields, TweetIncludes
from kilroy_face_twitter.face.utils import Configurable
from kilroy_face_twitter.types import ScrapingType, StateType
from kilroy_face_twitter.utils import Deepcopyable


class Scraper(Configurable[StateType], Generic[StateType], ABC):
    @abstractmethod
    def scrap(
        self,
        client: TwitterClient,
        fields: TweetFields,
        before: Optional[datetime] = None,
        after: Optional[datetime] = None,
    ) -> AsyncIterable[Tuple[Tweet, TweetIncludes]]:
        pass

    @staticmethod
    @abstractmethod
    def scraping_type() -> ScrapingType:
        pass

    @classmethod
    def for_type(cls, scraping_type: ScrapingType) -> Type["Scraper"]:
        for scorer in cls.__subclasses__():
            if scorer.scraping_type() == scraping_type:
                return scorer
        raise ValueError(f'Scraper for type "{scraping_type}" not found.')


# Timeline


@dataclass
class TimelineScraperState(Deepcopyable):
    pass


class TimelineScraper(Scraper[TimelineScraperState]):
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

    @staticmethod
    def scraping_type() -> ScrapingType:
        return "timeline"

    async def _create_initial_state(self) -> TimelineScraperState:
        return TimelineScraperState()
