from typing import Optional
from uuid import UUID

from kilroy_face_py_shared import SerializableModel
from kilroy_server_py_utils import base64_encode
from tweepy import Tweet

from kilroy_face_twitter.data import TweetIncludes
from kilroy_face_twitter.utils import download_image, get_filename_from_url


class PostTextData(SerializableModel):
    content: str


class PostImageData(SerializableModel):
    raw: str
    filename: Optional[str]


class PostData(SerializableModel):
    text: Optional[PostTextData]
    image: Optional[PostImageData]


class Post(SerializableModel):
    data: PostData
    id: UUID
    url: str

    @classmethod
    async def from_tweet(cls, tweet: Tweet, includes: TweetIncludes) -> "Post":
        text = None
        image = None
        if tweet.text is not None:
            text = PostTextData(content=tweet.text)
        media_keys = (tweet.attachments or {}).get("media_keys", [])
        if len(media_keys) > 0:
            media_key = media_keys[0]
            try:
                image_url = next(
                    media.url
                    for media in includes.media
                    if media.media_key == media_key
                )
                image = PostImageData(
                    raw=base64_encode(await download_image(image_url)),
                    filename=get_filename_from_url(image_url),
                )
            except StopIteration:
                pass
        return cls(
            data=PostData(text=text, image=image),
            id=UUID(int=tweet.id),
            url=f"https://twitter.com/twitter/status/{tweet.id}",
        )
