"""Database models and session management."""

from datetime import datetime
from typing import Optional

from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime
from sqlalchemy.orm import declarative_base, sessionmaker, Session

from .config import config

Base = declarative_base()


class Task(Base):
    """Task model representing a coding task in the Karpathy loop."""

    __tablename__ = "tasks"

    id = Column(Integer, primary_key=True, autoincrement=True)
    spec = Column(Text, nullable=False)
    status = Column(String(20), nullable=False, default="pending")
    code = Column(Text, nullable=True)
    test_output = Column(Text, nullable=True)
    error_trace = Column(Text, nullable=True)
    iteration_count = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    def __repr__(self) -> str:
        return f"<Task(id={self.id}, status='{self.status}', spec='{self.spec[:50]}...')>"


# Database engine and session factory
engine = create_engine(config.database_url, pool_pre_ping=True, echo=False)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db() -> Session:
    """Get a database session.

    Yields:
        Database session that automatically closes when done.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """Initialize database schema (create tables if they don't exist)."""
    Base.metadata.create_all(bind=engine)
