from datetime import datetime, timezone
from typing import List, Optional

from pgvector.sqlalchemy import Vector
from pydantic import ConfigDict
from sqlmodel import Column, Field, SQLModel


class ResearchDocument(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    title: str = Field(index=True)
    content: str
    is_processed: bool = Field(default=False)
    uploaded_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class DocumentChunk(SQLModel, table=True):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    id: Optional[int] = Field(default=None, primary_key=True)
    document_id: int = Field(foreign_key="researchdocument.id")
    chunk_text: str
    embedding: List[float] = Field(sa_column=Column(Vector(384)))
