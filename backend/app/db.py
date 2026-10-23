"""Shared SQLAlchemy configuration for the existing API and operational modules."""
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session

DATABASE_URL = os.getenv('DATABASE_URL', 'sqlite:///./airportops.db')
engine = create_engine(
    DATABASE_URL,
    connect_args={'check_same_thread': False} if DATABASE_URL.startswith('sqlite') else {},
    pool_pre_ping=True,
)

class Base(DeclarativeBase):
    pass

def session():
    with Session(engine) as db:
        yield db
