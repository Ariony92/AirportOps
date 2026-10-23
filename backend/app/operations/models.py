"""New tables only: compatible with existing V0.3 PostgreSQL volumes."""
from uuid import uuid4
from sqlalchemy import Boolean, CheckConstraint, ForeignKey, Integer, String, UniqueConstraint
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
