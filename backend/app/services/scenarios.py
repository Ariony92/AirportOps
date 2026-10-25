"""Scenario-specific, reproducible planning inputs and server-side results."""
from __future__ import annotations

from random import Random
from types import SimpleNamespace
from sqlalchemy.orm import Session
from app.models import Scenario
from app.operations.queries import load_forecast_inputs
from app.operations.service import forecast, Strategy

# All minutes are relative to the simulated 06:00 start. This deliberately
# represents a temporary breakdown, not a permanently disabled fleet vehicle.
BREAKDOWN_END_MINUTE = 240


def generate_scenario_forecast(db: Session, scenario: Scenario,
                               strategy: Strategy) -> dict:
    """Apply a seeded delay/failure without saving changes to flights or vehicles.

    Scenario delay applies to exactly one reproducibly selected flight.
    Scenario breakdown takes one available service vehicle out of service
    from minute 0 to 240. Both share the planning model used for live playback.
    """
    inputs = load_forecast_inputs(db)
    rng = Random(scenario.seed)
    flights = sorted(inputs['flights'], key=lambda f: (f.scheduled_minute, f.flight_number))
    usable_vehicles = sorted(
        (v for v in inputs['vehicles'] if v.available and not v.maintenance),
        key=lambda v: (v.code, v.id),
    )
    chosen_flight = rng.choice(flights) if scenario.delay and flights else None
    chosen_vehicle = rng.choice(usable_vehicles) if scenario.breakdown and usable_vehicles else None
    scenario_incidents = []
    if chosen_flight is not None:
        scenario_incidents.append(SimpleNamespace(
            id='scenario-delay', kind='flight_delay', target_id=chosen_flight.id,
            enabled=True, start_minute=0, end_minute=1440,
            delay_minutes=scenario.delay,
        ))
    if chosen_vehicle is not None:
        scenario_incidents.append(SimpleNamespace(
            id='scenario-breakdown', kind='vehicle_failure', target_id=chosen_vehicle.id,
            enabled=True, start_minute=0, end_minute=BREAKDOWN_END_MINUTE,
            delay_minutes=0,
        ))
    inputs['incidents'] = [*inputs['incidents'], *scenario_incidents]
    result = forecast(**inputs, strategy=strategy)
    result['scenario_inputs'] = {
        'delay_minutes': scenario.delay,
        'breakdown_enabled': scenario.breakdown,
        'seed': scenario.seed,
        'delayed_flight': chosen_flight.flight_number if chosen_flight else None,
        'failed_vehicle': chosen_vehicle.code if chosen_vehicle else None,
        'failure_window_minutes': [0, BREAKDOWN_END_MINUTE] if chosen_vehicle else None,
        'source': 'Snapshot du planning et des incidents globaux, avec perturbations propres au scénario',
    }
    return result
