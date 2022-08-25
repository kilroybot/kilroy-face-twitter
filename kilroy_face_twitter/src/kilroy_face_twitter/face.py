from abc import ABC
from dataclasses import dataclass
from datetime import datetime
from typing import Any, AsyncIterable, Dict, Optional, Set, Tuple
from uuid import UUID

from aiostream import stream
from kilroy_face_server_py_sdk import (
    Categorizable,
    CategorizableBasedParameter,
    Configurable,
    Face,
    JSONSchema,
    Metadata,
    Parameter,
    SerializableModel,
    classproperty,
    normalize,
)
from tweepy import Tweet

from kilroy_face_twitter.client import TwitterClient
from kilroy_face_twitter.models import TweetFields, TweetIncludes
from kilroy_face_twitter.processors import Processor
from kilroy_face_twitter.scorers import Scorer
from kilroy_face_twitter.scrapers import Scraper


class TwitterFaceParams(SerializableModel):
    consumer_key: str
    consumer_secret: str
    access_token: str
    access_token_secret: str
    scoring_type: str
    scorers_params: Dict[str, Dict[str, Any]] = {}
    scraping_type: str
    scrapers_params: Dict[str, Dict[str, Any]] = {}


@dataclass
class TwitterFaceState:
    processor: Processor
    scorer: Scorer
    scorers_params: Dict[str, Dict[str, Any]]
    scraper: Scraper
    scrapers_params: Dict[str, Dict[str, Any]]
    client: TwitterClient


class ScorerParameter(CategorizableBasedParameter[TwitterFaceState, Scorer]):
    async def _get_params(
        self, state: TwitterFaceState, category: str
    ) -> Dict[str, Any]:
        return {**state.scorers_params.get(category, {})}


class ScraperParameter(CategorizableBasedParameter[TwitterFaceState, Scraper]):
    async def _get_params(
        self, state: TwitterFaceState, category: str
    ) -> Dict[str, Any]:
        return {**state.scrapers_params.get(category, {})}


class TwitterFace(Categorizable, Face[TwitterFaceState], ABC):
    @classproperty
    def category(cls) -> str:
        name: str = cls.__name__
        return normalize(name.removesuffix("TwitterFace"))

    @classproperty
    def metadata(cls) -> Metadata:
        return Metadata(
            key="kilroy-face-twitter", description="Kilroy face for Twitter"
        )

    @classproperty
    def post_type(cls) -> str:
        return cls.category

    @classproperty
    def post_schema(cls) -> JSONSchema:
        return Processor.for_category(cls.post_type).post_schema

    @classproperty
    def parameters(cls) -> Set[Parameter]:
        return {
            ScorerParameter(),
            ScraperParameter(),
        }

    @classmethod
    async def _build_processor(cls) -> Processor:
        return Processor.for_category(cls.post_type)()

    @staticmethod
    async def _build_scorer(params: TwitterFaceParams) -> Scorer:
        scorer_cls = Scorer.for_category(params.scoring_type)
        scorer_params = params.scorers_params.get(params.scoring_type, {})
        if issubclass(scorer_cls, Configurable):
            scorer = await scorer_cls.build(**scorer_params)
            await scorer.init()
        else:
            scorer = scorer_cls(**scorer_params)
        return scorer

    @staticmethod
    async def _build_scraper(params: TwitterFaceParams) -> Scraper:
        scraper_cls = Scraper.for_category(params.scraping_type)
        scraper_params = params.scrapers_params.get(params.scraping_type, {})
        if issubclass(scraper_cls, Configurable):
            scraper = await scraper_cls.build(**scraper_params)
            await scraper.init()
        else:
            scraper = scraper_cls(**scraper_params)
        return scraper

    @staticmethod
    async def _build_client(params: TwitterFaceParams) -> TwitterClient:
        return TwitterClient(
            params.consumer_key,
            params.consumer_secret,
            params.access_token,
            params.access_token_secret,
        )

    async def build_default_state(self) -> TwitterFaceState:
        params = TwitterFaceParams(**self._kwargs)
        return TwitterFaceState(
            processor=await self._build_processor(),
            scorer=await self._build_scorer(params),
            scorers_params=params.scorers_params,
            scraper=await self._build_scraper(params),
            scrapers_params=params.scrapers_params,
            client=await self._build_client(params),
        )

    async def cleanup(self) -> None:
        pass

    async def post(self, post: Dict[str, Any]) -> UUID:
        async with self.state.read_lock() as state:
            return await state.processor.post(state.client, post)

    async def score(self, post_id: UUID) -> float:
        async with self.state.read_lock() as state:
            response = await state.client.v2.get_tweet(
                post_id.int,
                user_auth=True,
                **state.scorer.needed_fields.to_kwargs(),
            )
            tweet = response.data
            includes = TweetIncludes.from_response(response)
            return await state.scorer.score(state.client, tweet, includes)

    @staticmethod
    async def _fetch(
        client: TwitterClient,
        tweets: AsyncIterable[Tuple[Tweet, TweetIncludes]],
        processor: Processor,
        scorer: Scorer,
    ) -> AsyncIterable[Tuple[UUID, Dict[str, Any], float]]:
        async for tweet, includes in tweets:
            post_id = UUID(int=tweet.id)
            score = await scorer.score(client, tweet, includes)

            try:
                post = await processor.convert(client, tweet, includes)
            except Exception:
                continue

            yield post_id, post, score

    async def scrap(
        self,
        limit: Optional[int] = None,
        before: Optional[datetime] = None,
        after: Optional[datetime] = None,
    ) -> AsyncIterable[Tuple[UUID, Dict[str, Any], float]]:
        async with self.state.read_lock() as state:
            fields = TweetFields(tweet_fields=["id"])
            fields = fields + state.processor.needed_fields
            fields = fields + state.scorer.needed_fields
            tweets = state.scraper.scrap(state.client, fields, before, after)

            posts = self._fetch(
                state.client, tweets, state.processor, state.scorer
            )
            if limit is not None:
                posts = stream.take(posts, limit)
            else:
                posts = stream.iterate(posts)

            async with posts.stream() as streamer:
                async for post_id, post, score in streamer:
                    yield post_id, post, score


class TextOnlyTwitterFace(TwitterFace):
    pass


class ImageOnlyTwitterFace(TwitterFace):
    pass


class TextAndImageTwitterFace(TwitterFace):
    pass


class TextOrImageTwitterFace(TwitterFace):
    pass


class TextWithOptionalImageTwitterFace(TwitterFace):
    pass


class ImageWithOptionalTextTwitterFace(TwitterFace):
    pass
