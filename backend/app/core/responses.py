"""Consistent JSON envelope used by every endpoint:

    {"success": true, "message": "...", "data": ...}
    {"success": false, "message": "...", "errors": ...}
"""
from typing import Any

from fastapi import Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException


def ok(data: Any = None, message: str = "OK") -> dict:
    return {"success": True, "message": message, "data": jsonable_encoder(data)}


def paginated(items: list, total: int, page: int, page_size: int, message: str = "OK") -> dict:
    return ok({"items": items, "total": total, "page": page, "page_size": page_size}, message)


async def http_exception_handler(_: Request, exc: StarletteHTTPException) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content={"success": False, "message": str(exc.detail), "errors": None},
        headers=getattr(exc, "headers", None),
    )


async def validation_exception_handler(_: Request, exc: RequestValidationError) -> JSONResponse:
    errors = [
        {"field": ".".join(str(p) for p in e["loc"] if p != "body"), "message": e["msg"]}
        for e in exc.errors()
    ]
    return JSONResponse(
        status_code=422,
        content={"success": False, "message": "Validation failed", "errors": errors},
    )
