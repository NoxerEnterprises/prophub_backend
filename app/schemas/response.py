from typing import Any, Generic, TypeVar

from pydantic import BaseModel
from pydantic.generics import GenericModel

T = TypeVar("T")


class APIResponse(GenericModel, Generic[T]):
    success: bool
    message: str
    data: T | None = None
    errors: Any | None = None


def success_response(message: str, data: Any | None = None) -> dict[str, Any]:
    return {
        "success": True,
        "message": message,
        "data": data,
        "errors": None,
    }


def error_response(message: str, errors: Any | None = None) -> dict[str, Any]:
    return {
        "success": False,
        "message": message,
        "data": None,
        "errors": errors,
    }
