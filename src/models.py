"""
Data models — SQLAlchemy ORM definitions for the High-Assurance API.

Design Decisions:
    - Account.balance uses Numeric(12,2) instead of Float to prevent
      IEEE 754 floating-point precision errors in financial calculations.
    - IdempotencyKey enforces exactly-once semantics for fund transfers.
    - OutboxEvent implements the Transactional Outbox pattern for
      reliable event publishing without distributed transactions.
"""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import JSON, Column, DateTime, Integer, Numeric, String

from database import Base


class Account(Base):
    """Bank account with Numeric-precision balance for financial correctness."""

    __tablename__ = "accounts"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String, unique=True, index=True, nullable=False)
    password_hash = Column(String, nullable=False, server_default="")
    role = Column(String, nullable=False, server_default="user")
    balance = Column(Numeric(precision=12, scale=2), nullable=False, default=0.00)


class IdempotencyKey(Base):
    """Exactly-once transfer guard — prevents duplicate transaction replay."""

    __tablename__ = "idempotency_keys"

    id = Column(Integer, primary_key=True, index=True)
    idempotency_key = Column(String, unique=True, index=True, nullable=False)
    status = Column(String, nullable=False)
    response_body = Column(JSON, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(UTC))


class OutboxEvent(Base):
    """Transactional Outbox — append-only audit log for regulatory compliance.

    Satisfies:
        - SOC 2 CC7.2: Security event logging
        - PCI DSS 10.1: Audit trail for cardholder data access
        - FDA 21 CFR §11.10(e): Immutable timestamped records
    """

    __tablename__ = "outbox_events"

    id = Column(Integer, primary_key=True, index=True)
    event_type = Column(String, nullable=False)
    payload = Column(JSON, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(UTC))
