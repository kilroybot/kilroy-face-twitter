from abc import ABC, abstractmethod
from datetime import datetime
from typing import AsyncIterable, Optional, Tuple

from kilroy_face_server_py_sdk import Categorizable, classproperty, normalize
from tweepy import Tweet

from kilroy_face_twitter.client import TwitterClient
from kilroy_face_twitter.data import TweetFields, TweetIncludes


class Scraper(Categorizable, ABC):
    # noinspection PyMethodParameters
    @classproperty
    def category(cls) -> str:
        name: str = cls.__name__
        return normalize(name.removesuffix("Scraper"))

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


class TimelineScraper(Scraper):
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
