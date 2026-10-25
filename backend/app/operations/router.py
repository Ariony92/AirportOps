"""HTTP interface for runways, taxiways, service vehicles, ground tasks and forecast."""
from uuid import uuid4
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from app.db import session
from .models import Runway, Taxiway, GroundVehicle, GroundTask, OperationalIncident, OperationalForecastRun
from .schemas import (
    RunwayIn, RunwayPatch, RunwayOut, TaxiwayIn, TaxiwayPatch, TaxiwayOut,
    VehicleIn, VehiclePatch, VehicleOut, TaskIn, TaskPatch, TaskOut,
    IncidentIn, IncidentOut, SavedForecastIn, SavedForecastOut, Strategy,
)
from .service import forecast

router = APIRouter(prefix='/api/operations', tags=['Airport operations'])


def _create(db: Session, model, payload):
    item = model(id=str(uuid4()), **payload.model_dump())
    db.add(item)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, 'Un élément avec cet identifiant existe déjà')
    db.refresh(item)
    return item


def _patch(db: Session, model, item_id: str, payload):
    item = db.get(model, item_id)
    if item is None:
        raise HTTPException(404, 'Élément introuvable')
    changes = payload.model_dump(exclude_unset=True)
    if not changes or any(value is None for value in changes.values()):
        raise HTTPException(422, 'Au moins un champ valide est requis')
    for field, value in changes.items():
        setattr(item, field, value)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, 'Un élément similaire existe déjà')
    db.refresh(item)
    return item


def _delete(db: Session, model, item_id: str):
    item = db.get(model, item_id)
    if item is None:
        raise HTTPException(404, 'Élément introuvable')
    incident_kind = {Runway: 'runway_closure', Taxiway: 'taxiway_closure',
                     GroundVehicle: 'vehicle_failure'}.get(model)
    if incident_kind is not None and db.scalar(select(OperationalIncident.id).where(
            OperationalIncident.target_id == item_id,
            OperationalIncident.kind == incident_kind)):
        raise HTTPException(409, 'Cette ressource est liée à un incident enregistré')
    db.delete(item)
    db.commit()

@router.get('/runways', response_model=list[RunwayOut])
def runways(db: Session = Depends(session)):
    return db.scalars(select(Runway).order_by(Runway.designation)).all()

@router.post('/runways', response_model=RunwayOut, status_code=201)
def create_runway(payload: RunwayIn, db: Session = Depends(session)):
    return _create(db, Runway, payload)

@router.patch('/runways/{item_id}', response_model=RunwayOut)
def patch_runway(item_id: str, payload: RunwayPatch, db: Session = Depends(session)):
    return _patch(db, Runway, item_id, payload)

@router.delete('/runways/{item_id}', status_code=204)
def remove_runway(item_id: str, db: Session = Depends(session)):
    _delete(db, Runway, item_id)

@router.get('/taxiways', response_model=list[TaxiwayOut])
def taxiways(db: Session = Depends(session)):
    return db.scalars(select(Taxiway).order_by(Taxiway.start_node, Taxiway.end_node)).all()

@router.post('/taxiways', response_model=TaxiwayOut, status_code=201)
def create_taxiway(payload: TaxiwayIn, db: Session = Depends(session)):
    left, right = sorted((payload.start_node, payload.end_node))
    if db.scalar(select(Taxiway.id).where(Taxiway.start_node == left, Taxiway.end_node == right)):
        raise HTTPException(409, 'Cette liaison existe déjà')
    return _create(db, Taxiway, TaxiwayIn(start_node=left, end_node=right, distance_m=payload.distance_m, active=payload.active))

@router.patch('/taxiways/{item_id}', response_model=TaxiwayOut)
def patch_taxiway(item_id: str, payload: TaxiwayPatch, db: Session = Depends(session)):
    return _patch(db, Taxiway, item_id, payload)

@router.delete('/taxiways/{item_id}', status_code=204)
def remove_taxiway(item_id: str, db: Session = Depends(session)):
    _delete(db, Taxiway, item_id)

