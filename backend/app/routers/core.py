"""HTTP adapters: validation/serialization and orchestration only."""
from uuid import uuid4
from sqlalchemy.orm import Session
from sqlalchemy import select, func, delete
from sqlalchemy.exc import IntegrityError
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Literal
from app.db import session
from app.models import Scenario, Run, PlannedFlight, Aircraft, FlightAircraftAssignment, Airport, Audit
from app.schemas import ScenarioIn, ScenarioOut, RunOut, AirportIn, AirportOut, FlightPlanIn, FlightPlanPatch, FlightPlanOut, AircraftIn, AircraftPatch, AircraftOut, CompareIn
from app.services.aircraft import validate_assignment, AircraftNotFound, AircraftOverlap
from app.operations.models import GroundTask, OperationalIncident
router = APIRouter(tags=['Core API'])

def audit(db: Session, action: str, id: str):
    db.add(Audit(id=str(uuid4()), action=action, subject_id=id))

@router.get('/health')
def health():
    return {'status': 'ok'}

def check_aircraft_assignment(db: Session, aircraft_id: str | None, flight_id: str, scheduled_minute: int, duration_minutes: int) -> None:
    try:
        validate_assignment(db, aircraft_id, flight_id, scheduled_minute, duration_minutes)
    except AircraftNotFound:
        raise HTTPException(404, 'Aircraft not found')
    except AircraftOverlap:
        raise HTTPException(409, 'Aircraft is assigned to an overlapping flight')

@router.get('/api/aircraft', response_model=list[AircraftOut])
def list_aircraft(db: Session=Depends(session)):
    return db.scalars(select(Aircraft).order_by(Aircraft.registration)).all()

@router.get('/api/aircraft/{id}', response_model=AircraftOut)
def get_aircraft(id: str, db: Session=Depends(session)):
    item = db.get(Aircraft, id)
    if item is None:
        raise HTTPException(404, 'Aircraft not found')
    return item

@router.post('/api/aircraft', response_model=AircraftOut, status_code=201)
def add_aircraft(payload: AircraftIn, db: Session=Depends(session)):
    item = Aircraft(id=str(uuid4()), **payload.model_dump())
    db.add(item)
    try:
        db.flush()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, 'Registration already exists')
    audit(db, 'aircraft.created', item.id)
    db.commit()
    db.refresh(item)
    return item

@router.patch('/api/aircraft/{id}', response_model=AircraftOut)
def update_aircraft(id: str, payload: AircraftPatch, db: Session=Depends(session)):
    item = db.get(Aircraft, id)
    if item is None:
        raise HTTPException(404, 'Aircraft not found')
    changes = payload.model_dump(exclude_unset=True)
    if not changes or any((value is None for value in changes.values())):
        raise HTTPException(422, 'Provide at least one non-null field')
    for key, value in changes.items():
        setattr(item, key, value)
    try:
        db.flush()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, 'Registration already exists')
    audit(db, 'aircraft.updated', id)
    db.commit()
    db.refresh(item)
    return item

@router.delete('/api/aircraft/{id}', status_code=204)
def delete_aircraft(id: str, db: Session=Depends(session)):
    item = db.get(Aircraft, id)
    if item is None:
        raise HTTPException(404, 'Aircraft not found')
    if db.scalar(select(FlightAircraftAssignment.flight_plan_id).where(FlightAircraftAssignment.aircraft_id == id).limit(1)):
        raise HTTPException(409, 'Aircraft is assigned to a flight; unassign it first')
    db.delete(item)
    audit(db, 'aircraft.deleted', id)
    db.commit()

@router.get('/api/flight-plans', response_model=list[FlightPlanOut])
def list_flight_plans(db: Session=Depends(session)):
    return db.scalars(select(PlannedFlight).order_by(PlannedFlight.scheduled_minute, PlannedFlight.flight_number)).all()

