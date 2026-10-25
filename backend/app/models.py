"""Core persistent airport entities (SQLAlchemy models)."""
from __future__ import annotations
from datetime import datetime, timezone
from sqlalchemy import String, Integer, ForeignKey, DateTime, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db import Base

class Scenario(Base):
    __tablename__ = 'scenarios'
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    description: Mapped[str] = mapped_column(String(2000), default='')
    delay: Mapped[int] = mapped_column(Integer, default=30)
    breakdown: Mapped[bool] = mapped_column(default=False)
    seed: Mapped[int] = mapped_column(Integer, default=42)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    runs: Mapped[list['Run']] = relationship(back_populates='scenario', cascade='all, delete-orphan')

class PlannedFlight(Base):
    """User-managed timetable entries for the educational ten-flight engine."""
    __tablename__ = 'flight_plans'
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    flight_number: Mapped[str] = mapped_column(String(12), unique=True, nullable=False)
    airline: Mapped[str] = mapped_column(String(80), nullable=False)
    origin: Mapped[str] = mapped_column(String(3), nullable=False)
    destination: Mapped[str] = mapped_column(String(3), nullable=False)
    scheduled_minute: Mapped[int] = mapped_column(Integer, nullable=False)
    duration_minutes: Mapped[int] = mapped_column(Integer, nullable=False)
    assignment: Mapped['FlightAircraftAssignment | None'] = relationship(back_populates='flight', uselist=False, cascade='all, delete-orphan')

    @property
    def aircraft_id(self) -> str | None:
        return self.assignment.aircraft_id if self.assignment else None

class Aircraft(Base):
    """Educational fleet inventory. No real airworthiness or ATC validation."""
    __tablename__ = 'aircraft'
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    registration: Mapped[str] = mapped_column(String(12), unique=True, nullable=False)
    airline: Mapped[str] = mapped_column(String(80), nullable=False)
    manufacturer: Mapped[str] = mapped_column(String(80), nullable=False)
    model: Mapped[str] = mapped_column(String(80), nullable=False)
    category: Mapped[str] = mapped_column(String(20), nullable=False)
    seats: Mapped[int] = mapped_column(Integer, nullable=False)

class FlightAircraftAssignment(Base):
    """Separate association avoids altering the existing flight_plans table in V0.3."""
    __tablename__ = 'flight_aircraft_assignments'
    flight_plan_id: Mapped[str] = mapped_column(ForeignKey('flight_plans.id', ondelete='CASCADE'), primary_key=True)
    aircraft_id: Mapped[str] = mapped_column(ForeignKey('aircraft.id'), index=True, nullable=False)
    flight: Mapped[PlannedFlight] = relationship(back_populates='assignment')

class Run(Base):
    __tablename__ = 'runs'
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    scenario_id: Mapped[str] = mapped_column(ForeignKey('scenarios.id'), index=True)
    strategy: Mapped[str] = mapped_column(String(20))
    result: Mapped[dict] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    scenario: Mapped[Scenario] = relationship(back_populates='runs')

class Airport(Base):
    __tablename__ = 'airports'
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    code: Mapped[str] = mapped_column(String(8), unique=True)
    layout: Mapped[dict] = mapped_column(JSON, default=dict)

class Audit(Base):
    __tablename__ = 'audit_events'
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    action: Mapped[str] = mapped_column(String(50))
    subject_id: Mapped[str] = mapped_column(String(36))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
