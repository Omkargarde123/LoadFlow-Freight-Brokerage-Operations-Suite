"""
SQLite chosen per assessment: zero-setup, file-based, fine for a hackathon-scale
demo. SQLAlchemy ORM gives us real relational integrity (FKs, cascades) instead
of hand-rolled JSON blobs, which matters for an audit-trail-heavy domain like
this one.
"""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

DATABASE_URL = "sqlite:///./loadflow.db"

engine = create_engine(
    DATABASE_URL, connect_args={"check_same_thread": False}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
