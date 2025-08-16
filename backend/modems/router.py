"""
Module contains endpoints for modems:
- create_modem
- get_modem
- get_all_modems
- update_modem
- delete_modem
- get_change_ip_urls
"""

import hashlib
from ipaddress import IPv4Address
from typing import Annotated, Any, cast

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.encoders import jsonable_encoder
from fastapi.requests import Request
from pydantic import EmailStr, IPvAnyAddress
from pydantic_core import Url

from common.utils import get_base_url, get_caller_info
from config import get_settings
from dependencies import CsrfVerifyDependency, DatabaseDependency, jwt_verification
from exceptions import ClientRequestError, EntityDoesNotExistError
from logs.logging_conf import build_logger_extra_data, get_endpoint_logger
from users.crud import get_user_by_email
from users.models import User
from validators import validate_email_format

from . import crud, models, schemas

settings = get_settings()
logger = get_endpoint_logger()
router = APIRouter()

ENCODING: str = settings.default_encoding


@router.post(
    "/modems/",
    response_model=schemas.ShowModem,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(jwt_verification), CsrfVerifyDependency],
    description="Create a modem for a proxy.",
    operation_id="create-modem",
    responses={
        201: {"description": "Modem created"},
        400: {"description": "Modem exists"},
        404: {"description": "User not found"},
    },
)
async def create_modem(request: Request, body: schemas.CreateModem, db: DatabaseDependency) -> schemas.ShowModem:
    """
    Create modem or raise an exception if modem with provided IP is already exists.
    """
    db_modem = crud.get_modem_by_ip(db, str(body.ip))
    if db_modem is not None:
        raise ClientRequestError(
            "Modem with the given IP is already exists.",
            logger_extra_data={
                **build_logger_extra_data(request),
                **get_caller_info(),
            },
        )

    bind_db_user: User | None = None
    if body.bind_user_email is not None:
        bind_db_user = db.query(User).filter(User.email == body.bind_user_email).first()
        if bind_db_user is None:
            raise EntityDoesNotExistError(
                "User with the given email does not exist.",
                logger_extra_data={
                    **build_logger_extra_data(request),
                    **get_caller_info(),
                },
            )

    modem_data: dict[str, Any] = body.model_dump(
        exclude={
            "bind_user_email",
            "ip",
            "external_server_ip",
            "internal_server_ip",
            "external_server_host",
        }
    )
    modem_data["bind_user_id"] = bind_db_user.id if bind_db_user is not None else None
    modem_data["ip"] = str(body.ip)
    modem_data["external_server_ip"] = str(body.external_server_ip) if body.external_server_ip is not None else None
    modem_data["internal_server_ip"] = str(body.internal_server_ip) if body.internal_server_ip is not None else None
    modem_data["external_server_host"] = str(body.external_server_host)

    if bind_db_user is not None:
        modem_data["hashed_value"] = hashlib.sha256(
            f"{bind_db_user.email}{modem_data['ip']}".encode(ENCODING)
        ).hexdigest()[::2]

    modem = crud.create_modem(db, modem_data)
    show_modem = schemas.ShowModem(
        **jsonable_encoder(modem, exclude={"bind_user"}),
        bind_user_email=str(bind_db_user.email) if bind_db_user is not None else None,
    )

    return show_modem


@router.get(
    "/modems/{ip}",
    response_model=schemas.ShowModem,
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(jwt_verification)],
    description="Get modem by the given IP.",
    operation_id="get-modem-by-ip",
    responses={
        200: {"description": "Successfully"},
        404: {"description": "Modem not found"},
    },
)
async def get_modem(request: Request, ip: IPvAnyAddress, db: DatabaseDependency) -> schemas.ShowModem:
    """
    Return a modem by its `ip`.
    """
    db_modem = crud.get_modem_by_ip(db, str(ip))
    if db_modem is None:
        raise EntityDoesNotExistError(
            "Modem with the given IP does not exist.",
            logger_extra_data={
                **build_logger_extra_data(request),
                **get_caller_info(),
            },
        )

    db_modem_user = cast(User, db_modem.bind_user)
    show_modem = schemas.ShowModem(
        **jsonable_encoder(db_modem),
        bind_user_email=str(db_modem_user.email) if db_modem.bind_user is not None else None,
    )
    return show_modem


@router.get(
    "/modems/",
    response_model=list[schemas.ShowModem],
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(jwt_verification)],
    description="Get all modems within `skip` and `limit` params.",
    operation_id="get-modems",
    responses={200: {"description": "Successfully"}},
)
async def get_all_modems(db: DatabaseDependency, skip: int = 0, limit: int = 100) -> list[schemas.ShowModem]:
    """
    Return all modems within `skip` and `limit` params.
    """
    modems: list[models.Modem] = crud.get_all_modems(db, skip, limit)
    return [
        schemas.ShowModem(
            **jsonable_encoder(modem),
            bind_user_email=str(modem.bind_user.email) if modem.bind_user is not None else None,
        )
        for modem in modems
    ]


