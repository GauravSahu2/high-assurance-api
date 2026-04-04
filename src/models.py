from sqlalchemy import Column, Integer, String, Float, JSON, DateTime
from database import Base
from datetime import datetime, UTC

class Account(Base):
    __tablename__ = "accounts"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String, unique=True, index=True, nullable=False)
    password_hash = Column(String, nullable=False, server_default="")
    role = Column(String, nullable=False, server_default="user")
    balance = Column(Float, nullable=False, default=0.0)

class IdempotencyKey(Base):
    __tablename__ = "idempotency_keys"
    id = Column(Integer, primary_key=True, index=True)
    idempotency_key = Column(String, unique=True, index=True, nullable=False)
    status = Column(String, nullable=False)
    response_body = Column(JSON, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(UTC))

class OutboxEvent(Base):
    __tablename__ = "outbox_events"
    id = Column(Integer, primary_key=True, index=True)
    event_type = Column(String, nullable=False)
    payload = Column(JSON, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(UTC))
