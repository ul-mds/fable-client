from typing import Any

from pydantic import BaseModel, Field


class FakerGeneratorSpec(BaseModel):
    function_name: str
    attribute_name: str
    args: dict[str, Any] = Field(default_factory=dict)


def _default_faker_locale():
    return ["en_US"]


class FakerGeneratorConfig(BaseModel):
    seed: int
    count: int = Field(ge=0)
    locale: list[str] = Field(default_factory=_default_faker_locale)
    generators: list[FakerGeneratorSpec]
