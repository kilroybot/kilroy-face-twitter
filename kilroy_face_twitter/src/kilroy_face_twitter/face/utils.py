from abc import ABC, abstractmethod
from asyncio import Queue
from contextlib import asynccontextmanager
from typing import (
    Any,
    AsyncIterable,
    Dict,
    Generic,
    Iterable,
    Type,
    TypeVar,
)
from uuid import uuid4

from kilroy_face_server_py_sdk import JSONSchema
from kilroy_ws_server_py_sdk import JSON

from kilroy_face_twitter.errors import (
    INVALID_CONFIG_ERROR,
    STATE_NOT_READY_ERROR,
)
from kilroy_face_twitter.face.parameters import Parameter
from kilroy_face_twitter.types import StateType

T = TypeVar("T")


class Observable(ABC):
    _queues: Dict[str, Dict[Any, Queue]]

    def __init__(self) -> None:
        self._queues = {}

    @asynccontextmanager
    async def _create_queue(self, topic: str) -> Queue:
        queue_id = uuid4()
        queue = Queue()

        if topic not in self._queues:
            self._queues[topic] = {}
        self._queues[topic][queue_id] = queue

        yield queue

        self._queues[topic].pop(queue_id)
        if len(self._queues[topic]) == 0:
            self._queues.pop(topic)

    async def _subscribe(self, topic: str) -> AsyncIterable[Any]:
        async with self._create_queue(topic) as queue:
            while (message := await queue.get()) is not None:
                yield message

    async def _notify(self, topic: str, message: Any) -> None:
        for queue in self._queues.get(topic, {}).values():
            await queue.put(message)


class Loadable(Observable, Generic[StateType], ABC):
    __state: StateType
    __ready: bool

    def __init__(self) -> None:
        super().__init__()
        self.__ready = False

    @classmethod
    async def build(cls: Type[T], *args, **kwargs) -> T:
        instance = cls()
        await instance.__ainit__(*args, **kwargs)
        return instance

    async def __ainit__(self, *args, **kwargs) -> None:
        self.__state = await self._create_initial_state(*args, **kwargs)
        await self._set_ready(True)

    @abstractmethod
    async def _create_initial_state(self, *args, **kwargs) -> StateType:
        pass

    async def cleanup(self) -> None:
        await self._destroy_state(self.__state)

    async def _set_ready(self, value: bool) -> None:
        self.__ready = value
        await self._notify("ready", value)

    @asynccontextmanager
    async def _loading(self) -> StateType:
        await self._set_ready(False)
        try:
            state = await self._copy_state(self.__state)
            yield state
            old_state = self.__state
            self.__state = state
            await self._destroy_state(old_state)
        finally:
            await self._set_ready(True)

    @property
    def _state(self) -> StateType:
        if not self.__ready:
            raise STATE_NOT_READY_ERROR
        return self.__state

    @staticmethod
    async def _copy_state(state: StateType) -> StateType:
        return await state.__adeepcopy__()

    @staticmethod
    async def _destroy_state(state: StateType) -> None:
        pass

    async def is_ready(self) -> bool:
        return self.__ready

    async def watch_ready(self) -> AsyncIterable[bool]:
        async for ready in self._subscribe("ready"):
            yield ready


class Configurable(Loadable[StateType], Generic[StateType], ABC):
    async def get_config(self) -> JSON:
        params = self._parameters_mapping(self._state)
        return {
            name: await parameter.get(self._state)
            for name, parameter in params.items()
        }

    async def set_config(self, config: JSON) -> JSON:
        async with self._loading() as state:
            params = self._parameters_mapping(state)
            for name, value in config.items():
                try:
                    await params[name].set(state, value)
                except Exception as e:
                    raise INVALID_CONFIG_ERROR from e

        config = await self.get_config()
        await self._notify("config", config)
        return config

    async def watch_config(self) -> AsyncIterable[JSON]:
        async for config in self._subscribe("config"):
            yield config

    @property
    def config_json_schema(self) -> JSONSchema:
        return JSONSchema(
            {
                "title": "Face config schema",
                "type": "object",
                "properties": self.config_properties_schema,
            }
        )

    @property
    def config_properties_schema(self) -> JSON:
        params = self._parameters_mapping(self._state)
        return {
            name: parameter.schema(self._state)
            for name, parameter in params.items()
        }

    @property
    def config_ui_schema(self) -> JSON:
        params = self._parameters_mapping(self._state)
        return {
            name: parameter.ui_schema(self._state)
            for name, parameter in params.items()
        }

    def _parameters_mapping(self, state: StateType) -> Dict[str, Parameter]:
        return {
            parameter.name(state): parameter for parameter in self._parameters
        }

    @property
    def _parameters(self) -> Iterable[Parameter]:
        return []
