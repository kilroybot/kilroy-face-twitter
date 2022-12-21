from abc import ABC, abstractmethod

from kilroy_face_server_py_sdk import Categorizable, classproperty, normalize
from tweepy import Tweet

from kilroy_face_twitter.client import TwitterClient
from kilroy_face_twitter.data import TweetFields, TweetIncludes


class Scorer(Categorizable, ABC):
    # noinspection PyMethodParameters
    @classproperty
    def category(cls) -> str:
        name: str = cls.__name__
        return normalize(name.removesuffix("Scorer"))

    @abstractmethod
    async def score(
        self, client: TwitterClient, tweet: Tweet, includes: TweetIncludes
    ) -> float:
        pass

    # noinspection PyMethodParameters
    @classproperty
    @abstractmethod
    def needed_fields(cls) -> TweetFields:
        pass


# Likes


class LikesScorer(Scorer):
    async def score(
        self, client: TwitterClient, tweet: Tweet, includes: TweetIncludes
    ) -> float:
        return tweet.public_metrics["like_count"]

    # noinspection PyMethodParameters
    @classproperty
    def needed_fields(cls) -> TweetFields:
        return TweetFields(tweet_fields=["public_metrics"])


# Retweets


class RetweetsScorer(Scorer):
    async def score(
        self, client: TwitterClient, tweet: Tweet, includes: TweetIncludes
    ) -> float:
        return tweet.public_metrics["retweet_count"]

    # noinspection PyMethodParameters
    @classproperty
    def needed_fields(cls) -> TweetFields:
        return TweetFields(tweet_fields=["public_metrics"])


# Impressions


class ImpressionsScorer(Scorer):
    async def score(
        self, client: TwitterClient, tweet: Tweet, includes: TweetIncludes
    ) -> float:
        return tweet.non_public_metrics["impression_count"]

    # noinspection PyMethodParameters
    @classproperty
    def needed_fields(cls) -> TweetFields:
        return TweetFields(tweet_fields=["non_public_metrics"])
