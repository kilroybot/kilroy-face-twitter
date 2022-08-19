import json
from abc import ABC, abstractmethod
from io import BytesIO
from typing import Any, Dict, Optional
from uuid import UUID

from kilroy_face_server_py_sdk import (
    Categorizable,
    ImageData,
    ImageOnlyPost,
    ImageWithOptionalTextPost,
    JSONSchema,
    TextAndImagePost,
    TextData,
    TextOnlyPost,
    TextOrImagePost,
    TextWithOptionalImagePost,
    base64_decode,
    base64_encode,
    classproperty,
    normalize,
)
from tweepy import Media, Tweet

from kilroy_face_twitter.client import TwitterClient
from kilroy_face_twitter.models import TweetFields, TweetIncludes
from kilroy_face_twitter.utils import download_image, get_filename_from_url

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


class Processor(Categorizable, ABC):
    @classproperty
    def category(cls) -> str:
        name: str = cls.__name__
        return normalize(name.removesuffix("Processor"))

    @abstractmethod
    async def post(self, client: TwitterClient, post: Dict[str, Any]) -> UUID:
        pass

    @abstractmethod
    async def convert(
        self, client: TwitterClient, tweet: Tweet, includes: TweetIncludes
    ) -> Dict[str, Any]:
        pass

    @classproperty
    @abstractmethod
    def needed_fields(cls) -> TweetFields:
        pass

    @classproperty
    @abstractmethod
    def post_schema(cls) -> JSONSchema:
        pass


# Text only


class TextOnlyProcessor(Processor):
    @classproperty
    def post_schema(cls) -> JSONSchema:
        return JSONSchema(**TextOnlyPost.schema())

    @classproperty
    def needed_fields(cls) -> TweetFields:
        return TEXT_FIELDS

    async def post(self, client: TwitterClient, post: Dict[str, Any]) -> UUID:
        post = TextOnlyPost.parse_obj(post)
        return await create_tweet(client, text=post.text.content)

    async def convert(
        self, client: TwitterClient, tweet: Tweet, includes: TweetIncludes
    ) -> Dict[str, Any]:
        text = await get_text_data(tweet)
        post = TextOnlyPost(text=text)
        return json.loads(post.json())


# Image only


class ImageOnlyProcessor(Processor):
    @classproperty
    def post_schema(cls) -> JSONSchema:
        return JSONSchema(**ImageOnlyPost.schema())

    @classproperty
    def needed_fields(cls) -> TweetFields:
        return IMAGE_FIELDS

    async def post(self, client: TwitterClient, post: Dict[str, Any]) -> UUID:
        post = ImageOnlyPost.parse_obj(post)
        media = await upload_image(client, post.image)
        return await create_tweet(client, media_ids=[media.media_id])

    async def convert(
        self, client: TwitterClient, tweet: Tweet, includes: TweetIncludes
    ) -> Dict[str, Any]:
        image = await get_image_data(tweet, includes)
        post = ImageOnlyPost(image=image)
        return json.loads(post.json())


# Text and image


class TextAndImageProcessor(Processor):
    @classproperty
    def post_schema(cls) -> JSONSchema:
        return JSONSchema(**TextAndImagePost.schema())

    @classproperty
    def needed_fields(cls) -> TweetFields:
        return TEXT_FIELDS + IMAGE_FIELDS

    async def post(self, client: TwitterClient, post: Dict[str, Any]) -> UUID:
        post = TextAndImagePost.parse_obj(post)
        media = await upload_image(client, post.image)
        return await create_tweet(
            client, text=post.text.content, media_ids=[media.media_id]
        )

    async def convert(
        self, client: TwitterClient, tweet: Tweet, includes: TweetIncludes
    ) -> Dict[str, Any]:
        text = await get_text_data(tweet)
        image = await get_image_data(tweet, includes)
        post = TextAndImagePost(text=text, image=image)
        return json.loads(post.json())


# Text or image


class TextOrImageProcessor(Processor):
    @classproperty
    def post_schema(cls) -> JSONSchema:
        return JSONSchema(**TextOrImagePost.schema())

    @classproperty
    def needed_fields(cls) -> TweetFields:
        return TEXT_FIELDS + IMAGE_FIELDS

    async def post(self, client: TwitterClient, post: Dict[str, Any]) -> UUID:
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
    ) -> Dict[str, Any]:
        text = await get_text_data(tweet)
        image = await get_image_data(tweet, includes)
        post = TextOrImagePost(text=text, image=image)
        return json.loads(post.json())


# Text with optional image


class TextWithOptionalImageProcessor(Processor):
    @classproperty
    def post_schema(cls) -> JSONSchema:
        return JSONSchema(**TextWithOptionalImagePost.schema())

    @classproperty
    def needed_fields(cls) -> TweetFields:
        return TEXT_FIELDS + IMAGE_FIELDS

    async def post(self, client: TwitterClient, post: Dict[str, Any]) -> UUID:
        post = TextWithOptionalImagePost.parse_obj(post)
        kwargs = {}
        if post.image is not None:
            media = await upload_image(client, post.image)
            kwargs["media_ids"] = [media.media_id]
        return await create_tweet(client, text=post.text.content, **kwargs)

    async def convert(
        self, client: TwitterClient, tweet: Tweet, includes: TweetIncludes
    ) -> Dict[str, Any]:
        text = await get_text_data(tweet)
        image = await get_image_data(tweet, includes)
        post = TextWithOptionalImagePost(text=text, image=image)
        return json.loads(post.json())


# Image with optional text


class ImageWithOptionalTextProcessor(Processor):
    @classproperty
    def post_schema(cls) -> JSONSchema:
        return JSONSchema(**ImageWithOptionalTextPost.schema())

    @classproperty
    def needed_fields(cls) -> TweetFields:
        return TEXT_FIELDS + IMAGE_FIELDS

    async def post(self, client: TwitterClient, post: Dict[str, Any]) -> UUID:
        post = ImageWithOptionalTextPost.parse_obj(post)
        kwargs = {}
        if post.text is not None:
            kwargs["text"] = post.text.content
        media = await upload_image(client, post.image)
        return await create_tweet(client, media_ids=[media.media_id], **kwargs)

    async def convert(
        self, client: TwitterClient, tweet: Tweet, includes: TweetIncludes
    ) -> Dict[str, Any]:
        text = await get_text_data(tweet)
        image = await get_image_data(tweet, includes)
        post = ImageWithOptionalTextPost(text=text, image=image)
        return json.loads(post.json())
