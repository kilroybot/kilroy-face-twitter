import json
from abc import ABC, abstractmethod
from dataclasses import dataclass
from io import BytesIO
from typing import Generic, Iterable, Optional
from uuid import UUID

from kilroy_face_server_py_sdk import (
    BasePostModel,
    BaseState,
    Categorizable,
    ConfigurableWithLoadableState,
    ImageData,
    ImageOnlyPost,
    ImageWithOptionalTextPost,
    JSONSchema,
    Parameter,
    StateType,
    TextAndImagePost,
    TextData,
    TextOnlyPost,
    TextOrImagePost,
    TextWithOptionalImagePost,
    base64_decode,
    base64_encode,
    get_filename_from_url,
    JSON,
)
from tweepy import Media, Tweet

from kilroy_face_twitter.client import TwitterClient
from kilroy_face_twitter.models import TweetFields, TweetIncludes
from kilroy_face_twitter.utils import download_image

TEXT_FIELDS = TweetFields(tweet_fields=["text"])
IMAGE_FIELDS = TweetFields(
    expansions=["attachments.media_keys"],
    media_fields=["url"],
    tweet_fields=["attachments"],
)


async def upload_image(client: TwitterClient, image: ImageData) -> Media:
    image_bytes = base64_decode(image.raw)
    with BytesIO(image_bytes) as file:
        return client.v1.media_upload(file=file, filename=image.filename)


async def create_tweet(client: TwitterClient, *args, **kwargs) -> UUID:
    response = await client.v2.create_tweet(*args, **kwargs)
    return UUID(int=Tweet(response.data).id)


def to_json(post: BasePostModel) -> JSON:
    return json.loads(post.json())


async def get_text_data(tweet: Tweet) -> Optional[TextData]:
    if not tweet.text:
        return
    return TextData(content=tweet.text)


async def get_image_data(
    tweet: Tweet, includes: TweetIncludes
) -> Optional[ImageData]:
    if len(tweet.attachments.get("media_keys", [])) == 0:
        return None
    media_key = tweet.attachments["media_keys"][0]
    try:
        image_url = next(
            media.url
            for media in includes.media
            if media.media_key == media_key
        )
    except StopIteration:
        return None
    return ImageData(
        raw=base64_encode(await download_image(image_url)),
        filename=get_filename_from_url(image_url),
    )


class Processor(
    ConfigurableWithLoadableState[StateType],
    Categorizable,
    Generic[StateType],
    ABC,
):
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
    def post_schema() -> JSONSchema:
        pass


# Text only


@dataclass
class TextOnlyProcessorState(BaseState):
    pass


class TextOnlyProcessor(Processor[TextOnlyProcessorState]):
    @classmethod
    def category(cls) -> str:
        return "text"

    @staticmethod
    def post_schema() -> JSONSchema:
        return JSONSchema(TextOnlyPost.schema())

    @staticmethod
    def needed_fields() -> TweetFields:
        return TEXT_FIELDS

    async def _create_initial_state(self) -> TextOnlyProcessorState:
        return TextOnlyProcessorState()

    async def post(self, client: TwitterClient, post: JSON) -> UUID:
        post = TextOnlyPost.parse_obj(post)
        return await create_tweet(client, text=post.text.content)

    async def convert(
        self, client: TwitterClient, tweet: Tweet, includes: TweetIncludes
    ) -> JSON:
        text = await get_text_data(tweet)
        post = TextOnlyPost(text=text)
        return to_json(post)

    async def _get_parameters(self) -> Iterable[Parameter]:
        return []


# Image only


@dataclass
class ImageOnlyProcessorState(BaseState):
    pass


class ImageOnlyProcessor(Processor[ImageOnlyProcessorState]):
    @classmethod
    def category(cls) -> str:
        return "image"

    @staticmethod
    def post_schema() -> JSONSchema:
        return JSONSchema(ImageOnlyPost.schema())

    @staticmethod
    def needed_fields() -> TweetFields:
        return IMAGE_FIELDS

    async def _create_initial_state(self) -> ImageOnlyProcessorState:
        return ImageOnlyProcessorState()

    async def post(self, client: TwitterClient, post: JSON) -> UUID:
        post = ImageOnlyPost.parse_obj(post)
        media = await upload_image(client, post.image)
        return await create_tweet(client, media_ids=[media.media_id])

    async def convert(
        self, client: TwitterClient, tweet: Tweet, includes: TweetIncludes
    ) -> JSON:
        image = await get_image_data(tweet, includes)
        post = ImageOnlyPost(image=image)
        return to_json(post)

    async def _get_parameters(self) -> Iterable[Parameter]:
        return []


# Text and image


@dataclass
class TextAndImageProcessorState(BaseState):
    pass


