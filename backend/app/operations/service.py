"""Deterministic educational airport lifecycle forecast.

Models a runway slot calendar, configurable taxiway graph, five stands and
resource-constrained ground tasks. Does not implement certified ATC rules.
Forecast is read-only: availability and fuel are simulated from a snapshot.
"""
from __future__ import annotations
import heapq
import math
from collections import defaultdict
from typing import Any

DEFAULT_TASKS = [
    ('baggage', 12, 2), ('fuel', 15, 1), ('cleaning', 10, 1),
    ('catering', 9, 1), ('tug', 6, 1),
]
GATES = (2, 3, 4, 5, 6)
CATEGORY_MIN_LENGTH = {'regional': 900, 'narrow_body': 1700, 'wide_body': 2500}


def shortest_path(edges: list[Any], source: int, target: int) -> int | None:
    """Dijkstra; return path length (m), None if disconnected."""
    graph: dict[int, list[tuple[int, int]]] = defaultdict(list)
    for edge in edges:
        if not edge.active:
            continue
        graph[edge.start_node].append((edge.end_node, edge.distance_m))
        graph[edge.end_node].append((edge.start_node, edge.distance_m))
    queue = [(0, source)]
    best = {source: 0}
    while queue:
        dist, node = heapq.heappop(queue)
        if dist != best[node]:
            continue
        if node == target:
            return dist
        for next_node, weight in graph[node]:
            candidate = dist + weight
            if candidate < best.get(next_node, math.inf):
                best[next_node] = candidate
                heapq.heappush(queue, (candidate, next_node))
    return None


def reserve_slot(bookings: list[tuple[int, int]], requested: int, duration: int, separation: int) -> int:
    """Earliest slot respecting every previously reserved slot (including future slots)."""
    moment = max(0, requested)
    for start, end in sorted(bookings):
        if moment + duration + separation <= start:
            break
        if moment >= end + separation:
            continue
        moment = end + separation
    bookings.append((moment, moment + duration))
    return moment