@router.get('/vehicles', response_model=list[VehicleOut])
def vehicles(db: Session = Depends(session)):
    return db.scalars(select(GroundVehicle).order_by(GroundVehicle.code)).all()

@router.post('/vehicles', response_model=VehicleOut, status_code=201)
def create_vehicle(payload: VehicleIn, db: Session = Depends(session)):
    return _create(db, GroundVehicle, payload)

@router.patch('/vehicles/{item_id}', response_model=VehicleOut)
def patch_vehicle(item_id: str, payload: VehiclePatch, db: Session = Depends(session)):
    return _patch(db, GroundVehicle, item_id, payload)

@router.delete('/vehicles/{item_id}', status_code=204)
def remove_vehicle(item_id: str, db: Session = Depends(session)):
    _delete(db, GroundVehicle, item_id)

@router.get('/tasks', response_model=list[TaskOut])
def tasks(flight_plan_id: str | None = None, db: Session = Depends(session)):
    stmt = select(GroundTask).order_by(GroundTask.flight_plan_id, GroundTask.kind)
    if flight_plan_id:
        stmt = stmt.where(GroundTask.flight_plan_id == flight_plan_id)
    return db.scalars(stmt).all()

@router.post('/tasks', response_model=TaskOut, status_code=201)
def create_task(payload: TaskIn, db: Session = Depends(session)):
    # Import only inside endpoint to avoid cyclic main/router dependency.
    from app.main import PlannedFlight
    if db.get(PlannedFlight, payload.flight_plan_id) is None:
        raise HTTPException(404, 'Vol introuvable')
    return _create(db, GroundTask, payload)

@router.patch('/tasks/{item_id}', response_model=TaskOut)
def patch_task(item_id: str, payload: TaskPatch, db: Session = Depends(session)):
    return _patch(db, GroundTask, item_id, payload)

@router.delete('/tasks/{item_id}', status_code=204)
def remove_task(item_id: str, db: Session = Depends(session)):
    _delete(db, GroundTask, item_id)

@router.get('/forecast')
def get_forecast(include_demo_flights: bool = True, strategy: Strategy = 'optimized',
                 use_incidents: bool = True, db: Session = Depends(session)):
    from app.main import PlannedFlight, Aircraft
    plans = db.scalars(select(PlannedFlight).order_by(PlannedFlight.scheduled_minute, PlannedFlight.flight_number)).all()
    if not plans and include_demo_flights:
        from types import SimpleNamespace
        plans = [SimpleNamespace(id=f'demo-{i}', flight_number=f'AO{1000+i}',
                  scheduled_minute=10+i*12, duration_minutes=18, aircraft_id=None)
                 for i in range(10)]
    assigned_ids = {p.aircraft_id for p in plans if p.aircraft_id}
    fleet = {a.id: a for a in db.scalars(select(Aircraft).where(Aircraft.id.in_(assigned_ids))).all()} if assigned_ids else {}
    return forecast(plans, fleet,
                    db.scalars(select(Runway)).all(),
                    db.scalars(select(Taxiway)).all(),
                    db.scalars(select(GroundVehicle)).all(),
                    db.scalars(select(GroundTask)).all(),
                    incidents=db.scalars(select(OperationalIncident).where(OperationalIncident.enabled == True)).all() if use_incidents else [],
                    strategy=strategy)


def _check_incident_target(payload: IncidentIn, db: Session) -> None:
    from app.main import PlannedFlight
    targets = {
        'runway_closure': Runway,
        'taxiway_closure': Taxiway,
        'vehicle_failure': GroundVehicle,
        'flight_delay': PlannedFlight,
    }
    if db.get(targets[payload.kind], payload.target_id) is None:
        raise HTTPException(404, 'Ressource cible introuvable')


@router.get('/incidents', response_model=list[IncidentOut])
def list_incidents(db: Session = Depends(session)):
    return db.scalars(select(OperationalIncident).order_by(OperationalIncident.start_minute)).all()