class TextAndImageProcessor(Processor[TextAndImageProcessorState]):
    @classmethod
    def category(cls) -> str:
        return "text-and-image"

    @staticmethod
    def post_schema() -> JSONSchema:
        return JSONSchema(TextAndImagePost.schema())

    @staticmethod
    def needed_fields() -> TweetFields:
        return TEXT_FIELDS + IMAGE_FIELDS

    async def _create_initial_state(self) -> TextAndImageProcessorState:
        return TextAndImageProcessorState()

    async def post(self, client: TwitterClient, post: JSON) -> UUID:
        post = TextAndImagePost.parse_obj(post)
        media = await upload_image(client, post.image)
        return await create_tweet(
            client, text=post.text.content, media_ids=[media.media_id]
        )

    async def convert(
        self, client: TwitterClient, tweet: Tweet, includes: TweetIncludes
    ) -> JSON:
        text = await get_text_data(tweet)
        image = await get_image_data(tweet, includes)
        post = TextAndImagePost(text=text, image=image)
        return to_json(post)

    async def _get_parameters(self) -> Iterable[Parameter]:
        return []


# Text or image


@dataclass
class TextOrImageProcessorState(BaseState):
    pass


class TextOrImageProcessor(Processor[TextOrImageProcessorState]):
    @classmethod
    def category(cls) -> str:
        return "text-or-image"

    @staticmethod
    def post_schema() -> JSONSchema:
        return JSONSchema(TextOrImagePost.schema())

    @staticmethod
    def needed_fields() -> TweetFields:
        return TEXT_FIELDS + IMAGE_FIELDS

    async def _create_initial_state(self) -> TextOrImageProcessorState:
        return TextOrImageProcessorState()

    async def post(self, client: TwitterClient, post: JSON) -> UUID:
        post = TextOrImagePost.parse_obj(post)
        kwargs = {}
        if post.text is not None:
            kwargs["text"] = post.text.content
        if post.image is not None:
            media = await upload_image(client, post.image)
            kwargs["media_ids"] = [media.media_id]
        return await create_tweet(client, **kwargs)

    async def convert(
        self, client: TwitterClient, tweet: Tweet, includes: TweetIncludes
    ) -> JSON:
        text = await get_text_data(tweet)
        image = await get_image_data(tweet, includes)
        post = TextOrImagePost(text=text, image=image)
        return to_json(post)

    async def _get_parameters(self) -> Iterable[Parameter]:
        return []


# Text with optional image


@dataclass
class TextWithOptionalImageProcessorState(BaseState):
    pass


class TextWithOptionalImageProcessor(
    Processor[TextWithOptionalImageProcessorState]
):
    @classmethod
    def category(cls) -> str:
        return "text-with-optional-image"

    @staticmethod
    def post_schema() -> JSONSchema:
        return JSONSchema(TextWithOptionalImagePost.schema())

    @staticmethod
    def needed_fields() -> TweetFields:
        return TEXT_FIELDS + IMAGE_FIELDS

    async def _create_initial_state(
        self,
    ) -> TextWithOptionalImageProcessorState:
        return TextWithOptionalImageProcessorState()

    async def post(self, client: TwitterClient, post: JSON) -> UUID:
        post = TextWithOptionalImagePost.parse_obj(post)
        kwargs = {}
        if post.image is not None:
            media = await upload_image(client, post.image)
            kwargs["media_ids"] = [media.media_id]
        return await create_tweet(client, text=post.text.content, **kwargs)

    async def convert(
        self, client: TwitterClient, tweet: Tweet, includes: TweetIncludes
    ) -> JSON:
        text = await get_text_data(tweet)
        image = await get_image_data(tweet, includes)
        post = TextWithOptionalImagePost(text=text, image=image)
        return to_json(post)

    async def _get_parameters(self) -> Iterable[Parameter]:
        return []


# Image with optional text


@dataclass
class ImageWithOptionalTextProcessorState(BaseState):
    pass


class ImageWithOptionalTextProcessor(
    Processor[ImageWithOptionalTextProcessorState]
):
    @classmethod
    def category(cls) -> str:
        return "image-with-optional-text"

    @staticmethod
    def post_schema() -> JSONSchema:
        return JSONSchema(ImageWithOptionalTextPost.schema())

    @staticmethod
    def needed_fields() -> TweetFields:
        return TEXT_FIELDS + IMAGE_FIELDS

    async def _create_initial_state(
        self,
    ) -> ImageWithOptionalTextProcessorState:
        return ImageWithOptionalTextProcessorState()

    async def post(self, client: TwitterClient, post: JSON) -> UUID:
        post = ImageWithOptionalTextPost.parse_obj(post)
        kwargs = {}
        if post.text is not None:
            kwargs["text"] = post.text.content
        media = await upload_image(client, post.image)
        return await create_tweet(client, media_ids=[media.media_id], **kwargs)

    async def convert(
        self, client: TwitterClient, tweet: Tweet, includes: TweetIncludes
    ) -> JSON:
        text = await get_text_data(tweet)
        image = await get_image_data(tweet, includes)
        post = ImageWithOptionalTextPost(text=text, image=image)
        return to_json(post)

    async def _get_parameters(self) -> Iterable[Parameter]:
        return []
