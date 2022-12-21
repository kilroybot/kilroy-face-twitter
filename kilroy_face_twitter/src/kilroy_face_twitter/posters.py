from abc import ABC, abstractmethod
from io import BytesIO
from uuid import UUID

from kilroy_server_py_utils import (
    Categorizable,
    classproperty,
    normalize,
    base64_decode,
)
from tweepy import Tweet, User

from kilroy_face_twitter.client import TwitterClient
from kilroy_face_twitter.post import PostData, Post


class Poster(Categorizable, ABC):
    # noinspection PyMethodParameters
    @classproperty
    def category(cls) -> str:
        name: str = cls.__name__
        return normalize(name.removesuffix("Poster"))

    @abstractmethod
    async def post(self, client: TwitterClient, data: PostData) -> Post:
        pass


# Basic


class BasicPoster(Poster):
    async def post(self, client: TwitterClient, data: PostData) -> Post:
        kwargs = {}
        if data.text is not None:
            kwargs["text"] = data.text.content
        if data.image is not None:
            image_bytes = base64_decode(data.image.raw)
            with BytesIO(image_bytes) as file:
                media = client.v1.media_upload(
                    file=file, filename=data.image.filename
                )
            kwargs["media_ids"] = [media.media_id]
        response = await client.v2.create_tweet(**kwargs)
        tweet = Tweet(response.data)
        response = await client.v2.get_me()
        user = User(response.data)
        return Post(
            data=data,
            id=UUID(int=tweet.id),
            url=f"https://twitter.com/{user.username}/status/{tweet.id}",
        )
