from abc import ABC

from humps import camelize
from pydantic import BaseModel


class BasePostModel(BaseModel, ABC):
    def json(self, *args, by_alias: bool = True, **kwargs) -> str:
        return super().json(*args, by_alias=by_alias, **kwargs)

    class Config:
        allow_population_by_field_name = True
        alias_generator = camelize


class TextData(BasePostModel):
    content: str


class ImageData(BasePostModel):
    raw: str
    filename: str


class BasePost(BasePostModel, ABC):
    pass


class TextOnlyPost(BasePost):
    text: TextData


class ImageOnlyPost(BasePost):
    image: ImageData


class TextAndImagePost(BasePost):
    text: TextData
    image: ImageData
