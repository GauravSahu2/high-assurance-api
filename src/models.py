from database import Base
from sqlalchemy import JSON, Column, DateTime, Float, Integer, String
from sqlalchemy.sql import func


class Account(Base):
    __tablename__ = "accounts"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String, unique=True, index=True, nullable=False)
    balance = Column(Float, nullable=False, default=0.0)


class IdempotencyKey(Base):
    __tablename__ = "idempotency_keys"
    id = Column(Integer, primary_key=True, index=True)
    idempotency_key = Column(String, unique=True, index=True, nullable=False)
    status = Column(String, nullable=False, default="processing")
    response_body = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class OutboxEvent(Base):
    __tablename__ = "outbox_events"
    id = Column(Integer, primary_key=True, index=True)
    event_type = Column(String, nullable=False)
    payload = Column(JSON, nullable=False)
    status = Column(String, nullable=False, default="pending")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
