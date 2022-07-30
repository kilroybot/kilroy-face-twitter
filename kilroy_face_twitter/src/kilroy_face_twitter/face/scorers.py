from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Generic, Type

from tweepy import Tweet

from kilroy_face_twitter.client import TwitterClient
from kilroy_face_twitter.face.models import TweetFields, TweetIncludes
from kilroy_face_twitter.face.utils import Configurable
from kilroy_face_twitter.types import ScoringType, StateType
from kilroy_face_twitter.utils import Deepcopyable


class Scorer(Configurable[StateType], Generic[StateType], ABC):
    @abstractmethod
    async def score(
        self, client: TwitterClient, tweet: Tweet, includes: TweetIncludes
    ) -> float:
        pass

    @staticmethod
    @abstractmethod
    def scoring_type() -> ScoringType:
        pass

    @staticmethod
    @abstractmethod
    def needed_fields() -> TweetFields:
        pass

    @classmethod
    def for_type(cls, scoring_type: ScoringType) -> Type["Scorer"]:
        for scorer in cls.__subclasses__():
            if scorer.scoring_type() == scoring_type:
                return scorer
        raise ValueError(f'Scorer for type "{scoring_type}" not found.')


# Likes


@dataclass
class LikesScorerState(Deepcopyable):
    pass


class LikesScorer(Scorer[LikesScorerState]):
    async def score(
        self, client: TwitterClient, tweet: Tweet, includes: TweetIncludes
    ) -> float:
        return tweet.public_metrics["like_count"]

    @staticmethod
    def scoring_type() -> ScoringType:
        return "likes"

    @staticmethod
    def needed_fields() -> TweetFields:
        return TweetFields(tweet_fields=["public_metrics"])

    async def _create_initial_state(self) -> LikesScorerState:
        return LikesScorerState()


# Retweets


@dataclass
class RetweetsScorerState(Deepcopyable):
    pass


class RetweetsScorer(Scorer[RetweetsScorerState]):
    async def score(
        self, client: TwitterClient, tweet: Tweet, includes: TweetIncludes
    ) -> float:
        return tweet.public_metrics["retweet_count"]

    @staticmethod
    def scoring_type() -> ScoringType:
        return "retweets"

    @staticmethod
    def needed_fields() -> TweetFields:
        return TweetFields(tweet_fields=["public_metrics"])

    async def _create_initial_state(self) -> RetweetsScorerState:
        return RetweetsScorerState()


# Impressions


@dataclass
class ImpressionsScorerState(Deepcopyable):
    pass


class ImpressionsScorer(Scorer[ImpressionsScorerState]):
    async def score(
        self, client: TwitterClient, tweet: Tweet, includes: TweetIncludes
    ) -> float:
        return tweet.non_public_metrics["impression_count"]

    @staticmethod
    def scoring_type() -> ScoringType:
        return "impressions"

    @staticmethod
    def needed_fields() -> TweetFields:
        return TweetFields(tweet_fields=["non_public_metrics"])

    async def _create_initial_state(self) -> ImpressionsScorerState:
        return ImpressionsScorerState()
