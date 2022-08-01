from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Generic, Iterable

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


class Scorer(
    ConfigurableWithLoadableState[StateType],
    Categorizable,
    Generic[StateType],
    ABC,
):
    @abstractmethod
    async def score(
        self, client: TwitterClient, tweet: Tweet, includes: TweetIncludes
    ) -> float:
        pass

    @staticmethod
    @abstractmethod
    def needed_fields() -> TweetFields:
        pass


# Likes


@dataclass
class LikesScorerState(BaseState):
    pass


class LikesScorer(Scorer[LikesScorerState]):
    @classmethod
    def category(cls) -> str:
        return "likes"

    async def score(
        self, client: TwitterClient, tweet: Tweet, includes: TweetIncludes
    ) -> float:
        return tweet.public_metrics["like_count"]

    @staticmethod
    def needed_fields() -> TweetFields:
        return TweetFields(tweet_fields=["public_metrics"])

    async def _create_initial_state(self) -> LikesScorerState:
        return LikesScorerState()

    async def _get_parameters(self) -> Iterable[Parameter]:
        return []


# Retweets


@dataclass
class RetweetsScorerState(BaseState):
    pass


class RetweetsScorer(Scorer[RetweetsScorerState]):
    @classmethod
    def category(cls) -> str:
        return "retweets"

    async def score(
        self, client: TwitterClient, tweet: Tweet, includes: TweetIncludes
    ) -> float:
        return tweet.public_metrics["retweet_count"]

    @staticmethod
    def needed_fields() -> TweetFields:
        return TweetFields(tweet_fields=["public_metrics"])

    async def _create_initial_state(self) -> RetweetsScorerState:
        return RetweetsScorerState()

    async def _get_parameters(self) -> Iterable[Parameter]:
        return []


# Impressions


@dataclass
class ImpressionsScorerState(BaseState):
    pass


class ImpressionsScorer(Scorer[ImpressionsScorerState]):
    @classmethod
    def category(cls) -> str:
        return "impressions"

    async def score(
        self, client: TwitterClient, tweet: Tweet, includes: TweetIncludes
    ) -> float:
        return tweet.non_public_metrics["impression_count"]

    @staticmethod
    def needed_fields() -> TweetFields:
        return TweetFields(tweet_fields=["non_public_metrics"])

    async def _create_initial_state(self) -> ImpressionsScorerState:
        return ImpressionsScorerState()

    async def _get_parameters(self) -> Iterable[Parameter]:
        return []
