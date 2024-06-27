from typing import Any, Type, Optional

from pydantic import BaseModel, ValidationError, field_validator, model_validator

SENTINEL = object()


def validate_model(
    model: Type[BaseModel], input_data: Any
) -> tuple[dict[str, Any], set[str], Optional[ValidationError]]:
    """Pydantic V2 implementation of the core bits of Pydantic V1's `validate_model`"""

    class Model_(model, PartialModel):
        pass

    model_ = Model_.model_validate(input_data)
    fields_set = model_.model_fields.keys() - set(model_.invalid_fields)
    values = model_.model_dump(exclude=model_.invalid_fields)
    return values, fields_set, model_._validation_error


class PartialModel(BaseModel):
    _validation_error: Optional[ValidationError] = None

    @model_validator(mode="before")
    @classmethod
    def missing_fields_as_sentinels(cls, data: Any) -> Any:
        if not isinstance(data, dict):
            return data
        return data | {
            field: (SENTINEL, data)
            for field, field_info in cls.model_fields.items()
            if field_info.is_required() and field not in data
        }

    @field_validator("*", mode="wrap")
    @classmethod
    def gracefully_handle_validation_errors(cls, v, handler, info):
        if isinstance(v, tuple) and v and v[0] is SENTINEL:
            error = dict(type="missing", loc=(info.field_name,), input=v[1], ctx=info.context or {})
            return (SENTINEL, error)
        try:
            return handler(v)
        except ValidationError as ex:
            return (SENTINEL, ex.errors()[0] | dict(loc=(info.field_name,)))

    @model_validator(mode="after")
    def build_model_validation_error(self) -> "PartialModel":
        if self.invalid_fields:
            self._validation_error = ValidationError.from_exception_data(
                title=type(self).__bases__[0].__name__,
                line_errors=[getattr(self, field)[1] for field in self.invalid_fields],
            )
        return self

    @property
    def invalid_fields(self) -> list[str]:
        return [
            k
            for k in self.model_fields
            if (v := getattr(self, k)) and isinstance(v, tuple) and v[0] is SENTINEL
        ]


if __name__ == "__main__":
    from datetime import datetime

    class Model(BaseModel):
        a: datetime
        b: int
        c: bool
        d: str


    data = {
        "a": "2024-06-27",
        "b": "satoshi",
        "c": "on",
        # "d": 10
    }

    a, b, c = validate_model(Model, data)

    print(a)
    print(b)
    print(c)

    try:
        Model.model_validate(data)
    except Exception as ex:
        print(ex)
