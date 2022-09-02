import json
from abc import ABC
from dataclasses import dataclass
from datetime import datetime
from functools import partial
from pathlib import Path
from typing import Any, AsyncIterable, Dict, Optional, Set, Tuple
from uuid import UUID

from aiostream import stream
from kilroy_face_server_py_sdk import (
    Categorizable,
    CategorizableBasedParameter,
    Face,
    JSONSchema,
    Metadata,
    Parameter,
    Savable,
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


class Params(SerializableModel):
    consumer_key: str
    consumer_secret: str
    access_token: str
    access_token_secret: str
    scoring_type: str
    scorers_params: Dict[str, Dict[str, Any]] = {}
    scraping_type: str
    scrapers_params: Dict[str, Dict[str, Any]] = {}


@dataclass
class State:
    processor: Processor
    scorer: Scorer
    scorers_params: Dict[str, Dict[str, Any]]
    scraper: Scraper
    scrapers_params: Dict[str, Dict[str, Any]]
    client: TwitterClient


class ScorerParameter(CategorizableBasedParameter[State, Scorer]):
    async def _get_params(self, state: State, category: str) -> Dict[str, Any]:
        return {**state.scorers_params.get(category, {})}


class ScraperParameter(CategorizableBasedParameter[State, Scraper]):
    async def _get_params(self, state: State, category: str) -> Dict[str, Any]:
        return {**state.scrapers_params.get(category, {})}


class TwitterFace(Categorizable, Face[State], ABC):
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
        return await cls._build_generic(Processor, category=cls.post_type)

    @classmethod
    async def _build_scorer(cls, params: Params) -> Scorer:
        return await cls._build_generic(
            Scorer,
            category=params.scoring_type,
            **params.scorers_params.get(params.scoring_type, {}),
        )

    @classmethod
    async def _build_scraper(cls, params: Params) -> Scraper:
        return await cls._build_generic(
            Scraper,
            category=params.scraping_type,
            **params.scrapers_params.get(params.scraping_type, {}),
        )

    @staticmethod
    async def _build_client(params: Params) -> TwitterClient:
        return TwitterClient(
            consumer_key=params.consumer_key,
            consumer_secret=params.consumer_secret,
            access_token=params.access_token,
            access_token_secret=params.access_token_secret,
        )

    async def _build_default_state(self) -> State:
        params = Params(**self._kwargs)
        return State(
            processor=await self._build_processor(),
            scorer=await self._build_scorer(params),
            scorers_params=params.scorers_params,
            scraper=await self._build_scraper(params),
            scrapers_params=params.scrapers_params,
            client=await self._build_client(params),
        )

    @staticmethod
    async def _save_processor(state: State, directory: Path) -> None:
        if isinstance(state.processor, Savable):
            await state.processor.save(directory / "processor")

    @staticmethod
    async def _save_scorer(state: State, directory: Path) -> None:
        if isinstance(state.scorer, Savable):
            await state.scorer.save(directory / "scorer")

    @staticmethod
    async def _save_scraper(state: State, directory: Path) -> None:
        if isinstance(state.scraper, Savable):
            await state.scraper.save(directory / "scraper")

    @staticmethod
    async def _create_state_dict(state: State) -> Dict[str, Any]:
        return {
            "processor_type": state.processor.category,
            "scorer_type": state.scorer.category,
            "scraper_type": state.scraper.category,
            "scorers_params": state.scorers_params,
            "scrapers_params": state.scrapers_params,
        }

    @staticmethod
    async def _save_state_dict(
        state_dict: Dict[str, Any], directory: Path
    ) -> None:
        with open(directory / "state.json", "w") as f:
            json.dump(state_dict, f)

    @classmethod
    async def _save_state(cls, state: State, directory: Path) -> None:
        await cls._save_processor(state, directory)
        await cls._save_scorer(state, directory)
        await cls._save_scraper(state, directory)
        state_dict = await cls._create_state_dict(state)
        await cls._save_state_dict(state_dict, directory)

    @staticmethod
    async def _load_state_dict(directory: Path) -> Dict[str, Any]:
        with open(directory / "state.json", "r") as f:
            return json.load(f)

    @classmethod
    async def _load_processor(
        cls, directory: Path, state_dict: Dict[str, Any]
    ) -> Processor:
        return await cls._load_generic(
            directory / "processor",
            Processor,
            category=state_dict["processor_type"],
            default=cls._build_processor,
        )

    @classmethod
    async def _load_scorer(
        cls, directory: Path, state_dict: Dict[str, Any], params: Params
    ) -> Scorer:
        return await cls._load_generic(
            directory / "scorer",
            Scorer,
            category=state_dict["scorer_type"],
            default=partial(cls._build_scorer, params),
        )

    @classmethod
    async def _load_scraper(
        cls, directory: Path, state_dict: Dict[str, Any], params: Params
    ) -> Scraper:
        return await cls._load_generic(
            directory / "scraper",
            Scraper,
            category=state_dict["scraper_type"],
            default=partial(cls._build_scraper, params),
        )

    async def _load_saved_state(self, directory: Path) -> State:
        state_dict = await self._load_state_dict(directory)
        params = Params(**self._kwargs)

        return State(
            processor=await self._load_processor(directory, state_dict),
            scorer=await self._load_scorer(directory, state_dict, params),
            scorers_params=state_dict["scorers_params"],
            scraper=await self._load_scraper(directory, state_dict, params),
            scrapers_params=state_dict["scrapers_params"],
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
