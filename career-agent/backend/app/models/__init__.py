"""Import all models here so Alembic's autogenerate can discover them
via Base.metadata. Every new model module must be imported below."""

from app.models.user import User

__all__ = ["User"]
