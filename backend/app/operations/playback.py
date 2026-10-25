"""Presentation projections derived only from the server's operational forecast.

The frontend receives scheduled visual keyframes; it never decides which resource
is available, which flight is delayed or when a service vehicle moves.
"""
from __future__ import annotations

from typing import Any

GATE_X = (112, 282, 452, 622, 792)
DEPOT = (450, 286)


def gate_position(gate: int | None) -> tuple[int, int]:
    if gate is None or not 0 <= gate < len(GATE_X):
        return DEPOT
    return (GATE_X[gate], 187)


def project_playback(forecast: dict[str, Any], vehicle_codes: list[str]) -> dict[str, Any]:
    """Convert planned movements into explicit timestamped scene tracks."""
    events = forecast['timeline']
    flights = {f['flight_number']: f for f in forecast['flights']}
    tracks: list[dict[str, Any]] = []
    actors = {}
    max_minute = 30
    for number, flight in flights.items():
        gate_x, gate_y = gate_position(flight['gate'])
        runway_x = 310
        # State transitions follow planned flight phases, not an independent clock.
        positions = {
            'approach': (50, 390), 'landing': (runway_x, 390),
            'runway_exit': (450, 390), 'taxi_in': (450, 285),
            'at_gate': (gate_x, gate_y), 'pushback': (gate_x, 285),
            'taxi_out': (450, 390), 'takeoff': (840, 390),
        }
        phases = [e for e in events if e['flight_number'] == number and e['phase'] in positions]
        if not phases:
            continue
        keyframes = [dict(minute=e['minute'], x=positions[e['phase']][0],
                          y=positions[e['phase']][1], phase=e['phase'], label=e['details'])
                     for e in phases]
        if flight['status'] == 'blocked':
            keyframes.append({**keyframes[-1], 'minute': max(keyframes[-1]['minute'] + 1, next(
                (e['minute'] for e in events if e['flight_number'] == number and e['phase'] == 'blocked'),
                keyframes[-1]['minute'] + 1)), 'phase': 'blocked', 'label': flight['reason'] or 'Bloqué'})
        keyframes.sort(key=lambda k: k['minute'])
        last = keyframes[-1]['minute']
        tracks.append({'id': number, 'kind': 'aircraft', 'label': number, 'keyframes': keyframes,
                       'visible_from': keyframes[0]['minute'],
                       'visible_until': last + 1 if flight['status'] == 'completed' else last + 30})
        max_minute = max(max_minute, last + 10)
        actors[number] = flight

    # Vehicle dispatch timing is emitted by the operational planner. Once a
    # vehicle completes an assignment, it remains parked until its next dispatch.
    for code in vehicle_codes:
        jobs = sorted((e for e in events if e.get('vehicle') == code and e['phase'] in
                       ('vehicle_dispatch', 'service_start', 'service_end', 'pushback')),
                      key=lambda e: (e['minute'], {'vehicle_dispatch': 0, 'service_start': 1,
                                                      'pushback': 1, 'service_end': 2}.get(e['phase'], 3)))
        if not jobs:
            continue
        frames = [{'minute': 0, 'x': DEPOT[0], 'y': DEPOT[1], 'phase': 'idle', 'label': 'En attente'}]
        location = DEPOT
        for event in jobs:
            flight = flights.get(event['flight_number'])
            target = gate_position(flight['gate'] if flight else None)
            if event['phase'] == 'vehicle_dispatch':
                # Last position remains stable until this event.
                frames.append({'minute': event['minute'], 'x': location[0], 'y': location[1],
                               'phase': 'dispatch', 'label': 'Départ en mission'})
            else:
                if event['phase'] in ('service_start', 'pushback'):
                    location = target
                frames.append({'minute': event['minute'], 'x': location[0], 'y': location[1],
                               'phase': event['phase'], 'label': event['details']})
            max_minute = max(max_minute, event['minute'] + 10)
        tracks.append({'id': code, 'kind': 'vehicle', 'label': code, 'keyframes': frames,
                       'visible_from': 0, 'visible_until': max_minute + 30})
    for track in tracks:
        if track['kind'] == 'vehicle':
            track['visible_until'] = min(1440, max_minute)
    return {'version': 1, 'duration_minutes': min(1440, max_minute),
            'tracks': tracks, 'timeline': events, 'flights': forecast['flights'],
            'kpis': forecast['kpis'], 'strategy': forecast['strategy'],
            'note': forecast['note']}
