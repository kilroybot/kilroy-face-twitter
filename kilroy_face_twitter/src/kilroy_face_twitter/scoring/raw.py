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


class RelativeLikesScorer(Scorer):
    async def score(
        self, client: TwitterClient, tweet: Tweet, includes: TweetIncludes
    ) -> float:
        likes = tweet.public_metrics["like_count"]
        author = next(
            user for user in includes.users if user.id == tweet.author_id
        )
        followers = author.public_metrics["followers_count"]
        return likes / max(followers, 1)

    # noinspection PyMethodParameters
    @classproperty
    def needed_fields(cls) -> TweetFields:
        return TweetFields(
            expansions=["author_id"],
            tweet_fields=["public_metrics"],
            user_fields=["public_metrics"],
        )


# Retweets


class RelativeRetweetsScorer(Scorer):
    async def score(
        self, client: TwitterClient, tweet: Tweet, includes: TweetIncludes
    ) -> float:
        retweets = tweet.public_metrics["retweet_count"]
        author = next(
            user for user in includes.users if user.id == tweet.author_id
        )
        followers = author.public_metrics["followers_count"]
        return retweets / max(followers, 1)

    # noinspection PyMethodParameters
    @classproperty
    def needed_fields(cls) -> TweetFields:
        return TweetFields(
            expansions=["author_id"],
            tweet_fields=["public_metrics"],
            user_fields=["public_metrics"],
        )


# Impressions


class RelativeImpressionsScorer(Scorer):
    async def score(
        self, client: TwitterClient, tweet: Tweet, includes: TweetIncludes
    ) -> float:
        impressions = tweet.non_public_metrics["impression_count"] or 0
        author = next(
            user for user in includes.users if user.id == tweet.author_id
        )
        followers = author.public_metrics["followers_count"]
        return impressions / max(followers, 1)

    # noinspection PyMethodParameters
    @classproperty
    def needed_fields(cls) -> TweetFields:
        return TweetFields(
            expansions=["author_id"],
            tweet_fields=["non_public_metrics"],
            user_fields=["public_metrics"],
        )
