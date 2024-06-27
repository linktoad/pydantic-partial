"""
A solution to https://github.com/pydantic/pydantic/issues/7140
"""

from __future__ import annotations
from typing import Any, Type, Optional

from pydantic import BaseModel, ValidationError, field_validator, model_validator

SENTINEL = object()


def validate_model(
    model: Type[BaseModel], input_data: Any
) -> tuple[dict[str, Any], set[str], Optional[ValidationError]]:
    """
    Pydantic V2 implementation of the core bits of Pydantic V1's `validate_model`.
    https://github.com/pydantic/pydantic/blob/0454fabbc116ea78df0e29756a122cdbeba631d8/pydantic/v1/main.py#L1032

    Returns:
        `values`: A dict containing the validated data.
        `fields_set`: The set of field names which passed validation.
        `ValidationError | None`: `ValidationError` if there were errors.
    """

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
    def build_model_validation_error(self) -> PartialModel:
        if self.invalid_fields:
            self._validation_error = ValidationError.from_exception_data(
                title=type(self).__bases__[0].__name__,
                line_errors=[getattr(self, field)[1] for field in self.invalid_fields],
            )
        for field in self.invalid_fields:  # Don't show invalids in model repr.
            self.model_fields[field].repr = False  # Not core logic but it's pretty neat.
        return self

    @property
    def invalid_fields(self) -> list[str]:
        return [
            k
            for k in self.model_fields
            if (v := getattr(self, k)) and isinstance(v, tuple) and v[0] is SENTINEL
        ]


if __name__ == "__main__":

    class Model(PartialModel):
        a: str
        b: int
        c: bool
        d: float


data = {"a": "foo", "b": TypeError, "d": True}

a, b, c = validate_model(Model, data)

"""
>>> a
{'a': 'foo', 'd': 1.0}
>>> b
{'d', 'a'}
>>> c
2 validation errors for Model
b
  Input should be a valid integer [type=int_type, input_value=<class 'TypeError'>, input_type=type]
    For further information visit https://errors.pydantic.dev/2.7/v/int_type
c
  Field required [type=missing, input_value={'a': 'foo', 'b': <class 'TypeError'>, 'd': True}, input_type=dict]
    For further information visit https://errors.pydantic.dev/2.7/v/missing
"""
