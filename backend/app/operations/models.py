"""New tables only: compatible with existing V0.3 PostgreSQL volumes."""
from uuid import uuid4
from datetime import datetime, timezone
from sqlalchemy import Boolean, CheckConstraint, DateTime, ForeignKey, Integer, String, UniqueConstraint, JSON
from sqlalchemy.orm import Mapped, mapped_column
from app.db import Base

class Runway(Base):
    __tablename__ = 'operational_runways'
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    designation: Mapped[str] = mapped_column(String(16), unique=True, nullable=False)
    length_m: Mapped[int] = mapped_column(Integer, nullable=False)
    separation_min: Mapped[int] = mapped_column(Integer, nullable=False, default=3)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    __table_args__ = (CheckConstraint('length_m BETWEEN 400 AND 6000'),)

class Taxiway(Base):
    __tablename__ = 'operational_taxiways'
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    start_node: Mapped[int] = mapped_column(Integer, nullable=False)
    end_node: Mapped[int] = mapped_column(Integer, nullable=False)
    distance_m: Mapped[int] = mapped_column(Integer, nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    __table_args__ = (
        UniqueConstraint('start_node', 'end_node', name='uq_taxiway_segment'),
        CheckConstraint('start_node <> end_node'),
        CheckConstraint('distance_m > 0'),
    )

class GroundVehicle(Base):
    __tablename__ = 'operational_vehicles'
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    code: Mapped[str] = mapped_column(String(24), nullable=False, unique=True)
    kind: Mapped[str] = mapped_column(String(24), nullable=False)
    speed_kmh: Mapped[int] = mapped_column(Integer, nullable=False)
    capacity_units: Mapped[int] = mapped_column(Integer, nullable=False)
    fuel_pct: Mapped[int] = mapped_column(Integer, nullable=False, default=100)
    available: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    maintenance: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    home_node: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    cost_per_hour: Mapped[int] = mapped_column(Integer, nullable=False, default=30)

class GroundTask(Base):
    __tablename__ = 'operational_tasks'
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    flight_plan_id: Mapped[str] = mapped_column(ForeignKey('flight_plans.id', ondelete='CASCADE'), nullable=False, index=True)
    kind: Mapped[str] = mapped_column(String(24), nullable=False)
    duration_min: Mapped[int] = mapped_column(Integer, nullable=False)
    units: Mapped[int] = mapped_column(Integer, nullable=False, default=1)


class OperationalIncident(Base):
    """Persisted timed disruption; forecast consumes an immutable snapshot."""
    __tablename__ = 'operational_incidents'
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    kind: Mapped[str] = mapped_column(String(32), nullable=False)
    target_id: Mapped[str] = mapped_column(String(36), nullable=False)
    start_minute: Mapped[int] = mapped_column(Integer, nullable=False)
    end_minute: Mapped[int] = mapped_column(Integer, nullable=False)
    delay_minutes: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    description: Mapped[str] = mapped_column(String(240), nullable=False, default='')
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    __table_args__ = (
        CheckConstraint('start_minute >= 0 AND start_minute <= 1440'),
        CheckConstraint('end_minute > start_minute AND end_minute <= 1440'),
        CheckConstraint('delay_minutes >= 0 AND delay_minutes <= 180'),
    )


class OperationalForecastRun(Base):
    """Stored KPI/report snapshot; no change to the source timetable or fleet."""
    __tablename__ = 'operational_forecast_runs'
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    label: Mapped[str] = mapped_column(String(100), nullable=False)
    strategy: Mapped[str] = mapped_column(String(16), nullable=False)
    incident_count: Mapped[int] = mapped_column(Integer, nullable=False)
    result: Mapped[dict] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
