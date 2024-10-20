import logging
from typing import Any, Awaitable, Callable

from fastapi import Request
from fastapi.responses import JSONResponse


def custom_error_handler(
    status_code: int, initial_detail: str | dict[str, str], logger: logging.Logger | None = None
) -> Callable[..., Awaitable[JSONResponse]]:
    """
    Returns a custom exception handler for FastAPI that logs errors
    and returns a JSON response with the provided status code.

    Args:
        status_code (int): The HTTP status code to return with the JSON response.
            initial_detail (str | dict[str, str]): The initial detail message to return in the response
            if no specific message is provided by the exception.
        logger (logging.Logger | None): An optional logger for logging exception details.
            If provided, the logger will log the exception message and additional context if available.

    Returns:
        Callable[..., Awaitable[JSONResponse]]: A coroutine-based exception handler function that
            logs the error (if a logger is provided) and returns a JSON response
            with the given status code and message.

    Usage Example:
        ```python
        from fastapi import FastAPI

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
            logger.info(
                exc.message if isinstance(exc.message, str) else list(exc.message.values())[0],
                extra=extra,
            )

        return JSONResponse({"detail": detail["message"]}, status_code)

    return exception_handler


class ProxyManagementApiError(Exception):
    """
    Base exceptions class.
    """

    def __init__(self, message: str | dict[str, str], logger_extra_data: dict[str, Any] | None = None) -> None:
        self.message = message
        self.logger_extra_data = logger_extra_data
        super().__init__(self.message)


class UserUnauthorizedError(ProxyManagementApiError):
    """
    User not authenticated via OAuth2 flow or via email and password.
    Typically returns a 401 status.
    """


class EntityDoesNotExistError(ProxyManagementApiError):
    """
    Entity is not found in the database. Typically returns a 404 status.
    """


class ClientRequestError(ProxyManagementApiError):
    """
    Raised when a client's request cannot be handled properly due to invalid data.

    This could be triggered by invalid or duplicate inputs such as an already registered email,
    an invalid email format, or other request-related issues. Typically returns a 400 status.
    """
