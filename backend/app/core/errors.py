from fastapi import Request
from fastapi.responses import JSONResponse
import logging

log = logging.getLogger("app")


class AppError(Exception):
    def __init__(self, status: int, code: str, message: str):
        self.status, self.code, self.message = status, code, message


def install(app):
    @app.exception_handler(AppError)
    async def _app(_: Request, e: AppError):
        return JSONResponse({"error": {"code": e.code, "message": e.message}}, status_code=e.status)

    @app.exception_handler(Exception)
    async def _any(_: Request, e: Exception):
        log.exception("unhandled error")  # no secrets are logged: only the traceback
        return JSONResponse({"error": {"code": "internal_error", "message": "Unexpected server error"}}, status_code=500)
