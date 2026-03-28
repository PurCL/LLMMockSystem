from typing import Optional
from sqlmodel import SQLModel, Field

class User(SQLModel, table=True):
    __tablename__ = "users"
    id: Optional[int] = Field(default=None, primary_key=True)
    browser_id: str = Field(index=True, unique=True)
    nickname: str = Field(default="Anonymous")
