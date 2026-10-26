"""
FRIENDLY ERROR MESSAGES for bad inputs.

FastAPI already rejects inputs of the wrong type (e.g. horizon=abc), but its own messages
are written for programmers. Here we swap them for plain-English ones.

Every input problem comes back with status 422 ("I understood the request, but the
values in it are not allowed") and this shape:
    {"error": "<the first problem, in plain English>",
     "problems": [{"field": "horizon", "message": "..."}, ...]}
"""

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.api.schemas import Method, Mode
from app.core.cushion import CONFIDENCE_LEVELS
from app.core.metrics import SLIDER_HOURS


def _listed(values):
    return ", ".join(str(v) for v in values)


HORIZON_MAX = max(SLIDER_HOURS)

FRIENDLY_MESSAGES = {
    "horizon": (
        f"horizon must be a whole number of hours from 0 to {HORIZON_MAX}. "
        f"{HORIZON_MAX} is the limit because it is the furthest ahead that EVERY hour of "
        "January 2026 still has a forecast published in time. Further ahead, some hours "
        "would have no forecast at all, so the numbers would not be comparable."
    ),
    "mode": f"mode must be one of: {_listed(m.value for m in Mode)}.",
    "confidence": (
        f"confidence must be one of: {_listed(CONFIDENCE_LEVELS)} "
        "(the % of hours the cushion should cover)."
    ),
    "method": (
        f"method must be one of: {_listed(m.value for m in Method)} "
        "(per_group is experimental: it failed the back-test)."
    ),
    "start": "start must be a date written as YYYY-MM-DD, for example 2026-01-15.",
    "end": "end must be a date written as YYYY-MM-DD, for example 2026-01-15.",
    "date": "date must be a date written as YYYY-MM-DD, for example 2026-01-15.",
}


class InputError(Exception):
    """Raise this from an endpoint when an input is the right type but not allowed."""

    def __init__(self, field, message):
        super().__init__(message)
        self.field = field
        self.message = message


def _reply(problems):
    return JSONResponse(
        status_code=422, content={"error": problems[0]["message"], "problems": problems}
    )


async def _on_validation_error(request: Request, exc: RequestValidationError):
    """FastAPI's own type checks failed: replace its messages with ours."""
    problems, seen = [], set()
    for error in exc.errors():
        field = str(error["loc"][-1])
        if field not in seen:  # one message per field is enough
            seen.add(field)
            problems.append({"field": field, "message": FRIENDLY_MESSAGES.get(field, error["msg"])})
    return _reply(problems)


async def _on_input_error(request: Request, exc: InputError):
    return _reply([{"field": exc.field, "message": exc.message}])


def register(app: FastAPI):
    """Tell the app to use the handlers above."""
    app.add_exception_handler(RequestValidationError, _on_validation_error)
    app.add_exception_handler(InputError, _on_input_error)
