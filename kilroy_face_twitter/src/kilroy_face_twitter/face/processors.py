import json
from abc import ABC, abstractmethod
from dataclasses import dataclass
from io import BytesIO
from typing import Generic, Type
from uuid import UUID

from kilroy_face_server_py_sdk import JSONSchema
from kilroy_ws_server_py_sdk import JSON
from tweepy import Tweet

from kilroy_face_twitter.client import TwitterClient
from kilroy_face_twitter.face.models import TweetFields, TweetIncludes
from kilroy_face_twitter.face.utils import Configurable
from kilroy_face_twitter.posts import (
    ImageData,
    ImageOnlyPost,
    TextAndImagePost,
    TextData,
    TextOnlyPost,
)
from kilroy_face_twitter.types import PostType, StateType
from kilroy_face_twitter.utils import (
    Deepcopyable,
    base64_decode,
    base64_encode,
    download_image,
    get_filename_from_url,
)


class Processor(Configurable[StateType], Generic[StateType], ABC):
    @abstractmethod
    async def post(self, client: TwitterClient, post: JSON) -> UUID:
        pass

    @abstractmethod
    async def convert(
        self, client: TwitterClient, tweet: Tweet, includes: TweetIncludes
    ) -> JSON:
        pass

    @staticmethod
    @abstractmethod
    def needed_fields() -> TweetFields:
        pass

    @staticmethod
    @abstractmethod
    def post_type() -> PostType:
        pass

    @staticmethod
    @abstractmethod
    def post_schema() -> JSONSchema:
        pass

    @classmethod
    def for_type(cls, post_type: PostType) -> Type["Processor"]:
        for processor in cls.__subclasses__():
            if processor.post_type() == post_type:
                return processor
        raise ValueError(f'Processor for type "{post_type}" not found.')


# Text only


@dataclass
class TextOnlyProcessorState(Deepcopyable):
    pass


class TextOnlyProcessor(Processor[TextOnlyProcessorState]):
    @staticmethod
    def post_type() -> PostType:
        return "text"

    @staticmethod
    def post_schema() -> JSONSchema:
        return JSONSchema(TextOnlyPost.schema())

    @staticmethod
    def needed_fields() -> TweetFields:
        return TweetFields(tweet_fields=["text"])

    async def _create_initial_state(self) -> TextOnlyProcessorState:
        return TextOnlyProcessorState()

    async def post(self, client: TwitterClient, post: JSON) -> UUID:
        post = TextOnlyPost.parse_obj(post)
        response = await client.v2.create_tweet(text=post.text.content)
        return UUID(int=Tweet(response.data).id)

    async def convert(
        self, client: TwitterClient, tweet: Tweet, includes: TweetIncludes
    ) -> JSON:
        post = TextOnlyPost(text=TextData(content=tweet.text))
        return json.loads(post.json())


# Image only


@dataclass
class ImageOnlyProcessorState(Deepcopyable):
    pass


class ImageOnlyProcessor(Processor[ImageOnlyProcessorState]):
    @staticmethod
    def post_type() -> PostType:
        return "image"

    @staticmethod
    def post_schema() -> JSONSchema:
        return JSONSchema(ImageOnlyPost.schema())

    @staticmethod
    def needed_fields() -> TweetFields:
        return TweetFields(
            expansions=["attachments.media_keys"],
            media_fields=["url"],
            tweet_fields=["attachments"],
        )

    async def _create_initial_state(self) -> ImageOnlyProcessorState:
        return ImageOnlyProcessorState()

    async def post(self, client: TwitterClient, post: JSON) -> UUID:
        post = ImageOnlyPost.parse_obj(post)
        image_bytes = base64_decode(post.image.raw)
        with BytesIO(image_bytes) as file:
            media = client.v1.media_upload(
                file=file, filename=post.image.filename
            )
        response = await client.v2.create_tweet(media_ids=[media.media_id])
        return UUID(int=Tweet(response.data).id)

    async def convert(
        self, client: TwitterClient, tweet: Tweet, includes: TweetIncludes
    ) -> JSON:
        media_key = tweet.attachments["media_keys"][0]
        image_url = next(
            media.url
            for media in includes.media
            if media.media_key == media_key
        )
        post = ImageOnlyPost(
            image=ImageData(
                raw=base64_encode(await download_image(image_url)),
                filename=get_filename_from_url(image_url),
            )
        )
        return json.loads(post.json())


# Text + image


@dataclass
class TextAndImageProcessorState(Deepcopyable):
    pass


class TextAndImageProcessor(Processor[TextAndImageProcessorState]):
    @staticmethod
    def post_type() -> PostType:
        return "text+image"

    @staticmethod
    def post_schema() -> JSONSchema:
        return JSONSchema(TextAndImagePost.schema())

    @staticmethod
    def needed_fields() -> TweetFields:
        return TweetFields(
            expansions=["attachments.media_keys"],
            media_fields=["url"],
            tweet_fields=["attachments", "text"],
        )

    async def _create_initial_state(self) -> TextAndImageProcessorState:
        return TextAndImageProcessorState()

    async def post(self, client: TwitterClient, post: JSON) -> UUID:
        post = TextAndImagePost.parse_obj(post)
        image_bytes = base64_decode(post.image.raw)
        with BytesIO(image_bytes) as file:
            media = client.v1.media_upload(
                file=file, filename=post.image.filename
            )
        response = await client.v2.create_tweet(
            text=post.text.content, media_ids=[media.media_id]
        )
        return UUID(int=Tweet(response.data).id)

    async def convert(
        self, client: TwitterClient, tweet: Tweet, includes: TweetIncludes
    ) -> JSON:
        media_key = tweet.attachments["media_keys"][0]
        image_url = next(
            media.url
            for media in includes.media
            if media.media_key == media_key
        )
        post = TextAndImagePost(
            text=TextData(content=tweet.text),
            image=ImageData(
                raw=base64_encode(await download_image(image_url)),
                filename=get_filename_from_url(image_url),
            ),
        )
        return json.loads(post.json())
