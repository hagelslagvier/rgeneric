from datetime import timedelta

from fastapi import APIRouter, Depends
from fastapi.security import OAuth2PasswordRequestForm
from injector import Injector

from app.config import Config
from app.dependencies.injector import make_injector
from app.interactors.auth.errors import UserNotFoundError
from app.interactors.auth.interfaces import AuthInterface
from app.interactors.auth.secret_manager import SecretVerificationError

router = APIRouter(
    prefix="/tokens",
    tags=["tokens"],
)


@router.post("/")
def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    injector: Injector = Depends(make_injector),
) -> dict:
    config = injector.get(Config)
    auth = injector.get(AuthInterface)

    login, password = form_data.username, form_data.password

    try:
        user = auth.get_user(login=login)
    except UserNotFoundError:
        # logging here
        raise

    try:
        auth.authenticate(secret=password, hash=user.password)
    except SecretVerificationError:
        # logging here
        raise

    payload = {"sub": login}

    refresh_token_ttl = timedelta(minutes=config.refresh_token_expiration_minutes)
    refresh_token = auth.create_token(payload=payload, ttl=refresh_token_ttl)

    access_token_ttl = timedelta(minutes=config.access_token_expiration_minutes)
    access_token = auth.create_token(payload=payload, ttl=access_token_ttl)

    return {
        "refresh_token": refresh_token,
        "access_token": access_token,
        "token_type": "bearer",
    }