@router.post('/api/flight-plans', response_model=FlightPlanOut, status_code=201)
def add_flight_plan(payload: FlightPlanIn, db: Session=Depends(session)):
    if (db.scalar(select(func.count()).select_from(PlannedFlight)) or 0) >= 10:
        raise HTTPException(409, 'Maximum 10 flights supported in V0.2')
    data = payload.model_dump(exclude={'aircraft_id'})
    item = PlannedFlight(id=str(uuid4()), **data)
    check_aircraft_assignment(db, payload.aircraft_id, item.id, item.scheduled_minute, item.duration_minutes)
    if payload.aircraft_id is not None:
        item.assignment = FlightAircraftAssignment(aircraft_id=payload.aircraft_id)
    db.add(item)
    try:
        db.flush()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, 'Flight number already exists')
    audit(db, 'flight_plan.created', item.id)
    db.commit()
    db.refresh(item)
    return item

@router.patch('/api/flight-plans/{id}', response_model=FlightPlanOut)
def update_flight_plan(id: str, payload: FlightPlanPatch, db: Session=Depends(session)):
    item = db.get(PlannedFlight, id)
    if not item:
        raise HTTPException(404, 'Flight not found')
    changes = payload.model_dump(exclude_unset=True)
    if not changes or any((value is None for key, value in changes.items() if key != 'aircraft_id')):
        raise HTTPException(422, 'Provide at least one valid field')
    new_aircraft_id = changes.pop('aircraft_id', item.aircraft_id)
    new_scheduled = changes.get('scheduled_minute', item.scheduled_minute)
    new_duration = changes.get('duration_minutes', item.duration_minutes)
    check_aircraft_assignment(db, new_aircraft_id, id, new_scheduled, new_duration)
    for key, value in changes.items():
        setattr(item, key, value)
    if new_aircraft_id is None:
        item.assignment = None
    elif item.assignment is None:
        item.assignment = FlightAircraftAssignment(aircraft_id=new_aircraft_id)
    else:
        item.assignment.aircraft_id = new_aircraft_id
    try:
        db.flush()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, 'Flight number already exists')
    audit(db, 'flight_plan.updated', id)
    db.commit()
    db.refresh(item)
    return item

@router.delete('/api/flight-plans/{id}', status_code=204)
def delete_flight_plan(id: str, db: Session=Depends(session)):
    item = db.get(PlannedFlight, id)
    if not item:
        raise HTTPException(404, 'Flight not found')
    if db.scalar(select(OperationalIncident.id).where(OperationalIncident.kind == 'flight_delay', OperationalIncident.target_id == id)):
        raise HTTPException(409, 'Ce vol est lié à un incident enregistré')
    db.execute(delete(GroundTask).where(GroundTask.flight_plan_id == id))
    db.delete(item)
    audit(db, 'flight_plan.deleted', id)
    db.commit()

@router.get('/api/airports', response_model=list[AirportOut])
def airports(db: Session=Depends(session)):
    return db.scalars(select(Airport)).all()

@router.post('/api/airports', response_model=AirportOut, status_code=201)
def add_airport(payload: AirportIn, db: Session=Depends(session)):
    if db.scalar(select(Airport).where(Airport.code == payload.code)):
        raise HTTPException(409, 'Airport code already exists')
    item = Airport(id=str(uuid4()), **payload.model_dump())
    db.add(item)
    audit(db, 'airport.created', item.id)
    db.commit()
    db.refresh(item)
    return item

@router.get('/api/scenarios', response_model=list[ScenarioOut])
def list_scenarios(db: Session=Depends(session)):
    return db.scalars(select(Scenario).order_by(Scenario.created_at.desc())).all()

@router.post('/api/scenarios', response_model=ScenarioOut, status_code=201)
def add_scenario(payload: ScenarioIn, db: Session=Depends(session)):
    item = Scenario(id=str(uuid4()), **payload.model_dump())
    db.add(item)
    audit(db, 'scenario.created', item.id)
    db.commit()
    db.refresh(item)
    return item

