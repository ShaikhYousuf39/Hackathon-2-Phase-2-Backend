from sqlmodel import SQLModel, Field
from datetime import datetime
from typing import Optional


class AuthUser(SQLModel, table=True):
    """Shadow Better Auth user table so SQLModel can resolve FK."""
    __tablename__ = "user"

    id: str = Field(primary_key=True)


class Task(SQLModel, table=True):
    """Task model for todo items"""
    __tablename__ = "tasks"

    id: Optional[int] = Field(default=None, primary_key=True)
    # Better Auth uses "user" table; keep FK aligned with auth DB.
    user_id: str = Field(foreign_key="user.id", index=True)
    title: str = Field(max_length=200)
    description: Optional[str] = None
    completed: bool = Field(default=False)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
