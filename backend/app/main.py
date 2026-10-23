"""AirportOps persistence API. Flight positions are computed client-side by the C++ engine."""
import os
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from uuid import uuid4
from typing import Literal
from sqlalchemy.exc import IntegrityError
from sqlalchemy import func
from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from sqlalchemy import String, Integer, ForeignKey, DateTime, JSON, select, delete
from sqlalchemy.orm import Mapped, mapped_column, Session, relationship
from app.db import DATABASE_URL, engine, Base, session

class Scenario(Base):
    __tablename__='scenarios'
    id:Mapped[str]=mapped_column(String(36),primary_key=True)
    name:Mapped[str]=mapped_column(String(120),nullable=False)
    description:Mapped[str]=mapped_column(String(2000),default='')
    delay:Mapped[int]=mapped_column(Integer,default=30)
    breakdown:Mapped[bool]=mapped_column(default=False)
    seed:Mapped[int]=mapped_column(Integer,default=42)
    created_at:Mapped[datetime]=mapped_column(DateTime(timezone=True),default=lambda:datetime.now(timezone.utc))
    runs:Mapped[list['Run']]=relationship(back_populates='scenario',cascade='all, delete-orphan')
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
    assignment: Mapped['FlightAircraftAssignment | None'] = relationship(
        back_populates='flight', uselist=False, cascade='all, delete-orphan'
    )

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
    flight_plan_id: Mapped[str] = mapped_column(
        ForeignKey('flight_plans.id', ondelete='CASCADE'), primary_key=True
    )
    aircraft_id: Mapped[str] = mapped_column(
        ForeignKey('aircraft.id'), index=True, nullable=False
    )
    flight: Mapped[PlannedFlight] = relationship(back_populates='assignment')

class Run(Base):
    __tablename__='runs'
    id:Mapped[str]=mapped_column(String(36),primary_key=True)
    scenario_id:Mapped[str]=mapped_column(ForeignKey('scenarios.id'),index=True)
    strategy:Mapped[str]=mapped_column(String(20))
    result:Mapped[dict]=mapped_column(JSON)
    created_at:Mapped[datetime]=mapped_column(DateTime(timezone=True),default=lambda:datetime.now(timezone.utc))
    scenario:Mapped[Scenario]=relationship(back_populates='runs')
class Airport(Base):
    __tablename__='airports'
    id:Mapped[str]=mapped_column(String(36),primary_key=True)
    name:Mapped[str]=mapped_column(String(120),nullable=False)
    code:Mapped[str]=mapped_column(String(8),unique=True)
    layout:Mapped[dict]=mapped_column(JSON,default=dict)
class Audit(Base):
    __tablename__='audit_events'
    id:Mapped[str]=mapped_column(String(36),primary_key=True)
    action:Mapped[str]=mapped_column(String(50))
    subject_id:Mapped[str]=mapped_column(String(36))
    created_at:Mapped[datetime]=mapped_column(DateTime(timezone=True),default=lambda:datetime.now(timezone.utc))

from app.operations.models import Runway, Taxiway, GroundVehicle, GroundTask
from app.operations.router import router as operations_router, initialize_demo_infrastructure
from app.operations.catalog import catalog_router

@asynccontextmanager
async def lifespan(app:FastAPI):
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        initialize_demo_infrastructure(db)
    yield
app=FastAPI(title='AirportOps API',version='0.5.0',description='Airports, scenarios, immutable simulation runs',lifespan=lifespan)
app.add_middleware(CORSMiddleware,allow_origins=os.getenv('CORS_ORIGINS','http://localhost:5173,http://127.0.0.1:5173').split(','),allow_credentials=False,allow_methods=['GET','POST','PATCH','DELETE'],allow_headers=['*'])
class ScenarioIn(BaseModel):
    name:str=Field(min_length=1,max_length=120)
    description:str=Field(default='',max_length=2000)
    delay:int=Field(default=30,ge=0,le=180)
    breakdown:bool=False
    seed:int=Field(default=42,ge=1,le=2147483647)
class ScenarioOut(ScenarioIn):
    id:str
    created_at:datetime
    model_config={'from_attributes':True}