@router.get('/api/scenarios/{id}', response_model=ScenarioOut)
def get_scenario(id: str, db: Session=Depends(session)):
    item = db.get(Scenario, id)
    if not item:
        raise HTTPException(404, 'Scenario not found')
    return item

@router.patch('/api/scenarios/{id}', response_model=ScenarioOut)
def patch_scenario(id: str, payload: ScenarioIn, db: Session=Depends(session)):
    item = db.get(Scenario, id)
    if not item:
        raise HTTPException(404, 'Scenario not found')
    for key, value in payload.model_dump().items():
        setattr(item, key, value)
    audit(db, 'scenario.updated', id)
    db.commit()
    db.refresh(item)
    return item

@router.post('/api/scenarios/{id}/duplicate', response_model=ScenarioOut, status_code=201)
def duplicate_scenario(id: str, db: Session=Depends(session)):
    item = db.get(Scenario, id)
    if not item:
        raise HTTPException(404, 'Scenario not found')
    new = Scenario(id=str(uuid4()), name=item.name + ' (copie)', description=item.description, delay=item.delay, breakdown=item.breakdown, seed=item.seed)
    db.add(new)
    audit(db, 'scenario.duplicated', new.id)
    db.commit()
    db.refresh(new)
    return new

@router.delete('/api/scenarios/{id}', status_code=204)
def delete_scenario(id: str, db: Session=Depends(session)):
    item = db.get(Scenario, id)
    if not item:
        raise HTTPException(404, 'Scenario not found')
    db.delete(item)
    audit(db, 'scenario.deleted', id)
    db.commit()

@router.get('/api/scenarios/{id}/runs', response_model=list[RunOut])
def list_runs(id: str, db: Session=Depends(session)):
    if not db.get(Scenario, id):
        raise HTTPException(404, 'Scenario not found')
    return db.scalars(select(Run).where(Run.scenario_id == id).order_by(Run.created_at.desc())).all()

@router.get('/api/runs/{id}', response_model=RunOut)
def get_run(id: str, db: Session=Depends(session)):
    item = db.get(Run, id)
    if not item:
        raise HTTPException(404, 'Run not found')
    return item

@router.post('/api/comparisons')
def compare_runs(payload: CompareIn, db: Session=Depends(session)):
    first = db.get(Run, payload.baseline_run_id)
    second = db.get(Run, payload.optimized_run_id)
    if not first or not second:
        raise HTTPException(404, 'Run not found')
    if first.scenario_id != second.scenario_id:
        raise HTTPException(400, 'Runs must belong to the same scenario')
    from app.services.analytics import compare_stored_scenario_runs
    try:
        delta, source_note = compare_stored_scenario_runs(first.result, second.result)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
    return {'scenario_id': first.scenario_id, 'baseline': first.result,
            'optimized': second.result, 'delta': delta, 'note': source_note}

@router.get('/api/audit')
def audit_log(limit: int=20, db: Session=Depends(session)):
    if limit < 1 or limit > 100:
        raise HTTPException(422, 'limit must be 1..100')
    items = db.scalars(select(Audit).order_by(Audit.created_at.desc()).limit(limit)).all()
    return [{'action': x.action, 'subject_id': x.subject_id, 'created_at': x.created_at} for x in items]

class ServerRunRequest(BaseModel):
    strategy: Literal['baseline', 'optimized'] = 'optimized'

@router.post('/api/scenarios/{id}/generate', response_model=RunOut, status_code=201)
def generate_server_run(id: str, payload: ServerRunRequest, db: Session=Depends(session)):
    """Persist a server-authoritative operational result rather than client claims."""
    scenario = db.get(Scenario, id)
    if scenario is None:
        raise HTTPException(404, 'Scenario not found')
    from app.services.scenarios import generate_scenario_forecast
    data = generate_scenario_forecast(db, scenario, payload.strategy)
    record = Run(id=str(uuid4()), scenario_id=id, strategy=payload.strategy, result=data)
    db.add(record)
    audit(db, 'run.generated', record.id)
    db.commit()
    db.refresh(record)
    return record
