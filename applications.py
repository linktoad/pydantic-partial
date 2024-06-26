from __future__ import annotations
from typing import Any, Optional

from pydantic import (
    BaseModel,
    RootModel,
    ValidationError,
    field_validator,
    model_validator,
    computed_field,
    ValidatorFunctionWrapHandler,
    ValidationInfo,
)

SENTINEL = object()


class Error(BaseModel):
    field: str
    type: str = "missing"
    msg: str = "Field required"
    input: Any = None

    @model_validator(mode="before")
    def get_field_name_from_context(cls, data: Any, info: ValidationInfo) -> Any:
        if not isinstance(data, dict):
            return data
        return {"field": (info.context or {}).get("field")} | data


class Errors(RootModel):
    root: list[Error] = []


class MissingOrInvaidAllowed(BaseModel):
    _errors: Errors = Errors()

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
            return Errors([Error(field=info.field_name)])
        try:
            return handler(v)
        except ValidationError as ex:
            return Errors.model_validate_json(ex.json(), context={"field": info.field_name})

    @model_validator(mode="after")
    def save_errors_and_set_none(self) -> MissingOrInvaidAllowed:
        for field in self.model_fields:
            value = getattr(self, field)
            if isinstance(value, Errors):
                self._errors.root.extend(value.root)
                setattr(self, field, None)
        return self

    @computed_field
    @property
    def errors(self) -> Optional[Errors]:
        return self._errors if self._errors.root else None


if __name__ == "__main__":
    from datetime import datetime

    class Model(MissingOrInvaidAllowed):
        a: str
        b: datetime
        c: int
        d: float
        e: bool

    data = {
        "a": 3,
        "b": False,
        "c": "foo",
        "d": "bar",
        "e": datetime.now(),
    }

    m = Model.model_validate(data)
    print(m.model_dump_json(indent=4))

    # And then can just insert m.errors.model_dump_json() ::JSONB

    """
    {
        "a": null,
        "b": null,
        "c": null,
        "d": null,
        "e": null,
        "errors": [
            {
                "field": "a",
                "type": "string_type",
                "msg": "Input should be a valid string",
                "input": 3
            },
            {
                "field": "b",
                "type": "datetime_type",
                "msg": "Input should be a valid datetime",
                "input": false
            },
            {
                "field": "c",
                "type": "int_parsing",
                "msg": "Input should be a valid integer, unable to parse string as an integer",
                "input": "foo"
            },
            {
                "field": "d",
                "type": "float_parsing",
                "msg": "Input should be a valid number, unable to parse string as a number",
                "input": "bar"
            },
            {
                "field": "e",
                "type": "bool_type",
                "msg": "Input should be a valid boolean",
                "input": "2024-06-26T12:17:14.329990"
            }
        ]
    }
    """