class RunIn(BaseModel):
    strategy:Literal['baseline','optimized']
    finished:int=Field(ge=0,le=10)
    total_delay:int=Field(ge=0)
    conflicts:int=Field(ge=0)
    vehicle_missions:int=Field(ge=0)
    vehicle_distance:int=Field(default=0,ge=0)
    max_delay:int=Field(default=0,ge=0)
    flights:list[dict]=Field(default_factory=list,max_length=10)
class RunOut(BaseModel):
    id:str
    scenario_id:str
    strategy:str
    result:dict
    created_at:datetime
    model_config={'from_attributes':True}
class AirportIn(BaseModel):
    name:str=Field(min_length=1,max_length=120)
    code:str=Field(min_length=3,max_length=8,pattern='^[A-Z0-9]+$')
    layout:dict=Field(default_factory=dict)
class AirportOut(AirportIn):
    id:str
    model_config={'from_attributes':True}
class FlightPlanIn(BaseModel):
    flight_number: str = Field(min_length=3, max_length=12, pattern=r'^[A-Z0-9-]+$')
    airline: str = Field(min_length=1, max_length=80)
    origin: str = Field(min_length=3, max_length=3, pattern=r'^[A-Z]{3}$')
    destination: str = Field(min_length=3, max_length=3, pattern=r'^[A-Z]{3}$')
    scheduled_minute: int = Field(ge=0, le=1200)
    duration_minutes: int = Field(ge=5, le=180)
    aircraft_id: str | None = None

class FlightPlanPatch(BaseModel):
    flight_number: str | None = Field(default=None, min_length=3, max_length=12, pattern=r'^[A-Z0-9-]+$')
    airline: str | None = Field(default=None, min_length=1, max_length=80)
    origin: str | None = Field(default=None, min_length=3, max_length=3, pattern=r'^[A-Z]{3}$')
    destination: str | None = Field(default=None, min_length=3, max_length=3, pattern=r'^[A-Z]{3}$')
    scheduled_minute: int | None = Field(default=None, ge=0, le=1200)
    duration_minutes: int | None = Field(default=None, ge=5, le=180)
    aircraft_id: str | None = None

class FlightPlanOut(FlightPlanIn):
    id: str
    model_config = {'from_attributes': True}

class AircraftIn(BaseModel):
    registration: str = Field(min_length=3, max_length=12, pattern=r'^[A-Z0-9-]+$')
    airline: str = Field(min_length=1, max_length=80)
    manufacturer: str = Field(min_length=1, max_length=80)
    model: str = Field(min_length=1, max_length=80)
    category: Literal['regional', 'narrow_body', 'wide_body'] = 'narrow_body'
    seats: int = Field(ge=1, le=900)

class AircraftPatch(BaseModel):
    registration: str | None = Field(default=None, min_length=3, max_length=12, pattern=r'^[A-Z0-9-]+$')
    airline: str | None = Field(default=None, min_length=1, max_length=80)
    manufacturer: str | None = Field(default=None, min_length=1, max_length=80)
    model: str | None = Field(default=None, min_length=1, max_length=80)
    category: Literal['regional', 'narrow_body', 'wide_body'] | None = None
    seats: int | None = Field(default=None, ge=1, le=900)

class AircraftOut(AircraftIn):
    id: str
    model_config = {'from_attributes': True}

class CompareIn(BaseModel):
    baseline_run_id:str
    optimized_run_id:str

def audit(db:Session,action:str,id:str):db.add(Audit(id=str(uuid4()),action=action,subject_id=id))
app.include_router(operations_router)
app.include_router(catalog_router)

@app.get('/health')
def health():return {'status':'ok'}
def check_aircraft_assignment(
    db: Session, aircraft_id: str | None, flight_id: str,
    scheduled_minute: int, duration_minutes: int,
) -> None:
    if aircraft_id is None:
        return
    if db.get(Aircraft, aircraft_id) is None:
        raise HTTPException(404, 'Aircraft not found')
    # One aircraft cannot serve overlapping planned ground-service windows.
    assignments = db.execute(
        select(FlightAircraftAssignment, PlannedFlight)
        .join(PlannedFlight, PlannedFlight.id == FlightAircraftAssignment.flight_plan_id)
        .where(FlightAircraftAssignment.aircraft_id == aircraft_id)
        .where(FlightAircraftAssignment.flight_plan_id != flight_id)
    ).all()
    end_minute = scheduled_minute + duration_minutes
    for _, other in assignments:
        other_end = other.scheduled_minute + other.duration_minutes
        if scheduled_minute < other_end and other.scheduled_minute < end_minute:
            raise HTTPException(409, 'Aircraft is assigned to an overlapping flight')

