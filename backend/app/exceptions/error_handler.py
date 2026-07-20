from fastapi import HTTPException

from app.exceptions.custom_exception import AppException


def to_http_exception(error: AppException) -> HTTPException:
    return HTTPException(status_code=error.status_code, detail=error.message)
