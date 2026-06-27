"""
Self-Healing Models

SQLAlchemy models for self-healing selectors, healing sessions and healing
results. These power the Self-Healing dashboard: flaky UI selectors are
tracked, healed on demand and every healing operation is recorded.

Registered on the shared ``models.Base`` metadata so Alembic autogenerate and
``init_db()`` (create_all) both pick them up. See
``docs/superpowers/specs/2026-06-27-self-healing-backend-design.md``.
"""

from sqlalchemy import (
    Column,
    Integer,
    String,
    Float,
    Boolean,
    Text,
    DateTime,
    ForeignKey,
)
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

from models import Base


class HealingSelector(Base):
    """A UI selector tracked by the self-healing system."""

    __tablename__ = "self_healing_selectors"

    id = Column(Integer, primary_key=True, index=True)
    value = Column(String, nullable=False, index=True)
    selector_type = Column(String, default="css")  # css, xpath, id, data_attribute
    description = Column(Text, nullable=True)
    confidence_score = Column(Float, default=0.5)  # 0.0 - 1.0
    confidence_level = Column(String, default="medium")  # high, medium, low
    is_active = Column(Boolean, default=True)
    usage_count = Column(Integer, default=0)
    success_rate = Column(Float, default=0.0)  # 0.0 - 1.0
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    results = relationship("HealingResult", back_populates="selector")


class HealingSession(Base):
    """A healing session aggregating one or more healing operations."""

    __tablename__ = "self_healing_sessions"

    id = Column(Integer, primary_key=True, index=True)
    status = Column(String, default="running")  # running, success, partial, failed
    total_selectors = Column(Integer, default=0)
    successful_heals = Column(Integer, default=0)
    failed_heals = Column(Integer, default=0)
    success_rate = Column(Float, default=0.0)  # 0.0 - 1.0
    average_confidence = Column(Float, default=0.0)  # 0.0 - 1.0
    started_at = Column(DateTime, default=func.now())
    completed_at = Column(DateTime, nullable=True)

    results = relationship("HealingResult", back_populates="session")


class HealingResult(Base):
    """The outcome of a single healing operation on a selector."""

    __tablename__ = "self_healing_results"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("self_healing_sessions.id"), nullable=True)
    selector_id = Column(Integer, ForeignKey("self_healing_selectors.id"), nullable=True)
    original_selector_value = Column(String, nullable=False)
    healed_selector_value = Column(String, nullable=True)
    status = Column(String, default="success")  # success, failed, skipped
    confidence_score = Column(Float, default=0.0)  # 0.0 - 1.0
    confidence_level = Column(String, default="low")  # high, medium, low
    healing_time_ms = Column(Integer, default=0)
    attempts = Column(Integer, default=1)
    created_at = Column(DateTime, default=func.now())

    session = relationship("HealingSession", back_populates="results")
    selector = relationship("HealingSelector", back_populates="results")