def forecast(flights: list[Any], aircraft: dict[str, Any], runways: list[Any],
             taxiways: list[Any], vehicles: list[Any], tasks: list[Any]) -> dict[str, Any]:
    active_runways = [r for r in runways if r.active]
    reservations: dict[str, list[tuple[int, int]]] = {r.id: [] for r in active_runways}
    gate_free = {gate: 0 for gate in GATES}
    fleet = {v.id: {'free': 0, 'node': v.home_node, 'fuel': v.fuel_pct} for v in vehicles}
    task_lookup: dict[str, list[Any]] = defaultdict(list)
    for task in tasks:
        task_lookup[task.flight_plan_id].append(task)

    timeline: list[dict[str, Any]] = []
    results: list[dict[str, Any]] = []
    totals = {'flights': len(flights), 'completed': 0, 'blocked': 0,
              'runway_conflicts_avoided': 0, 'vehicle_missions': 0,
              'total_delay_min': 0, 'taxi_distance_m': 0,
              'vehicle_distance_m': 0, 'estimated_vehicle_cost': 0.0}

    def emit(flight: Any, minute: int, phase: str, details: str, vehicle: str | None = None) -> None:
        timeline.append({'flight_number': flight.flight_number, 'minute': int(minute),
                         'phase': phase, 'details': details, 'vehicle': vehicle})

    for flight in sorted(flights, key=lambda f: (f.scheduled_minute, f.flight_number)):
        assigned = aircraft.get(flight.aircraft_id)
        required = CATEGORY_MIN_LENGTH.get(assigned.category if assigned else 'narrow_body', 1700)
        candidates = [r for r in active_runways if r.length_m >= required]
        summary: dict[str, Any] = {'flight_number': flight.flight_number,
              'aircraft_registration': assigned.registration if assigned else None,
              'runway': None, 'gate': None, 'status': 'blocked',
              'reason': None, 'landing_minute': None, 'takeoff_minute': None,
              'delay_min': 0, 'operations': []}
        results.append(summary)
        emit(flight, max(0, flight.scheduled_minute-5), 'approach', 'Approche de l’aéroport')
        if not candidates:
            summary['reason'] = 'Aucune piste ouverte suffisamment longue'
            emit(flight, flight.scheduled_minute, 'blocked', summary['reason'])
            totals['blocked'] += 1
            continue

        accessible = [(shortest_path(taxiways, 0, gate), gate) for gate in GATES]
        accessible = [(dist, gate) for dist, gate in accessible if dist is not None]
        if not accessible:
            summary['reason'] = 'Aucune voie de circulation vers les portes'
            emit(flight, flight.scheduled_minute, 'blocked', summary['reason'])
            totals['blocked'] += 1
            continue
        # One of the eligible runways, earliest feasible landing slot.
        proposals = []
        for runway in candidates:
            temp = reservations[runway.id].copy()
            minute = reserve_slot(temp, flight.scheduled_minute, 2, runway.separation_min)
            proposals.append((minute, runway.designation, runway))
        landing, _, runway = min(proposals, key=lambda x: (x[0], x[1]))
        reserve_slot(reservations[runway.id], landing, 2, runway.separation_min)
        if landing > flight.scheduled_minute:
            totals['runway_conflicts_avoided'] += 1
        summary['runway'] = runway.designation
        summary['landing_minute'] = landing
        emit(flight, landing, 'landing', f'Atterrissage piste {runway.designation}')
        emit(flight, landing + 2, 'runway_exit', 'Libération de la piste')

        options = []
        for distance, gate in accessible:
            taxi_min = max(1, math.ceil(distance / 500))
            ready = max(landing + 2 + taxi_min, gate_free[gate])
            options.append((ready, distance, gate, taxi_min))
        stand_time, distance, gate, taxi_min = min(options)
        if stand_time > landing + 2 + taxi_min:
            totals['runway_conflicts_avoided'] += 1
        gate_free[gate] = stand_time + 1
        summary['gate'] = gate - 1
        totals['taxi_distance_m'] += distance
        emit(flight, landing + 2, 'taxi_in', f'Roulage vers la porte {gate - 1}')
        emit(flight, stand_time, 'at_gate', f'Arrivée à la porte {gate - 1}')

        scheduled_tasks = task_lookup.get(flight.id)
        if scheduled_tasks:
            jobs = [(t.kind, t.duration_min, t.units) for t in scheduled_tasks]
            if not any(kind == 'tug' for kind, _, _ in jobs):
                jobs.append(('tug', 6, 1))
        else:
            jobs = DEFAULT_TASKS
        # Independent services overlap. Pushback requires every other service to finish.
        service_end = stand_time
        has_failed = False
        for kind, duration, units in [job for job in jobs if job[0] != 'tug']:
            chosen = None
            for vehicle in vehicles:
                if vehicle.kind != kind or not vehicle.available or vehicle.maintenance or vehicle.capacity_units < units:
                    continue
                state = fleet[vehicle.id]
                approach_distance = shortest_path(taxiways, state['node'], gate)
                if approach_distance is None:
                    continue
                fuel_needed = max(1, math.ceil(approach_distance / 5000))
                if state['fuel'] < fuel_needed:
                    continue
                travel = math.ceil(approach_distance * 60 / (vehicle.speed_kmh * 1000))
                start = max(stand_time, state['free'] + travel)
                candidate = (start, approach_distance, vehicle.code, vehicle, fuel_needed)
                if chosen is None or candidate[:3] < chosen[:3]:
                    chosen = candidate
            if chosen is None:
                summary['reason'] = f'Aucun véhicule disponible pour : {kind}'
                emit(flight, service_end, 'blocked', summary['reason'])
                has_failed = True
                break
            start, v_distance, _, vehicle, fuel_needed = chosen
            finish = start + duration
            state = fleet[vehicle.id]
            state.update({'free': finish, 'node': gate, 'fuel': state['fuel'] - fuel_needed})
            service_end = max(service_end, finish)
            totals['vehicle_missions'] += 1
            totals['vehicle_distance_m'] += v_distance
            totals['estimated_vehicle_cost'] += duration * vehicle.cost_per_hour / 60
            emit(flight, start, 'service_start', f'{kind} — début', vehicle.code)
            emit(flight, finish, 'service_end', f'{kind} — terminé', vehicle.code)
            summary['operations'].append({'kind': kind, 'vehicle': vehicle.code, 'start': start, 'end': finish})

        if not has_failed:
            pushback_duration = next((d for k, d, _ in jobs if k == 'tug'), 6)
            tug_units = next((u for k, _, u in jobs if k == 'tug'), 1)
            choices = []
            for vehicle in vehicles:
                if vehicle.kind != 'tug' or not vehicle.available or vehicle.maintenance or vehicle.capacity_units < tug_units:
                    continue
                state = fleet[vehicle.id]
                to_gate = shortest_path(taxiways, state['node'], gate)
                if to_gate is None:
                    continue
                fuel_needed = max(1, math.ceil(to_gate / 5000))
                if state['fuel'] < fuel_needed:
                    continue
                start = max(service_end, state['free'] + math.ceil(to_gate * 60 / (vehicle.speed_kmh * 1000)))
                choices.append((start, to_gate, vehicle.code, vehicle, fuel_needed))
            if choices:
                start, v_distance, _, vehicle, fuel_needed = min(choices)
                finish = start + pushback_duration
                fleet[vehicle.id].update({'free': finish, 'node': gate,
                                         'fuel': fleet[vehicle.id]['fuel'] - fuel_needed})
                totals['vehicle_missions'] += 1
                totals['vehicle_distance_m'] += v_distance
                totals['estimated_vehicle_cost'] += pushback_duration * vehicle.cost_per_hour / 60
                emit(flight, start, 'pushback', 'Repoussage depuis la porte', vehicle.code)
                summary['operations'].append({'kind': 'tug', 'vehicle': vehicle.code, 'start': start, 'end': finish})
                depart_request = finish + taxi_min
                emit(flight, finish, 'taxi_out', f'Roulage vers la piste {runway.designation}')
                takeoff = reserve_slot(reservations[runway.id], depart_request, 2, runway.separation_min)
                emit(flight, takeoff, 'takeoff', f'Décollage piste {runway.designation}')
                summary['takeoff_minute'] = takeoff
                summary['delay_min'] = max(0, takeoff - (flight.scheduled_minute + flight.duration_minutes + taxi_min * 2 + 8))
                summary['status'] = 'completed'
                totals['completed'] += 1
                totals['total_delay_min'] += summary['delay_min']
                totals['taxi_distance_m'] += distance
                gate_free[gate] = max(gate_free[gate], finish + 1)
                if takeoff > depart_request:
                    totals['runway_conflicts_avoided'] += 1
            else:
                summary['reason'] = 'Aucun tracteur de repoussage disponible'
                emit(flight, service_end, 'blocked', summary['reason'])
                has_failed = True
        if has_failed:
            gate_free[gate] = max(gate_free[gate], 1440)  # Stand unavailable for the remainder of the forecast.
            totals['blocked'] += 1

    timeline.sort(key=lambda item: (item['minute'], item['flight_number'], item['phase']))
    totals['estimated_vehicle_cost'] = round(totals['estimated_vehicle_cost'], 2)
    return {'kpis': totals, 'flights': results, 'timeline': timeline,
            'note': 'Prévision pédagogique non certifiée ; calcul C++ local distinct.'}
