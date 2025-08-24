from functools import wraps
from typing import Any, Awaitable, Callable

from fastapi import HTTPException, Request
from fastapi.responses import RedirectResponse
from fastapi.security import HTTPAuthorizationCredentials
from starlette.templating import _TemplateResponse

from ..config import get_settings
from ..dependencies import DatabaseDependency, jwt_verification
from ..users.models import User

settings = get_settings()


def template_jwt_verification(
    func: Callable[..., Awaitable[_TemplateResponse]],
) -> Callable[..., Awaitable[_TemplateResponse | RedirectResponse]]:
    """
    Decorator to verify a JWT token from the request cookies before processing the request.
    Redirects to the login page if the token is missing or invalid.

    Args:
        func (Callable[..., Awaitable[_TemplateResponse]]): The endpoint function to wrap.

    Returns:
        Callable[..., Awaitable[_TemplateResponse | RedirectResponse]: A wrapped function that
            either proceeds to the original endpoint or redirects if not authorized.
    """

    @wraps(func)
    async def wrapper(
        request: Request, db: DatabaseDependency, *args: Any, **kwargs: Any
    ) -> RedirectResponse | _TemplateResponse:
        no_authorized_response = RedirectResponse(str(request.url_for("login_page")))
        access_token = request.cookies.get(settings.cookies_key_jwt)

        if access_token is None:
            return no_authorized_response

        try:
            credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials=access_token)
            user: User = await jwt_verification(db, credentials)
            request.state.user = user
        except HTTPException:
            return no_authorized_response

        return await func(request, db, *args, **kwargs)

    return wrapper
