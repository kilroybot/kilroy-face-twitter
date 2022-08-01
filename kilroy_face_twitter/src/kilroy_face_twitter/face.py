from dataclasses import dataclass
from datetime import datetime
from typing import (
    AsyncIterable,
    Dict,
    Iterable,
    Optional,
    Tuple,
)
from uuid import UUID

from asyncstdlib import islice
from kilroy_face_server_py_sdk import (
    BaseState,
    Face,
    JSON,
    JSONSchema,
    Parameter,
)
from tweepy import Tweet

from kilroy_face_twitter.client import TwitterClient
from kilroy_face_twitter.config import FaceConfig
from kilroy_face_twitter.models import TweetFields, TweetIncludes
from kilroy_face_twitter.processors import Processor
from kilroy_face_twitter.scorers import Scorer
from kilroy_face_twitter.scrapers import Scraper


@dataclass
class TwitterFaceState(BaseState):
    processor: Processor
    scoring_type: str
    scorers: Dict[str, Scorer]
    scraping_type: str
    scrapers: Dict[str, Scraper]
    client: TwitterClient

    @property
    def scorer(self) -> Scorer:
        return self.scorers[self.scoring_type]

    @property
    def scraper(self) -> Scraper:
        return self.scrapers[self.scraping_type]


class ProcessorParameter(Parameter[TwitterFaceState, JSON]):
    async def _get(self, state: TwitterFaceState) -> JSON:
        return await state.processor.config.get()

    async def _set(self, state: TwitterFaceState, value: JSON) -> None:
        await state.processor.config.set(value)

    async def name(self, state: TwitterFaceState) -> str:
        return "processor"

    async def schema(self, state: TwitterFaceState) -> JSON:
        return {
            "type": "object",
            "properties": await state.processor.config.get_properties_schema(),
        }


class ScorerParameter(Parameter[TwitterFaceState, JSON]):
    async def _get(self, state: TwitterFaceState) -> JSON:
        return {
            "type": state.scoring_type,
            "config": await state.scorer.config.get(),
        }

    async def _set(self, state: TwitterFaceState, value: JSON) -> None:
        state.scoring_type = value["type"]
        await state.scorer.config.set(value["config"])

    async def name(self, state: TwitterFaceState) -> str:
        return "scorer"

    async def schema(self, state: TwitterFaceState) -> JSON:
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
                            "properties": await state.scorers[
                                scoring_type
                            ].config.get_properties_schema(),
                        },
                    },
                }
                for scoring_type in Scorer.all_categories()
            ],
        }


class ScraperParameter(Parameter[TwitterFaceState, JSON]):
    async def _get(self, state: TwitterFaceState) -> JSON:
        return {
            "type": state.scraping_type,
            "config": await state.scraper.config.get(),
        }

    async def _set(self, state: TwitterFaceState, value: JSON) -> None:
        state.scraping_type = value["type"]
        await state.scraper.config.set(value["config"])

    async def name(self, state: TwitterFaceState) -> str:
        return "scraper"

    async def schema(self, state: TwitterFaceState) -> JSON:
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
                            "properties": await state.scrapers[
                                scraping_type
                            ].config.get_properties_schema(),
                        },
                    },
                }
                for scraping_type in Scraper.all_categories()
            ],
        }


class TwitterFace(Face[TwitterFaceState]):
    def __init__(self, config: FaceConfig) -> None:
        super().__init__()
        self._face_config = config

    async def _create_initial_state(self) -> TwitterFaceState:
        return TwitterFaceState(
            processor=await Processor.for_category(
                self._face_config.post_type
            ).build(
                **self._face_config.processors_params.get(
                    self._face_config.post_type, {}
                )
            ),
            scoring_type=self._face_config.default_scoring_type,
            scorers={
                scoring_type: await Scorer.for_category(scoring_type).build(
                    **self._face_config.scorers_params.get(scoring_type, {})
                )
                for scoring_type in Scorer.all_categories()
            },
            scraping_type=self._face_config.default_scraping_type,
            scrapers={
                scraping_type: await Scraper.for_category(scraping_type).build(
                    **self._face_config.scrapers_params.get(scraping_type, {})
                )
                for scraping_type in Scraper.all_categories()
            },
            client=TwitterClient(
                consumer_key=self._face_config.consumer_key,
                consumer_secret=self._face_config.consumer_secret,
                access_token=self._face_config.access_token,
                access_token_secret=self._face_config.access_token_secret,
            ),
        )

    @property
    def post_schema(self) -> JSONSchema:
        return self.state.processor.post_schema()

    async def _get_parameters(self) -> Iterable[Parameter]:
        return [ProcessorParameter(), ScorerParameter(), ScraperParameter()]

    async def post(self, post: JSON) -> UUID:
        return await self.state.processor.post(self.state.client, post)

    async def score(self, post_id: UUID) -> float:
        response = await self.state.client.v2.get_tweet(
            post_id.int,
            user_auth=True,
            **self.state.scorer.needed_fields().to_kwargs(),
        )
        tweet = response.data
        includes = TweetIncludes.from_response(response)
        return await self.state.scorer.score(
            self.state.client, tweet, includes
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

        fields = self.state.processor.needed_fields() + TweetFields(
            tweet_fields=["id"]
        )

        tweets = self.state.scraper.scrap(
            self.state.client,
            fields,
            before,
            after,
        )
        posts = islice(
            fetch(self.state.client, tweets, self.state.processor), limit
        )

        async for post_id, post in posts:
            yield post_id, post