@app.get('/api/aircraft', response_model=list[AircraftOut])
def list_aircraft(db: Session = Depends(session)):
    return db.scalars(select(Aircraft).order_by(Aircraft.registration)).all()

@app.get('/api/aircraft/{id}', response_model=AircraftOut)
def get_aircraft(id: str, db: Session = Depends(session)):
    item = db.get(Aircraft, id)
    if item is None:
        raise HTTPException(404, 'Aircraft not found')
    return item

@app.post('/api/aircraft', response_model=AircraftOut, status_code=201)
def add_aircraft(payload: AircraftIn, db: Session = Depends(session)):
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

@app.patch('/api/aircraft/{id}', response_model=AircraftOut)
def update_aircraft(id: str, payload: AircraftPatch, db: Session = Depends(session)):
    item = db.get(Aircraft, id)
    if item is None:
        raise HTTPException(404, 'Aircraft not found')
    changes = payload.model_dump(exclude_unset=True)
    if not changes or any(value is None for value in changes.values()):
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

@app.delete('/api/aircraft/{id}', status_code=204)
def delete_aircraft(id: str, db: Session = Depends(session)):
    item = db.get(Aircraft, id)
    if item is None:
        raise HTTPException(404, 'Aircraft not found')
    if db.scalar(select(FlightAircraftAssignment.flight_plan_id)
                 .where(FlightAircraftAssignment.aircraft_id == id).limit(1)):
        raise HTTPException(409, 'Aircraft is assigned to a flight; unassign it first')
    db.delete(item)
    audit(db, 'aircraft.deleted', id)
    db.commit()

@app.get('/api/flight-plans', response_model=list[FlightPlanOut])
def list_flight_plans(db: Session = Depends(session)):
    return db.scalars(select(PlannedFlight).order_by(PlannedFlight.scheduled_minute, PlannedFlight.flight_number)).all()

@app.post('/api/flight-plans', response_model=FlightPlanOut, status_code=201)
def add_flight_plan(payload: FlightPlanIn, db: Session = Depends(session)):
    if (db.scalar(select(func.count()).select_from(PlannedFlight)) or 0) >= 10:
        raise HTTPException(409, 'Maximum 10 flights supported in V0.2')
    data = payload.model_dump(exclude={'aircraft_id'})
    item = PlannedFlight(id=str(uuid4()), **data)
    check_aircraft_assignment(db, payload.aircraft_id, item.id,
                              item.scheduled_minute, item.duration_minutes)
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

@app.patch('/api/flight-plans/{id}', response_model=FlightPlanOut)
def update_flight_plan(id: str, payload: FlightPlanPatch, db: Session = Depends(session)):
    item = db.get(PlannedFlight, id)
    if not item:
        raise HTTPException(404, 'Flight not found')
    changes = payload.model_dump(exclude_unset=True)
    if not changes or any(value is None for key, value in changes.items() if key != 'aircraft_id'):
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

@app.delete('/api/flight-plans/{id}', status_code=204)
def delete_flight_plan(id: str, db: Session = Depends(session)):
    item = db.get(PlannedFlight, id)
    if not item:
        raise HTTPException(404, 'Flight not found')
    db.execute(delete(GroundTask).where(GroundTask.flight_plan_id == id))
    db.delete(item)
    audit(db, 'flight_plan.deleted', id)
    db.commit()

@app.get('/api/airports',response_model=list[AirportOut])
def airports(db:Session=Depends(session)):return db.scalars(select(Airport)).all()
@app.post('/api/airports',response_model=AirportOut,status_code=201)
def add_airport(payload:AirportIn,db:Session=Depends(session)):
    if db.scalar(select(Airport).where(Airport.code==payload.code)):raise HTTPException(409,'Airport code already exists')
    item=Airport(id=str(uuid4()),**payload.model_dump());db.add(item);audit(db,'airport.created',item.id);db.commit();db.refresh(item);return item
