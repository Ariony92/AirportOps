"""Read-only collection of inputs needed by the operational planning service."""
from __future__ import annotations

from types import SimpleNamespace
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.models import PlannedFlight, Aircraft
from .models import Runway, Taxiway, GroundVehicle, GroundTask, OperationalIncident


def load_forecast_inputs(db: Session, *, include_demo_flights: bool = True,
                         use_incidents: bool = True) -> dict:
    """Load a consistent set of ORM objects; never mutate the persisted inputs."""
    plans = db.scalars(select(PlannedFlight).order_by(
        PlannedFlight.scheduled_minute, PlannedFlight.flight_number)).all()
    if not plans and include_demo_flights:
        plans = [SimpleNamespace(id=f'demo-{i}', flight_number=f'AO{1000+i}',
                                 scheduled_minute=10+i*12, duration_minutes=18,
                                 aircraft_id=None) for i in range(10)]
    assigned_ids = {p.aircraft_id for p in plans if p.aircraft_id}
    fleet = {a.id: a for a in db.scalars(select(Aircraft).where(
        Aircraft.id.in_(assigned_ids))).all()} if assigned_ids else {}
    return {
        'flights': plans,
        'aircraft': fleet,
        'runways': db.scalars(select(Runway)).all(),
        'taxiways': db.scalars(select(Taxiway)).all(),
        'vehicles': db.scalars(select(GroundVehicle)).all(),
        'tasks': db.scalars(select(GroundTask)).all(),
        'incidents': db.scalars(select(OperationalIncident).where(
            OperationalIncident.enabled.is_(True))).all() if use_incidents else [],
    }
