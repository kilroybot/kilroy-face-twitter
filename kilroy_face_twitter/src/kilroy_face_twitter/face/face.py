from dataclasses import dataclass
from datetime import datetime
from typing import (
    AsyncIterable,
    Dict,
    Iterable,
    Optional,
    Tuple,
    get_args,
)
from uuid import UUID

from asyncstdlib import islice
from kilroy_face_server_py_sdk import JSON, JSONSchema
from tweepy import Tweet

from kilroy_face_twitter.client import TwitterClient
from kilroy_face_twitter.config import FaceConfig
from kilroy_face_twitter.face.models import TweetFields, TweetIncludes
from kilroy_face_twitter.face.parameters import Parameter
from kilroy_face_twitter.face.processors import Processor
from kilroy_face_twitter.face.scorers import Scorer
from kilroy_face_twitter.face.scrapers import Scraper
from kilroy_face_twitter.face.utils import Configurable
from kilroy_face_twitter.types import ScoringType, ScrapingType, StateType
from kilroy_face_twitter.utils import Deepcopyable


@dataclass
class TwitterFaceState(Deepcopyable):
    processor: Processor
    scoring_type: ScoringType
    scorers: Dict[ScoringType, Scorer]
    scraping_type: ScrapingType
    scrapers: Dict[ScrapingType, Scraper]
    client: TwitterClient

    @property
    def scorer(self) -> Scorer:
        return self.scorers[self.scoring_type]

    @property
    def scraper(self) -> Scraper:
        return self.scrapers[self.scraping_type]


class ProcessorParameter(Parameter[TwitterFaceState, JSON]):
    async def _get(self, state: TwitterFaceState) -> JSON:
        return await state.processor.get_config()

    async def _set(self, state: TwitterFaceState, value: JSON) -> None:
        await state.processor.set_config(value)

    def name(self, state: TwitterFaceState) -> str:
        return "processor"

    def schema(self, state: TwitterFaceState) -> JSON:
        return {
            "type": "object",
            "properties": state.processor.config_properties_schema,
        }

    def ui_schema(self, state: StateType) -> JSON:
        return state.processor.config_ui_schema


class ScorerParameter(Parameter[TwitterFaceState, JSON]):
    async def _get(self, state: TwitterFaceState) -> JSON:
        return {
            "type": state.scoring_type,
            "config": await state.scorer.get_config(),
        }

    async def _set(self, state: TwitterFaceState, value: JSON) -> None:
        state.scoring_type = value["type"]
        await state.scorer.set_config(value["config"])

    def name(self, state: TwitterFaceState) -> str:
        return "scorer"

    def schema(self, state: TwitterFaceState) -> JSON:
        return {
            "type": "object",
            "oneOf": [
                {
                    "type": "object",
                    "properties": {
                        "type": {
                            "type": "string",
                            "const": scoring_type,
                        },
                        "config": {
                            "type": "object",
                            "properties": state.scorers[
                                scoring_type
                            ].config_properties_schema,
                        },
                    },
                }
                for scoring_type in get_args(ScoringType)
            ],
        }


class ScraperParameter(Parameter[TwitterFaceState, JSON]):
    async def _get(self, state: TwitterFaceState) -> JSON:
        return {
            "type": state.scraping_type,
            "config": await state.scraper.get_config(),
        }

    async def _set(self, state: TwitterFaceState, value: JSON) -> None:
        state.scraping_type = value["type"]
        await state.scraper.set_config(value["config"])

    def name(self, state: TwitterFaceState) -> str:
        return "scraper"

    def schema(self, state: TwitterFaceState) -> JSON:
        return {
            "type": "object",
            "oneOf": [
                {
                    "type": "object",
                    "properties": {
                        "type": {
                            "type": "string",
                            "const": scraping_type,
                        },
                        "config": {
                            "type": "object",
                            "properties": state.scrapers[
                                scraping_type
                            ].config_properties_schema,
                        },
                    },
                }
                for scraping_type in get_args(ScrapingType)
            ],
        }


class TwitterFace(Configurable[TwitterFaceState]):
    async def _create_initial_state(self, config: FaceConfig) -> StateType:
        return TwitterFaceState(
            processor=await Processor.for_type(config.post_type).build(
                **config.processors_params.get(config.post_type, {})
            ),
            scoring_type=config.default_scoring_type,
            scorers={
                scoring_type: await Scorer.for_type(scoring_type).build(
                    **config.scorers_params.get(scoring_type, {})
                )
                for scoring_type in get_args(ScoringType)
            },
            scraping_type=config.default_scraping_type,
            scrapers={
                scraping_type: await Scraper.for_type(scraping_type).build(
                    **config.scrapers_params.get(scraping_type, {})
                )
                for scraping_type in get_args(ScrapingType)
            },
            client=TwitterClient(
                consumer_key=config.consumer_key,
                consumer_secret=config.consumer_secret,
                access_token=config.access_token,
                access_token_secret=config.access_token_secret,
            ),
        )

    @property
    def post_json_schema(self) -> JSONSchema:
        return self._state.processor.post_schema()

    @property
    def _parameters(self) -> Iterable[Parameter]:
        return [ProcessorParameter(), ScorerParameter(), ScraperParameter()]

    async def post(self, post: JSON) -> UUID:
        return await self._state.processor.post(self._state.client, post)

    async def score(self, post_id: UUID) -> float:
        response = await self._state.client.v2.get_tweet(
            post_id.int,
            user_auth=True,
            **self._state.scorer.needed_fields().to_kwargs(),
        )
        tweet = response.data
        includes = TweetIncludes.from_response(response)
        return await self._state.scorer.score(
            self._state.client, tweet, includes
        )

    async def scrap(
        self,
        limit: Optional[int] = None,
        before: Optional[datetime] = None,
        after: Optional[datetime] = None,
    ) -> AsyncIterable[Tuple[UUID, JSON]]:
        async def fetch(
            client: TwitterClient,
            twts: AsyncIterable[Tuple[Tweet, TweetIncludes]],
            processor: Processor,
        ) -> AsyncIterable[Tuple[UUID, JSON]]:
            async for tweet, includes in twts:
                uuid = UUID(int=tweet.id)
                try:
                    post = await processor.convert(client, tweet, includes)
                except Exception:
                    continue
                yield uuid, post

        fields = self._state.processor.needed_fields() + TweetFields(
            tweet_fields=["id"]
        )

        tweets = self._state.scraper.scrap(
            self._state.client,
            fields,
            before,
            after,
        )
        posts = islice(
            fetch(self._state.client, tweets, self._state.processor), limit
        )

        async for post_id, post in posts:
            yield post_id, post
