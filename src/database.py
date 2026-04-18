import os

from sqlalchemy import create_engine, event
from sqlalchemy.orm import declarative_base, sessionmaker

if os.environ.get("TEST_MODE"):
    worker_id = os.environ.get("PYTEST_XDIST_WORKER", "master")
    db_path = f"./test_{worker_id}.db" if worker_id != "master" else "./test.db"
    DATABASE_URL = f"sqlite:///{db_path}"

    engine = create_engine(
        DATABASE_URL,
        connect_args={"check_same_thread": False, "timeout": 30},
    )
    @event.listens_for(engine, "connect")
    def set_wal_mode(dbapi_connection, connection_record):
        dbapi_connection.execute("PRAGMA journal_mode=WAL")
        dbapi_connection.execute("PRAGMA busy_timeout=30000")
else:  # pragma: no cover
    DATABASE_URL = os.environ.get("DATABASE_URL", "postgresql://admin:password123@localhost:5432/high_assurance")
    engine = create_engine(DATABASE_URL, pool_size=10, max_overflow=20)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
