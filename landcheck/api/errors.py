"""Standard error object (PRD Section 12.7)."""

import logging
from typing import Any

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

log = logging.getLogger(__name__)


class ApiError(Exception):
    def __init__(
        self, status: int, code: str, message: str, details: dict[str, Any] | None = None
    ) -> None:
        super().__init__(message)
        self.status = status
        self.code = code
        self.message = message
        self.details = details or {}


def error_body(code: str, message: str, details: dict[str, Any] | None = None) -> dict:
    return {"error": {"code": code, "message": message, "details": details or {}}}


def install_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(ApiError)
    async def _api_error(_: Request, exc: ApiError) -> JSONResponse:
        return JSONResponse(error_body(exc.code, exc.message, exc.details), exc.status)

    @app.exception_handler(Exception)
    async def _internal_error(request: Request, exc: Exception) -> JSONResponse:
        # Details stay in the server log, never in the response.
        log.exception("Unhandled error on %s %s", request.method, request.url.path)
        return JSONResponse(error_body("INTERNAL_ERROR", "Unexpected server error."), 500)
