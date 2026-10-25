"""Airport aircraft assignment rules, independent of HTTP presentation."""
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.models import Aircraft, PlannedFlight, FlightAircraftAssignment

class AircraftNotFound(Exception):
    pass

class AircraftOverlap(Exception):
    pass

def validate_assignment(db: Session, aircraft_id: str | None, flight_id: str, scheduled_minute: int, duration_minutes: int) -> None:
    if aircraft_id is None:
        return
    if db.get(Aircraft, aircraft_id) is None:
        raise AircraftNotFound()
    assignments = db.execute(select(FlightAircraftAssignment, PlannedFlight).join(PlannedFlight, PlannedFlight.id == FlightAircraftAssignment.flight_plan_id).where(FlightAircraftAssignment.aircraft_id == aircraft_id, FlightAircraftAssignment.flight_plan_id != flight_id)).all()
    end = scheduled_minute + duration_minutes
    if any(scheduled_minute < other.scheduled_minute + other.duration_minutes and other.scheduled_minute < end for _, other in assignments):
        raise AircraftOverlap()