@router.put(
    "/modems/{ip}",
    response_model=schemas.ShowModem,
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(jwt_verification), CsrfVerifyDependency],
    description="Update a  modem data by the given IP.",
    responses={404: {"description": "Modem not found"}, 200: {"description": "Successfully"}},
)
async def update_modem(
    request: Request, ip: IPvAnyAddress, body: schemas.UpdateModem, db: DatabaseDependency
) -> schemas.ShowModem:
    """
    Update modem by its IP address.
    """
    db_modem = crud.get_modem_by_ip(db, str(ip))
    if db_modem is None:
        raise EntityDoesNotExistError(
            "Modem with the given IP does not exist.",
            logger_extra_data={
                **build_logger_extra_data(request),
                **get_caller_info(),
            },
        )

    bind_db_user: User | None = None
    if body.bind_user_email is not None:
        bind_db_user = db.query(User).filter(User.email == body.bind_user_email).first()
        if bind_db_user is None:
            raise EntityDoesNotExistError(
                "User with the given email does not exist.",
                logger_extra_data={
                    **build_logger_extra_data(request),
                    **get_caller_info(),
                },
            )

    data_to_update: dict[str, Any] = body.model_dump(exclude={"ip", "bind_user_email", "update_hashed_value"})
    data_to_update["ip"] = str(body.ip)
    data_to_update["external_server_ip"] = str(body.external_server_ip) if body.external_server_ip is not None else None
    data_to_update["external_server_port"] = body.external_server_port
    data_to_update["external_server_host"] = str(body.external_server_host)
    data_to_update["internal_server_ip"] = str(body.internal_server_ip) if body.internal_server_ip is not None else None
    data_to_update["bind_user_id"] = bind_db_user.id if bind_db_user is not None else None

    if bind_db_user is not None and body.update_hashed_value:
        data_to_update["hashed_value"] = hashlib.sha256(
            f"{bind_db_user.email}{data_to_update['ip']}".encode(ENCODING)
        ).hexdigest()[::2]

    modem = crud.update_modem(db, db_modem, data_to_update)
    show_modem = schemas.ShowModem(
        **jsonable_encoder(modem, exclude={"bind_user"}),
        bind_user_email=str(bind_db_user.email) if bind_db_user is not None else None,
    )
    return show_modem


@router.delete(
    "/modems/{ip}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(jwt_verification), CsrfVerifyDependency],
    description="Delete a modem by the given IP.",
    operation_id="delete-modem-by-ip",
    responses={204: {"description": "Successfully"}},
)
async def delete_modem(request: Request, ip: IPvAnyAddress, db: DatabaseDependency) -> None:
    """
    Delete a modem with `ip`.
    """
    db_modem = crud.get_modem_by_ip(db, str(ip))
    if db_modem is None:
        raise EntityDoesNotExistError(
            "Modem with the given IP does not exist.",
            logger_extra_data={
                **build_logger_extra_data(request),
                **get_caller_info(),
            },
        )

    crud.delete_modem(db, str(ip))


@router.get(
    "/modems/change_ip_urls/{email}",
    response_model=list[schemas.ChangeIPUrl],
    name="change_ip_urls",
    status_code=status.HTTP_200_OK,
    description="Get urls for changing IP for a modem(s) for a user with the given email.",
    operation_id="get-change-ip-urls",
    responses={
        400: {"description": "User not found"},
        422: {"description": "Sorting problems"},
        200: {"description": "Successfully"},
    },
)
async def get_change_ip_urls(
    request: Request,
    db: DatabaseDependency,
    email: EmailStr,
    order_by: Annotated[str, Query(description="Sorting criteria: ip, public_server_ip, port, etc.")] = "ip",
) -> list[schemas.ChangeIPUrl]:
    """
    Get url(s) for changing IP (by rebooting a modem) for a modem(s) for a user with the given email.
    """
    try:
        valid_email = validate_email_format(email)
    except ValueError as e:
        raise ClientRequestError(
            f"Email is invalid. Reason: {e}.",
            logger_extra_data={
                **build_logger_extra_data(request),
                **get_caller_info(),
            },
        ) from e

    db_user = get_user_by_email(db, valid_email)
    if db_user is None:
        raise EntityDoesNotExistError(
            message="User with the given email does not exist.",
            logger_extra_data={
                **build_logger_extra_data(request),
                **get_caller_info(),
            },
        )

    def get_urls_list(request: Request) -> list[schemas.ChangeIPUrl]:
        """
        Returns all urls for changing IP for all user's modems.

        Raises:
            HTTPException: if unable to sort response data by field received in `order_by` query param.
        """
        base_url = get_base_url(request)

        # try to sort user modems by the given criteria
        # if any of user modems has nullable values an exception will be raised
        try:
            user_modems: list[models.Modem] = sorted(db_user.user_modems, key=lambda m: getattr(m, order_by))
        except TypeError as e:
            logger.error(
                "Unable to sort records because some entries contains null values.",
                extra={
                    **build_logger_extra_data(request),
                    **get_caller_info(),
                },
            )
            raise HTTPException(
                status.HTTP_422_UNPROCESSABLE_ENTITY,
                "Unable to sort records because some entries contains null values. ",
            ) from e

        urls: list[schemas.ChangeIPUrl] = []

        for modem in user_modems:
            data = schemas.ChangeIPUrl(
                ip=IPv4Address(modem.ip),
                port=int(modem.port),  # type: ignore
                external_server_ip=(
                    IPv4Address(modem.external_server_ip) if modem.external_server_ip is not None else None
                ),
                external_server_host=Url(str(modem.external_server_host)),
                internal_server_ip=(
                    IPv4Address(modem.internal_server_ip) if modem.internal_server_ip is not None else None
                ),
                last_change_ip=f"{modem.rebooted:%Y-%m-%d %H:%M}" if modem.rebooted is not None else "---",
                url=Url(f"{base_url}/modems/{db_user.token}/{modem.hashed_value}"),
            )
            urls.append(data)

        return urls

    return get_urls_list(request)