@app.get('/api/scenarios',response_model=list[ScenarioOut])
def list_scenarios(db:Session=Depends(session)):return db.scalars(select(Scenario).order_by(Scenario.created_at.desc())).all()
@app.post('/api/scenarios',response_model=ScenarioOut,status_code=201)
def add_scenario(payload:ScenarioIn,db:Session=Depends(session)):
    item=Scenario(id=str(uuid4()),**payload.model_dump());db.add(item);audit(db,'scenario.created',item.id);db.commit();db.refresh(item);return item
@app.get('/api/scenarios/{id}',response_model=ScenarioOut)
def get_scenario(id:str,db:Session=Depends(session)):
    item=db.get(Scenario,id)
    if not item:raise HTTPException(404,'Scenario not found')
    return item
@app.patch('/api/scenarios/{id}',response_model=ScenarioOut)
def patch_scenario(id:str,payload:ScenarioIn,db:Session=Depends(session)):
    item=db.get(Scenario,id)
    if not item:raise HTTPException(404,'Scenario not found')
    for key,value in payload.model_dump().items():setattr(item,key,value)
    audit(db,'scenario.updated',id);db.commit();db.refresh(item);return item
@app.post('/api/scenarios/{id}/duplicate',response_model=ScenarioOut,status_code=201)
def duplicate_scenario(id:str,db:Session=Depends(session)):
    item=db.get(Scenario,id)
    if not item:raise HTTPException(404,'Scenario not found')
    new=Scenario(id=str(uuid4()),name=item.name+' (copie)',description=item.description,delay=item.delay,breakdown=item.breakdown,seed=item.seed)
    db.add(new);audit(db,'scenario.duplicated',new.id);db.commit();db.refresh(new);return new
@app.delete('/api/scenarios/{id}',status_code=204)
def delete_scenario(id:str,db:Session=Depends(session)):
    item=db.get(Scenario,id)
    if not item:raise HTTPException(404,'Scenario not found')
    db.delete(item);audit(db,'scenario.deleted',id);db.commit()
@app.post('/api/scenarios/{id}/runs',response_model=RunOut,status_code=201)
def save_run(id:str,payload:RunIn,db:Session=Depends(session)):
    if not db.get(Scenario,id):raise HTTPException(404,'Scenario not found')
    run=Run(id=str(uuid4()),scenario_id=id,strategy=payload.strategy,result=payload.model_dump())
    db.add(run);audit(db,'run.created',run.id);db.commit();db.refresh(run);return run
@app.get('/api/scenarios/{id}/runs',response_model=list[RunOut])
def list_runs(id:str,db:Session=Depends(session)):
    if not db.get(Scenario,id):raise HTTPException(404,'Scenario not found')
    return db.scalars(select(Run).where(Run.scenario_id==id).order_by(Run.created_at.desc())).all()
@app.get('/api/runs/{id}',response_model=RunOut)
def get_run(id:str,db:Session=Depends(session)):
    item=db.get(Run,id)
    if not item:raise HTTPException(404,'Run not found')
    return item
@app.post('/api/comparisons')
def compare_runs(payload:CompareIn,db:Session=Depends(session)):
    first=db.get(Run,payload.baseline_run_id);second=db.get(Run,payload.optimized_run_id)
    if not first or not second:raise HTTPException(404,'Run not found')
    if first.scenario_id!=second.scenario_id:raise HTTPException(400,'Runs must belong to the same scenario')
    metrics=['total_delay','conflicts','vehicle_missions','vehicle_distance','max_delay']
    return {'scenario_id':first.scenario_id,'baseline':first.result,'optimized':second.result,'delta':{key:second.result.get(key,0)-first.result.get(key,0) for key in metrics},'note':'Client-produced simulation results are not independently verified by the server.'}
@app.get('/api/audit')
def audit_log(limit:int=20,db:Session=Depends(session)):
    if limit<1 or limit>100:raise HTTPException(422,'limit must be 1..100')
    items=db.scalars(select(Audit).order_by(Audit.created_at.desc()).limit(limit)).all()
    return [{'action':x.action,'subject_id':x.subject_id,'created_at':x.created_at} for x in items]
