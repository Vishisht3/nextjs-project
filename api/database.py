from sqlmodel import SQLModel, create_engine, Session
import os

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./biomed_rag.db")

engine = create_engine(DATABASE_URL, echo=True, connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {})

def init_db():
    SQLModel.metadata.create_all(engine)

def get_session():
    with Session(engine) as session:
        yield session