"""
Registered once in main.py via register_error_handlers(app). Two rules:
1. A ReportBuilderError (and subclasses) is safe to show — pass its message through.
2. Anything else (a real bug) gets a generic 500 message — the real exception
   still goes to the server logs, just never to the response body.
"""

import logging

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from errors.exceptions import ReportBuilderError

logger = logging.getLogger("report_builder")


def register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(ReportBuilderError)
    async def handle_known_error(request: Request, exc: ReportBuilderError):
        return JSONResponse(status_code=exc.status_code, content={"error": str(exc)})

    @app.exception_handler(Exception)
    async def handle_unknown_error(request: Request, exc: Exception):
        logger.exception("Unhandled error on %s %s", request.method, request.url)
        return JSONResponse(
            status_code=500,
            content={"error": "An internal error occurred. Please try again or contact support."},
        )
