from __future__ import annotations

from typing import Any

from pydantic import (
    BaseModel,
    ConfigDict,
    RootModel,
    ValidationError,
    ValidationInfo,
    ValidatorFunctionWrapHandler,
    computed_field,
    field_validator,
    model_validator,
)

SENTINEL = object()


class Error(BaseModel):
    model_config = ConfigDict(validate_default=True)

    field: str = None
    type: str = "missing"
    msg: str = "Field required"
    input: Any = None

    @field_validator("field", mode="before")
    def set_field_name_from_context(cls, v: Any, info: ValidationInfo) -> Any:
        return v or info.context


class Errors(RootModel):
    root: list[Error] = []


class MissingOrInvalidAsNone(BaseModel):
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
            return Errors.model_validate_json(ex.json(), context=info.field_name)
            # Pydantic has serialised the error input values for us. Lets use this instead!

    @model_validator(mode="after")
    def save_errors_and_set_none(self) -> MissingOrInvalidAsNone:
        for field, value in self:
            if isinstance(value, Errors):
                self._errors.root.extend(value.root)
                setattr(self, field, None)
        return self

    @computed_field
    @property
    def errors(self) -> Errors:
        return self._errors


if __name__ == "__main__":
    from datetime import datetime

    class Model(MissingOrInvalidAsNone):
        a: str
        b: datetime
        c: int
        d: float
        e: bool
        f: tuple
        g: list

    data = {
        "a": "this passes!",
        "b": False,
        "c": "foo",
        "d": None,
        "e": datetime.now(),
        "f": TypeError,
        # "g": [],
    }

    m = Model.model_validate(data)
    print(m.model_dump_json(indent=4))

    # And then can just insert m.errors.model_dump_json() if m.errors.root else None ::JSONB

    """
    {
        "a": "this passes!",
        "b": null,
        "c": null,
        "d": null,
        "e": null,
        "f": null,
        "g": null,
        "errors": [
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
                "type": "float_type",
                "msg": "Input should be a valid number",
                "input": null
            },
            {
                "field": "e",
                "type": "bool_type",
                "msg": "Input should be a valid boolean",
                "input": "2024-06-26T15:57:33.276163"
            },
            {
                "field": "f",
                "type": "tuple_type",
                "msg": "Input should be a valid tuple",
                "input": "<class 'TypeError'>"
            },
            {
                "field": "g",
                "type": "missing",
                "msg": "Field required",
                "input": null
            }
        ]
    }
    """
