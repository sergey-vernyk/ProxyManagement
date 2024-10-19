import logging
from typing import Any, Awaitable, Callable

from fastapi import Request
from fastapi.responses import JSONResponse


def custom_error_handler(
    status_code: int, initial_detail: str, logger: logging.Logger | None = None
) -> Callable[..., Awaitable[JSONResponse]]:
    """
    Returns a custom exception handler for FastAPI that logs errors
    and returns a JSON response with the provided status code.

    Args:
        status_code (int): The HTTP status code to return with the JSON response.
            initial_detail (str): The initial detail message to return in the response
            if no specific message is provided by the exception.
        logger (logging.Logger | None): An optional logger for logging exception details.
            If provided, the logger will log the exception message and additional context if available.

    Returns:
        Callable[..., Awaitable[JSONResponse]]: A coroutine-based exception handler function that
            logs the error (if a logger is provided) and returns a JSON response
            with the given status code and message.

    Usage Example:
        ```python
            app = FastAPI()

            app.add_exception_handler(
                exc_class_or_status_code=EntityDoesNotExistError,
                handler=custom_error_handler(
                    status_code=404,
                    initial_detail="Not Found",
                    logger=my_logger,
                ),
            )
        ```
    """
    detail = {"message": initial_detail}

    async def exception_handler(_: Request, exc: "ProxyManagementApiError") -> JSONResponse:
        if exc.message:
            detail["message"] = exc.message

        if logger is not None:
            extra = exc.logger_extra_data if hasattr(exc, "logger_extra_data") else {}
            logger.info(exc, extra=extra)

        return JSONResponse({"detail": detail["message"]}, status_code)

    return exception_handler


class ProxyManagementApiError(Exception):
    """
    Base exceptions class.
    """

    def __init__(self, message: str, logger_extra_data: dict[str, Any] | None = None) -> None:
        self.message = message
        self.logger_extra_data = logger_extra_data
        super().__init__(self.message)


class UserUnauthorizeExceptionError(ProxyManagementApiError):
    """
    User not authenticated via OAuth2 flow or via email and password.
    """


class EntityDoesNotExistError(ProxyManagementApiError):
    """
    Entity is not found in the database.
    """
