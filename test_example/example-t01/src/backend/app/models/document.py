from typing import Optional, List
from datetime import datetime, timezone
from sqlmodel import SQLModel, Field, Relationship

class DocumentBase(SQLModel):
    name: str = Field(index=True)
    size: int
    content_type: str
    path: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    owner_id: int = Field(default=1) # Mock User ID
    last_modified_by: Optional[str] = Field(default="Anonymous")
    extracted_text: Optional[str] = Field(default=None)

class Document(DocumentBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)

class DocumentRead(DocumentBase):
    id: int
    versions: List[dict] = []

# Pagination response model removed
