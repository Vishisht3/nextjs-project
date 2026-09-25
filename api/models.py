from sqlmodel import SQLModel, Field
from typing import Optional
from datetime import datetime

class ResearchDocument(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    title: str = Field(index=True)
    content: str
    is_processed: bool = Field(default=False) 
    uploaded_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())