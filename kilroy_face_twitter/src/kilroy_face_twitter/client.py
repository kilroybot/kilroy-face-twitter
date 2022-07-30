from tweepy import API, OAuth1UserHandler
from tweepy.asynchronous import AsyncClient


class TwitterClient:
    def __init__(
        self,
        consumer_key: str,
        consumer_secret: str,
        access_token: str,
        access_token_secret: str,
        wait_on_rate_limit: bool = True,
    ) -> None:
        self._v1 = API(
            OAuth1UserHandler(
                consumer_key,
                consumer_secret,
                access_token,
                access_token_secret,
            ),
            wait_on_rate_limit=wait_on_rate_limit,
        )
        self._v2 = AsyncClient(
            consumer_key=consumer_key,
            consumer_secret=consumer_secret,
            access_token=access_token,
            access_token_secret=access_token_secret,
            wait_on_rate_limit=wait_on_rate_limit,
        )

    @property
    def v1(self) -> API:
        return self._v1

    @property
    def v2(self) -> AsyncClient:
        return self._v2
