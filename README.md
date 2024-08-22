# pydantic-partial

Proof of concept of how to allow partially validated pydantic models to be instantiated.

It makes use of the less commonly used wrap field validator (and I suppose wrap mode in general).

I will note though, you should ***exercise caution*** with these models.

## Motivation

I wanted to ingest JSON API data that sometimes would fail validation (e.g. allowing mistakes to be made by the third-party) instead of effectively throwing that response away.

My goal was to store this in Postgres and have an errors JSONB column to capture the validation errors along with the input for context.

See [applications.py](https://github.com/linktoad/pydantic-partial/blob/main/applications.py) for the implementation.

## Notes

**Requires Python3.9+**

## Acknowledgements

I'd like to express my appreciation to Fred Baptiste from MathByte Academy for creating a tutorial on this technique.

You can find the video here: [https://www.youtube.com/watch?v=BtyA-mN0VIA](https://www.youtube.com/watch?v=BtyA-mN0VIA)