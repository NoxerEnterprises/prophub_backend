from fastapi import HTTPException, status


class AppException(HTTPException):
    def __init__(self, status_code: int, message: str, details: object | None = None) -> None:
        super().__init__(status_code=status_code, detail={"message": message, "details": details})


class BadRequestError(AppException):
    def __init__(self, message: str = "Bad request", details: object | None = None) -> None:
        super().__init__(status.HTTP_400_BAD_REQUEST, message, details)


class UnauthorizedError(AppException):
    def __init__(self, message: str = "Authentication required", details: object | None = None) -> None:
        super().__init__(status.HTTP_401_UNAUTHORIZED, message, details)


class ForbiddenError(AppException):
    def __init__(self, message: str = "You do not have permission to perform this action", details: object | None = None) -> None:
        super().__init__(status.HTTP_403_FORBIDDEN, message, details)


class NotFoundError(AppException):
    def __init__(self, message: str = "Resource not found", details: object | None = None) -> None:
        super().__init__(status.HTTP_404_NOT_FOUND, message, details)


class ConflictError(AppException):
    def __init__(self, message: str = "Resource already exists", details: object | None = None) -> None:
        super().__init__(status.HTTP_409_CONFLICT, message, details)
