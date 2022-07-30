from abc import ABC, abstractmethod
from typing import Generic, TypeVar

from kilroy_ws_server_py_sdk import AppError, JSON

from kilroy_face_twitter.errors import PARAMETER_GET_ERROR, PARAMETER_SET_ERROR
from kilroy_face_twitter.types import StateType

ParameterType = TypeVar("ParameterType")


class Parameter(ABC, Generic[StateType, ParameterType]):
    async def get(self, state: StateType) -> ParameterType:
        try:
            return await self._get(state)
        except AppError as e:
            raise e
        except Exception as e:
            raise PARAMETER_GET_ERROR from e

    async def set(
        self,
        state: StateType,
        value: ParameterType,
    ) -> None:
        if (await self.get(state)) == value:
            return
        try:
            await self._set(state, value)
        except AppError as e:
            raise e
        except Exception as e:
            raise PARAMETER_SET_ERROR from e

    @abstractmethod
    async def _get(self, state: StateType) -> ParameterType:
        pass

    @abstractmethod
    async def _set(
        self,
        state: StateType,
        value: ParameterType,
    ) -> None:
        pass

    @abstractmethod
    def name(self, state: StateType) -> str:
        pass

    @abstractmethod
    def schema(self, state: StateType) -> JSON:
        pass

    def ui_schema(self, state: StateType) -> JSON:
        return {}
