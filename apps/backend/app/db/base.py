from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


# Imported by Alembic so model metadata is registered.
from app import models  # noqa: E402,F401