@router.post('/incidents', response_model=IncidentOut, status_code=201)
def add_incident(payload: IncidentIn, db: Session = Depends(session)):
    _check_incident_target(payload, db)
    return _create(db, OperationalIncident, payload)


@router.delete('/incidents/{item_id}', status_code=204)
def delete_incident(item_id: str, db: Session = Depends(session)):
    _delete(db, OperationalIncident, item_id)


@router.patch('/incidents/{item_id}', response_model=IncidentOut)
def update_incident(item_id: str, payload: IncidentIn, db: Session = Depends(session)):
    if db.get(OperationalIncident, item_id) is None:
        raise HTTPException(404, 'Incident introuvable')
    _check_incident_target(payload, db)
    return _patch(db, OperationalIncident, item_id, payload)


@router.get('/analytics/compare')
def compare_forecasts(db: Session = Depends(session)):
    baseline = get_forecast(strategy='baseline', use_incidents=True, db=db)
    optimized = get_forecast(strategy='optimized', use_incidents=True, db=db)
    no_incidents = get_forecast(strategy='optimized', use_incidents=False, db=db)
    metrics = ['completed', 'blocked', 'total_delay_min', 'estimated_vehicle_cost',
               'vehicle_distance_m', 'taxi_distance_m', 'runway_conflicts_avoided',
               'taxi_conflicts_avoided', 'incident_delay_min']
    return {'baseline': baseline, 'optimized': optimized, 'without_incidents': no_incidents,
            'delta': {k: round(optimized['kpis'][k] - baseline['kpis'][k], 2) for k in metrics},
            'description': 'Prévisions recalculées depuis les mêmes données ; aucune modification en base.'}


@router.get('/analytics/history', response_model=list[SavedForecastOut])
def forecast_history(limit: int = 20, db: Session = Depends(session)):
    if limit < 1 or limit > 100:
        raise HTTPException(422, 'Limite comprise entre 1 et 100')
    return db.scalars(select(OperationalForecastRun).order_by(
        OperationalForecastRun.created_at.desc(), OperationalForecastRun.id.desc()).limit(limit)).all()


@router.post('/analytics/history', response_model=SavedForecastOut, status_code=201)
def save_forecast(payload: SavedForecastIn, db: Session = Depends(session)):
    result = get_forecast(strategy=payload.strategy, use_incidents=True, db=db)
    count = db.scalar(select(func.count()).select_from(OperationalIncident).where(OperationalIncident.enabled == True)) or 0
    record = OperationalForecastRun(label=payload.label, strategy=payload.strategy,
                                    incident_count=count, result=result)
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


@router.delete('/analytics/history/{item_id}', status_code=204)
def delete_forecast(item_id: str, db: Session = Depends(session)):
    _delete(db, OperationalForecastRun, item_id)


def initialize_demo_infrastructure(db: Session):
    """Seed only an entirely empty category; never overwrite an existing item."""
    if not db.scalar(select(func.count()).select_from(Runway)):
        db.add(Runway(designation='09/27', length_m=3400, separation_min=3, active=True))
    if not db.scalar(select(func.count()).select_from(Taxiway)):
        connections = [(0,1,600), (1,2,125), (1,3,200), (1,4,270), (1,5,350), (1,6,460)]
        for a, b, metres in connections:
            db.add(Taxiway(start_node=a, end_node=b, distance_m=metres))
    if not db.scalar(select(func.count()).select_from(GroundVehicle)):
        vehicle_templates = [
            ('BAG-01', 'baggage', 35, 30, 45),
            ('BAG-02', 'baggage', 32, 25, 40),
            ('FUEL-01', 'fuel', 28, 20, 85),
            ('CLEAN-01', 'cleaning', 30, 20, 35),
            ('CAT-01', 'catering', 28, 25, 55),
            ('TUG-01', 'tug', 22, 10, 90),
        ]
        for code, kind, speed, cap, cost in vehicle_templates:
            db.add(GroundVehicle(code=code, kind=kind, speed_kmh=speed,
                                 capacity_units=cap, cost_per_hour=cost, fuel_pct=100,
                                 available=True, maintenance=False, home_node=1))
    db.commit()
