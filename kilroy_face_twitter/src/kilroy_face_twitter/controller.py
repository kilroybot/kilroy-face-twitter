from typing import AsyncIterable, Awaitable

from kilroy_face_server_py_sdk import (
    Config,
    ConfigNotification,
    ConfigSchema,
    ConfigSetReply,
    ConfigSetRequest,
    FaceController,
    PostReply,
    PostRequest,
    PostSchema,
    ScoreReply,
    ScoreRequest,
    ScrapReply,
    ScrapRequest,
    Status,
    StatusEnum,
    StatusNotification,
)

from kilroy_face_twitter.face import TwitterFace


class TwitterController(FaceController):
    def __init__(self, face: TwitterFace) -> None:
        super().__init__()
        self._face = face

    async def post_schema(self) -> PostSchema:
        return PostSchema(post_schema=self._face.post_json_schema)

    async def status(self) -> Status:
        ready = await self._face.is_ready()
        return Status(status=StatusEnum.ready if ready else StatusEnum.loading)

    async def watch_status(self) -> AsyncIterable[StatusNotification]:
        old = await self.status()
        async for ready in self._face.watch_ready():
            new = Status(
                status=StatusEnum.ready if ready else StatusEnum.loading
            )
            yield StatusNotification(old=old, new=new)
            old = new

    async def config(self) -> Config:
        return Config(config=await self._face.get_config())

    async def config_schema(self) -> ConfigSchema:
        return ConfigSchema(
            config_schema=self._face.config_json_schema,
            ui_schema=self._face.config_ui_schema,
        )

    async def watch_config(self) -> AsyncIterable[ConfigNotification]:
        old = await self.config()
        async for config in self._face.watch_config():
            new = Config(config=config)
            yield ConfigNotification(old=old, new=new)
            old = new

    async def set_config(
        self, request: Awaitable[ConfigSetRequest]
    ) -> ConfigSetReply:
        old = await self.config()
        config = await self._face.set_config((await request).set.config)
        new = Config(config=config)
        return ConfigSetReply(old=old, new=new)

    async def post(self, request: Awaitable[PostRequest]) -> PostReply:
        post = (await request).post
        post_id = await self._face.post(post)
        return PostReply(post_id=post_id)

    async def score(self, request: Awaitable[ScoreRequest]) -> ScoreReply:
        post_id = (await request).post_id
        score = await self._face.score(post_id)
        return ScoreReply(score=score)

    async def scrap(
        self, request: Awaitable[ScrapRequest]
    ) -> AsyncIterable[ScrapReply]:
        request = await request
        async for post_id, post in self._face.scrap(
            request.limit, request.before, request.after
        ):
            yield ScrapReply(post_id=post_id, post=post)
