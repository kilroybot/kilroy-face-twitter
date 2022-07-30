from abc import ABC
from base64 import urlsafe_b64decode, urlsafe_b64encode
from copy import deepcopy
from pathlib import Path
from typing import Any, Dict, Optional, TypeVar
from urllib.parse import urlparse

import httpx
from tweepy import Tweet

from kilroy_face_twitter.client import TwitterClient

D = TypeVar("D", bound="Deepcopyable")


class Deepcopyable(ABC):
    async def __adeepcopy__(
        self: D, memo: Optional[Dict[int, Any]] = None
    ) -> D:
        memo = memo if memo is not None else {}
        new = self.__class__.__new__(self.__class__)
        memo[id(self)] = new
        await self.__adeepcopy_to__(new, memo)
        return new

    async def __adeepcopy_to__(self: D, new: D, memo: Dict[int, Any]) -> None:
        for name in self.__dict__:
            setattr(new, name, await self.__deepcopy_attribute__(name, memo))

    async def __deepcopy_attribute__(
        self, name: str, memo: Dict[int, Any]
    ) -> Any:
        return deepcopy(getattr(self, name), memo)


async def download_image(url: str) -> bytes:
    async with httpx.AsyncClient() as client:
        response = await client.get(url)
        return response.content


def base64_encode(value: bytes) -> str:
    return urlsafe_b64encode(value).decode("ascii")


def base64_decode(value: str) -> bytes:
    return urlsafe_b64decode(value.encode("ascii"))


def get_filename_from_url(url: str) -> str:
    return Path(urlparse(url).path).name


async def fetch_tweet(client: TwitterClient, tweet_id: int, **kwargs) -> Tweet:
    response = await client.v2.get_tweet(tweet_id, user_auth=True, **kwargs)
    return Tweet(response.data)
