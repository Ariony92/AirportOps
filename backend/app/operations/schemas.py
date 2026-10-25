"""Input validation and public DTOs. PATCH excludes unset keys."""
from typing import Literal
from pydantic import BaseModel, Field, model_validator
from datetime import datetime

VehicleKind = Literal['baggage', 'fuel', 'cleaning', 'catering', 'tug']

class RunwayIn(BaseModel):
    designation: str = Field(min_length=2, max_length=16, pattern=r'^[A-Z0-9/-]+$')
    length_m: int = Field(ge=400, le=6000)
    separation_min: int = Field(default=3, ge=1, le=15)
    active: bool = True

class RunwayPatch(BaseModel):
    designation: str | None = Field(default=None, min_length=2, max_length=16, pattern=r'^[A-Z0-9/-]+$')
    length_m: int | None = Field(default=None, ge=400, le=6000)
    separation_min: int | None = Field(default=None, ge=1, le=15)
    active: bool | None = None

class RunwayOut(RunwayIn):
    id: str
    model_config = {'from_attributes': True}

class TaxiwayIn(BaseModel):
    start_node: int = Field(ge=0, le=6)
    end_node: int = Field(ge=0, le=6)
    distance_m: int = Field(ge=1, le=10000)
    active: bool = True

    @model_validator(mode='after')
    def different_nodes(self):
        if self.start_node == self.end_node:
            raise ValueError('Taxiway must connect two distinct nodes')
        return self

class TaxiwayPatch(BaseModel):
    distance_m: int | None = Field(default=None, ge=1, le=10000)
    active: bool | None = None

class TaxiwayOut(TaxiwayIn):
    id: str
    model_config = {'from_attributes': True}

class VehicleIn(BaseModel):
    code: str = Field(min_length=2, max_length=24, pattern=r'^[A-Z0-9-]+$')
    kind: VehicleKind
    speed_kmh: int = Field(ge=5, le=120)
    capacity_units: int = Field(ge=1, le=500)
    fuel_pct: int = Field(default=100, ge=0, le=100)
    available: bool = True
    maintenance: bool = False
    home_node: int = Field(default=1, ge=0, le=6)
    cost_per_hour: int = Field(default=30, ge=0, le=10000)

class VehiclePatch(BaseModel):
    code: str | None = Field(default=None, min_length=2, max_length=24, pattern=r'^[A-Z0-9-]+$')
    kind: VehicleKind | None = None
    speed_kmh: int | None = Field(default=None, ge=5, le=120)
    capacity_units: int | None = Field(default=None, ge=1, le=500)
    fuel_pct: int | None = Field(default=None, ge=0, le=100)
    available: bool | None = None
    maintenance: bool | None = None
    home_node: int | None = Field(default=None, ge=0, le=6)
    cost_per_hour: int | None = Field(default=None, ge=0, le=10000)

class VehicleOut(VehicleIn):
    id: str
    model_config = {'from_attributes': True}

class TaskIn(BaseModel):
    flight_plan_id: str
    kind: VehicleKind
    duration_min: int = Field(ge=1, le=180)
    units: int = Field(default=1, ge=1, le=500)

class TaskPatch(BaseModel):
    kind: VehicleKind | None = None
    duration_min: int | None = Field(default=None, ge=1, le=180)
    units: int | None = Field(default=None, ge=1, le=500)

class TaskOut(TaskIn):
    id: str
    model_config = {'from_attributes': True}

class ForecastOptions(BaseModel):
    include_demo_flights: bool = True


from typing import Literal as IncidentLiteral

IncidentKind = IncidentLiteral['runway_closure', 'taxiway_closure', 'vehicle_failure', 'flight_delay']
Strategy = IncidentLiteral['baseline', 'optimized']

class IncidentIn(BaseModel):
    kind: IncidentKind
    target_id: str = Field(min_length=1, max_length=36)
    start_minute: int = Field(ge=0, le=1439)
    end_minute: int = Field(ge=1, le=1440)
    delay_minutes: int = Field(default=0, ge=0, le=180)
    description: str = Field(default='', max_length=240)
    enabled: bool = True

    @model_validator(mode='after')
    def check_timing(self):
        if self.end_minute <= self.start_minute:
            raise ValueError('La fin doit être après le début')
        if self.kind == 'flight_delay' and self.delay_minutes == 0:
            raise ValueError('Un retard doit avoir une durée positive')
        if self.kind != 'flight_delay' and self.delay_minutes != 0:
            raise ValueError('Le champ retard est réservé aux incidents de vol')
        return self

class IncidentOut(IncidentIn):
    id: str
    model_config = {'from_attributes': True}

class SavedForecastIn(BaseModel):
    label: str = Field(default='Prévision', min_length=1, max_length=100)
    strategy: Strategy = 'optimized'

class SavedForecastOut(BaseModel):
    id: str
    label: str
    strategy: Strategy
    incident_count: int
    result: dict
    created_at: datetime
    model_config = {'from_attributes': True}
