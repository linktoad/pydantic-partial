from __future__ import annotations

from typing import Any

from pydantic import (
    BaseModel,
    Field,
    ValidationError,
    ValidationInfo,
    ValidatorFunctionWrapHandler,
    computed_field,
    field_validator,
    model_validator,
)

SENTINEL = object()


class Error(BaseModel):
    field: str
    type: str = "missing"
    msg: str = "Field required"
    input: Any = Field(default=None, exclude=True)


class MissingOrInvalidAsNone(BaseModel):
    _errors: list[Error] = []

    @model_validator(mode="before")
    @classmethod
    def missing_fields_as_sentinels(cls, data: Any) -> Any:
        if not isinstance(data, dict):
            return data
        return data | {
            field: SENTINEL
            for field, field_info in cls.model_fields.items()
            if field_info.is_required() and field not in data
        }

    @field_validator("*", mode="wrap")
    @classmethod
    def gracefully_handle_validation_errors(
        cls, v: Any, handler: ValidatorFunctionWrapHandler, info: ValidationInfo
    ) -> Any:
        if v is SENTINEL:
            return Error(field=info.field_name)
        try:
            return handler(v)
        except ValidationError as ex:
            return Error(field=info.field_name, **ex.errors()[0])

    @model_validator(mode="after")
    def save_errors_and_set_none(self) -> MissingOrInvalidAsNone:
        for field, value in self:
            if isinstance(value, Error):
                self._errors.append(value)
                setattr(self, field, None)  # Could set it to anything you want for your app
        return self

    @computed_field
    @property
    def errors(self) -> list[Error]:
        return self._errors


if __name__ == "__main__":

    class Model(MissingOrInvalidAsNone):
        a: int
        b: bool
        c: str
        d: float

    json_data = """
    {
        "a": "3",
        "b": "something",
        "c": null
    }
    """

    m = Model.model_validate_json(json_data)
    print(m.model_dump_json(indent=4))

    """
    {
        "a": 3,
        "b": null,
        "c": null,
        "d": null,
        "errors": [
            {
                "field": "b",
                "type": "bool_parsing",
                "msg": "Input should be a valid boolean, unable to interpret input"
            },
            {
                "field": "c",
                "type": "string_type",
                "msg": "Input should be a valid string"
            },
            {
                "field": "d",
                "type": "missing",
                "msg": "Field required"
            }
        ]
    }
    """
