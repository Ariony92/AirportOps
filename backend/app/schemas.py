"""Core request and response contracts."""
from datetime import datetime
from typing import Literal
from pydantic import BaseModel, Field

class ScenarioIn(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    description: str = Field(default='', max_length=2000)
    delay: int = Field(default=30, ge=0, le=180)
    breakdown: bool = False
    seed: int = Field(default=42, ge=1, le=2147483647)

class ScenarioOut(ScenarioIn):
    id: str
    created_at: datetime
    model_config = {'from_attributes': True}

class RunOut(BaseModel):
    id: str
    scenario_id: str
    strategy: str
    result: dict
    created_at: datetime
    model_config = {'from_attributes': True}

class AirportIn(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    code: str = Field(min_length=3, max_length=8, pattern='^[A-Z0-9]+$')
    layout: dict = Field(default_factory=dict)

class AirportOut(AirportIn):
    id: str
    model_config = {'from_attributes': True}

class FlightPlanIn(BaseModel):
    flight_number: str = Field(min_length=3, max_length=12, pattern='^[A-Z0-9-]+$')
    airline: str = Field(min_length=1, max_length=80)
    origin: str = Field(min_length=3, max_length=3, pattern='^[A-Z]{3}$')
    destination: str = Field(min_length=3, max_length=3, pattern='^[A-Z]{3}$')
    scheduled_minute: int = Field(ge=0, le=1200)
    duration_minutes: int = Field(ge=5, le=180)
    aircraft_id: str | None = None

class FlightPlanPatch(BaseModel):
    flight_number: str | None = Field(default=None, min_length=3, max_length=12, pattern='^[A-Z0-9-]+$')
    airline: str | None = Field(default=None, min_length=1, max_length=80)
    origin: str | None = Field(default=None, min_length=3, max_length=3, pattern='^[A-Z]{3}$')
    destination: str | None = Field(default=None, min_length=3, max_length=3, pattern='^[A-Z]{3}$')
    scheduled_minute: int | None = Field(default=None, ge=0, le=1200)
    duration_minutes: int | None = Field(default=None, ge=5, le=180)
    aircraft_id: str | None = None

class FlightPlanOut(FlightPlanIn):
    id: str
    model_config = {'from_attributes': True}

class AircraftIn(BaseModel):
    registration: str = Field(min_length=3, max_length=12, pattern='^[A-Z0-9-]+$')
    airline: str = Field(min_length=1, max_length=80)
    manufacturer: str = Field(min_length=1, max_length=80)
    model: str = Field(min_length=1, max_length=80)
    category: Literal['regional', 'narrow_body', 'wide_body'] = 'narrow_body'
    seats: int = Field(ge=1, le=900)

class AircraftPatch(BaseModel):
    registration: str | None = Field(default=None, min_length=3, max_length=12, pattern='^[A-Z0-9-]+$')
    airline: str | None = Field(default=None, min_length=1, max_length=80)
    manufacturer: str | None = Field(default=None, min_length=1, max_length=80)
    model: str | None = Field(default=None, min_length=1, max_length=80)
    category: Literal['regional', 'narrow_body', 'wide_body'] | None = None
    seats: int | None = Field(default=None, ge=1, le=900)

class AircraftOut(AircraftIn):
    id: str
    model_config = {'from_attributes': True}

class CompareIn(BaseModel):
    baseline_run_id: str
    optimized_run_id: str
