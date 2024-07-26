import os
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv
from fastapi import FastAPI
from injector import Injector
from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session

from app.config import Config
from app.db.utils import migrate

ROOT_PATH = Path(__file__).parents[1]
ENV_BASE_PATH = ROOT_PATH / ".env.base"
ENV_DEV_PATH = ROOT_PATH / ".env.dev"

for path in [
    ENV_BASE_PATH,
    ENV_DEV_PATH,
]:  # in Dockerfile, ENV_DEV_PATH (.env.dev) is not copied to the image
    if path.exists() and path.is_file():
        load_dotenv(path)


def assemble_config(injector: Optional[Injector] = None) -> Injector:
    def make_config() -> Config:
        return Config(
            host=os.getenv("HOST", ""),
            port=os.getenv("PORT", 0),  # type: ignore
            reload=os.getenv("RELOAD", False),  # type: ignore
            db_url=os.getenv("DB_URL", ""),
            alembic_config_path=os.getenv("ALEMBIC_CONFIG_PATH", ""),
            db_migrations_path=os.getenv("MIGRATIONS_PATH", ""),
        )

    injector = injector or Injector()
    injector.binder.bind(Config, to=make_config)

    return injector


def assemble_db(injector: Injector) -> Injector:
    def make_engine() -> Engine:
        config = injector.get(Config)
        return create_engine(url=config.db_url)

    injector.binder.bind(Engine, to=make_engine)

    def make_session() -> Session:
        engine = injector.get(Engine)
        session = Session(bind=engine)

        return session

    injector.binder.bind(Session, to=make_session)

    return injector


def assemble_app(injector: Injector) -> Injector:
    from app.endpoints.health.health import router as health_router
    from app.endpoints.users.users import router as users_router

    config = injector.get(Config)

    @asynccontextmanager  # type: ignore
    async def lifespan(app: FastAPI) -> None:  # type: ignore
        migrate(config=config)
        yield

    def make_app() -> FastAPI:
        users_router.injector = injector  # type: ignore
        health_router.injector = injector  # type: ignore

        app = FastAPI()
        app.include_router(users_router)
        app.include_router(health_router)

        return app

    injector.binder.bind(FastAPI, to=make_app)

    return injector


root_injector = Injector()
assemble_config(root_injector)
assemble_db(root_injector)
assemble_app(root_injector)
