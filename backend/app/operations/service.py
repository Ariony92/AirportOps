"""Reproducible airport-operations forecast with timed disruptions and resource constraints.

This is a read-only, minute-resolution planning model, not real-time ATC or the
other forecasting implementations. Incidents are replayed from a fixed snapshot; no service
vehicle or timetable state is persisted by forecast().
"""
from __future__ import annotations

from collections import defaultdict
import heapq
import math
from typing import Any, Literal

DEFAULT_TASKS = [
    ('baggage', 12, 2), ('fuel', 15, 1), ('cleaning', 10, 1),
    ('catering', 9, 1), ('tug', 6, 1),
]
GATES = (2, 3, 4, 5, 6)
CATEGORY_MIN_LENGTH = {'regional': 900, 'narrow_body': 1700, 'wide_body': 2500}
Strategy = Literal['baseline', 'optimized']


def shortest_path(edges: list[Any], source: int, target: int) -> int | None:
    """Dijkstra across active bidirectional links; None if disconnected."""
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


def reserve_slot(bookings: list[tuple[int, int]], requested: int,
                 duration: int, separation: int) -> int:
    """Reserve earliest collision-free interval, also considering future bookings."""
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
             taxiways: list[Any], vehicles: list[Any], tasks: list[Any],
             incidents: list[Any] | None = None,
             strategy: Strategy = 'optimized') -> dict[str, Any]:
    """Compute a new deterministic forecast without mutating supplied resources."""
    if strategy not in ('baseline', 'optimized'):
        raise ValueError('Stratégie inconnue')
    disruptions = [e for e in (incidents or []) if e.enabled]
    by_kind: dict[str, list[Any]] = defaultdict(list)
    for e in disruptions:
        by_kind[e.kind].append(e)
    applied: set[str] = set()

    def affects(e: Any, resource_id: str, minute: int, duration: int = 0) -> bool:
        return (e.target_id == resource_id and
                minute < e.end_minute and minute + duration > e.start_minute)

    def usable_route(source: int, target: int, requested: int,
                     speed_kmh: int = 30) -> tuple[int, int] | None:
        """Recompute a safe route; postpone movement when no detour exists.

        Closed links unrelated to the shortest route must not delay the flight.
        The graph approximation assumes the whole selected trip uses one minute-
        resolution availability window (no link-by-link traversal timing).
        """
        candidate_time = requested
        closures = by_kind['taxiway_closure']
        all_distance = shortest_path(taxiways, source, target)
        if all_distance is None:
            return None
        for _ in range(len(closures) * 2 + 3):
            trip_minutes = max(1, math.ceil(all_distance * 60 / (speed_kmh * 1000)))
            affecting = [event for event in closures
                         if event.start_minute < candidate_time + trip_minutes
                         and event.end_minute > candidate_time]
            blocked = {event.target_id for event in affecting}
            alternatives = [edge for edge in taxiways
                            if getattr(edge, 'id', None) not in blocked]
            new_distance = shortest_path(alternatives, source, target)
            if new_distance is not None:
                new_minutes = max(1, math.ceil(new_distance * 60 / (speed_kmh * 1000)))
                # Account for additional closures encountered by a longer detour.
                extended = [event for event in closures if
                            event.start_minute < candidate_time + new_minutes and
                            event.end_minute > candidate_time]
                extended_blocked = {event.target_id for event in extended}
                if extended_blocked != blocked:
                    more_safe = shortest_path([edge for edge in taxiways
                        if getattr(edge, 'id', None) not in extended_blocked], source, target)
                    if more_safe is None:
                        affecting = extended
                    else:
                        new_distance = more_safe
                        affecting = extended
                if new_distance is not None:
                    # Mark only closures that truly lengthen the computed route.
                    if new_distance > all_distance:
                        applied.update(event.id for event in affecting)
                    return candidate_time, new_distance
            if not affecting:
                return None
            relevant = [event for event in affecting
                        if getattr(event, 'target_id', None) in
                        {getattr(edge, 'id', None) for edge in taxiways if edge.active}]
            if not relevant:
                return None
            candidate_time = min(event.end_minute for event in relevant)
            applied.update(event.id for event in relevant)
        return None

    def after_vehicle_failure(vehicle_id: str, minute: int, duration: int) -> int:
        """Move operation after any overlapping vehicle-outage window."""
        for e in sorted(by_kind['vehicle_failure'], key=lambda x: x.start_minute):
            if affects(e, vehicle_id, minute, duration):
                minute = e.end_minute
                applied.add(e.id)
        return minute

    active_runways = sorted([r for r in runways if r.active], key=lambda r: r.designation)
    reservations: dict[str, list[tuple[int, int]]] = {r.id: [] for r in active_runways}
    for event in by_kind['runway_closure']:
        if event.target_id in reservations:
            reservations[event.target_id].append((event.start_minute, event.end_minute))
    taxi_bookings: list[tuple[int, int]] = []  # Simplified shared corridor resource.
    gate_free = {gate: 0 for gate in GATES}
    vehicle_state = {v.id: {'free': 0, 'node': v.home_node, 'fuel': v.fuel_pct}
                     for v in vehicles}
    task_lookup: dict[str, list[Any]] = defaultdict(list)
    for task in tasks:
        task_lookup[task.flight_plan_id].append(task)
    timeline: list[dict[str, Any]] = []
    results: list[dict[str, Any]] = []
    totals: dict[str, int | float] = {
        'flights': len(flights), 'completed': 0, 'blocked': 0,
        'runway_conflicts_avoided': 0, 'taxi_conflicts_avoided': 0,
        'vehicle_missions': 0, 'total_delay_min': 0,
        'taxi_distance_m': 0, 'vehicle_distance_m': 0,
        'estimated_vehicle_cost': 0.0, 'incident_delay_min': 0,
        'configured_incidents': len(disruptions), 'applied_incidents': 0,
        'service_minutes': 0,
    }

    def emit(flight: Any, minute: int, phase: str, details: str,
             vehicle: str | None = None) -> None:
        timeline.append({'flight_number': flight.flight_number, 'minute': int(minute),
                         'phase': phase, 'details': details, 'vehicle': vehicle})

    for flight in sorted(flights, key=lambda f: (f.scheduled_minute, f.flight_number)):
        requested = flight.scheduled_minute
        for event in by_kind['flight_delay']:
            if event.target_id == flight.id and event.start_minute <= requested < event.end_minute:
                requested += event.delay_minutes
                totals['incident_delay_min'] += event.delay_minutes
                applied.add(event.id)
                emit(flight, flight.scheduled_minute, 'disruption',
                     f'Retard de vol : +{event.delay_minutes} min')

        assigned = aircraft.get(flight.aircraft_id)
        required = CATEGORY_MIN_LENGTH.get(assigned.category if assigned else 'narrow_body', 1700)
        candidates = [r for r in active_runways if r.length_m >= required]
        summary: dict[str, Any] = {
            'flight_number': flight.flight_number,
            'aircraft_registration': assigned.registration if assigned else None,
            'runway': None, 'gate': None, 'status': 'blocked', 'reason': None,
            'landing_minute': None, 'takeoff_minute': None, 'delay_min': 0,
            'operations': [],
        }
        results.append(summary)
        emit(flight, max(0, requested - 5), 'approach', 'Approche de l’aéroport')
        if not candidates:
            summary['reason'] = 'Aucune piste ouverte suffisamment longue'
            emit(flight, requested, 'blocked', summary['reason'])
            totals['blocked'] += 1
            continue

        # Find runway options, respecting scheduled closures as blocked intervals.
        proposals = []
        for runway in candidates:
            temp = reservations[runway.id].copy()
            landing = reserve_slot(temp, requested, 2, runway.separation_min)
            proposals.append((landing, runway.designation, runway))
        if strategy == 'baseline':
            landing, _, runway = proposals[0]
        else:
            landing, _, runway = min(proposals, key=lambda item: (item[0], item[1]))
        reserve_slot(reservations[runway.id], landing, 2, runway.separation_min)
        if landing > requested:
            totals['runway_conflicts_avoided'] += 1
        for event in by_kind['runway_closure']:
            if event.target_id == runway.id and event.start_minute <= requested < event.end_minute:
                applied.add(event.id)
                totals['incident_delay_min'] += max(0, landing - requested)
                emit(flight, requested, 'disruption', 'Piste momentanément indisponible')
        summary['runway'] = runway.designation
        summary['landing_minute'] = landing
        emit(flight, landing, 'landing', f'Atterrissage piste {runway.designation}')
        emit(flight, landing + 2, 'runway_exit', 'Libération de la piste')

        gate_options = []
        for gate in GATES:
            route = usable_route(0, gate, landing + 2)
            if route is None:
                continue
            leave, distance = route
            taxi_min = max(1, math.ceil(distance / 500))
            temp = taxi_bookings.copy()
            taxi_in = reserve_slot(temp, leave, taxi_min, 1)
            ready = max(taxi_in + taxi_min, gate_free[gate])
            gate_options.append((ready, distance, gate, taxi_min, taxi_in))
        if not gate_options:
            summary['reason'] = 'Aucune voie de circulation vers les portes'
            emit(flight, landing + 2, 'blocked', summary['reason'])
            totals['blocked'] += 1
            continue
        if strategy == 'baseline':
            stand_time, distance, gate, taxi_min, taxi_in = min(gate_options, key=lambda o: o[2])
        else:
            stand_time, distance, gate, taxi_min, taxi_in = min(gate_options,
                    key=lambda o: (o[0] + o[1] / 500, o[0], o[1], o[2]))
        taxi_actual = reserve_slot(taxi_bookings, taxi_in, taxi_min, 1)
        if taxi_actual > landing + 2:
            totals['taxi_conflicts_avoided'] += 1
        stand_time = max(stand_time, taxi_actual + taxi_min)
        gate_free[gate] = stand_time + 1
        summary['gate'] = gate - 1
        totals['taxi_distance_m'] += distance
        emit(flight, taxi_actual, 'taxi_in', f'Roulage vers la porte {gate - 1}')
        emit(flight, stand_time, 'at_gate', f'Arrivée à la porte {gate - 1}')

        scheduled = task_lookup.get(flight.id)
        if scheduled:
            jobs = [(t.kind, t.duration_min, t.units) for t in scheduled]
            if not any(kind == 'tug' for kind, _, _ in jobs):
                jobs.append(('tug', 6, 1))
        else:
            jobs = DEFAULT_TASKS
        service_end = stand_time
        failed = False
        for kind, duration, units in [job for job in jobs if job[0] != 'tug']:
            options = []
            for vehicle in vehicles:
                if vehicle.kind != kind or not vehicle.available or vehicle.maintenance or vehicle.capacity_units < units:
                    continue
                state = vehicle_state[vehicle.id]
                route = usable_route(state['node'], gate, max(stand_time, state['free']), vehicle.speed_kmh)
                if route is None:
                    continue
                leave, metres = route
                fuel_needed = max(1, math.ceil(metres / 5000))
                if state['fuel'] < fuel_needed:
                    continue
                travel = math.ceil(metres * 60 / (vehicle.speed_kmh * 1000))
                begin = max(stand_time, leave + travel, state['free'] + travel)
                begin = after_vehicle_failure(vehicle.id, begin, duration)
                options.append((begin, metres, vehicle.cost_per_hour, vehicle.code, vehicle, fuel_needed))
            if not options:
                summary['reason'] = f'Aucun véhicule disponible pour : {kind}'
                emit(flight, service_end, 'blocked', summary['reason'])
                failed = True
                break
            if strategy == 'baseline':
                chosen = options[0]
            else:
                chosen = min(options, key=lambda o: (o[0] + o[1] / 1000 + o[2] / 30, o[0], o[1], o[3]))
            begin, metres, _, _, vehicle, fuel_needed = chosen
            finish = begin + duration
            state = vehicle_state[vehicle.id]
            state.update({'free': finish, 'node': gate, 'fuel': state['fuel'] - fuel_needed})
            service_end = max(service_end, finish)
            totals['vehicle_missions'] += 1
            totals['service_minutes'] += duration
            totals['vehicle_distance_m'] += metres
            totals['estimated_vehicle_cost'] += duration * vehicle.cost_per_hour / 60
            chosen_travel = math.ceil(metres * 60 / (vehicle.speed_kmh * 1000)) if metres > 0 else 0
            if chosen_travel > 0:
                emit(flight, max(0, begin - chosen_travel), 'vehicle_dispatch', f'Déplacement vers la porte {gate - 1}', vehicle.code)
            emit(flight, begin, 'service_start', f'{kind} — début', vehicle.code)
            emit(flight, finish, 'service_end', f'{kind} — terminé', vehicle.code)
            summary['operations'].append({'kind': kind, 'vehicle': vehicle.code, 'start': begin, 'end': finish})

        if not failed:
            duration = next((d for kind, d, _ in jobs if kind == 'tug'), 6)
            units = next((u for kind, _, u in jobs if kind == 'tug'), 1)
            options = []
            for vehicle in vehicles:
                if vehicle.kind != 'tug' or not vehicle.available or vehicle.maintenance or vehicle.capacity_units < units:
                    continue
                state = vehicle_state[vehicle.id]
                route = usable_route(state['node'], gate, max(service_end, state['free']), vehicle.speed_kmh)
                if route is None:
                    continue
                leave, metres = route
                fuel_needed = max(1, math.ceil(metres / 5000))
                if state['fuel'] < fuel_needed:
                    continue
                travel = max(1, math.ceil(metres * 60 / (vehicle.speed_kmh * 1000))) if metres > 0 else 0
                begin = max(service_end, leave + travel, state['free'] + travel)
                begin = after_vehicle_failure(vehicle.id, begin, duration)
                options.append((begin, metres, vehicle.cost_per_hour, vehicle.code, vehicle, fuel_needed))
            if options:
                if strategy == 'baseline':
                    begin, metres, _, _, vehicle, fuel_needed = options[0]
                else:
                    begin, metres, _, _, vehicle, fuel_needed = min(options,
                        key=lambda o: (o[0] + o[1] / 1000 + o[2] / 30, o[0], o[1], o[3]))
                finish = begin + duration
                state = vehicle_state[vehicle.id]
                state.update({'free': finish, 'node': gate, 'fuel': state['fuel'] - fuel_needed})
                totals['vehicle_missions'] += 1
                totals['service_minutes'] += duration
                totals['vehicle_distance_m'] += metres
                totals['estimated_vehicle_cost'] += duration * vehicle.cost_per_hour / 60
                if metres > 0:
                    trip = max(1, math.ceil(metres * 60 / (vehicle.speed_kmh * 1000)))
                    emit(flight, max(0, begin - trip), 'vehicle_dispatch', f'Déplacement vers la porte {gate - 1}', vehicle.code)
                emit(flight, begin, 'pushback', 'Repoussage depuis la porte', vehicle.code)
                summary['operations'].append({'kind': 'tug', 'vehicle': vehicle.code, 'start': begin, 'end': finish})
                route = usable_route(gate, 0, finish)
                if route is None:
                    summary['reason'] = 'Voie de circulation inaccessible au départ'
                    emit(flight, finish, 'blocked', summary['reason'])
                    failed = True
                else:
                    taxi_out_start, out_distance = route
                    out_min = max(1, math.ceil(out_distance / 500))
                    depart_taxi = reserve_slot(taxi_bookings, taxi_out_start, out_min, 1)
                    if depart_taxi > taxi_out_start:
                        totals['taxi_conflicts_avoided'] += 1
                    depart_request = depart_taxi + out_min
                    emit(flight, depart_taxi, 'taxi_out', f'Roulage vers la piste {runway.designation}')
                    takeoff = reserve_slot(reservations[runway.id], depart_request, 2, runway.separation_min)
                    if takeoff > depart_request:
                        totals['runway_conflicts_avoided'] += 1
                    summary['takeoff_minute'] = takeoff
                    summary['delay_min'] = max(0, takeoff - (flight.scheduled_minute + flight.duration_minutes + taxi_min * 2 + 8))
                    summary['status'] = 'completed'
                    totals['completed'] += 1
                    totals['total_delay_min'] += summary['delay_min']
                    totals['taxi_distance_m'] += out_distance
                    gate_free[gate] = max(gate_free[gate], finish + 1)
                    emit(flight, takeoff, 'takeoff', f'Décollage piste {runway.designation}')
            else:
                summary['reason'] = 'Aucun tracteur de repoussage disponible'
                emit(flight, service_end, 'blocked', summary['reason'])
                failed = True
        if failed:
            gate_free[gate] = max(gate_free[gate], 1440)
            totals['blocked'] += 1

    totals['applied_incidents'] = len(applied)
    totals['completion_rate_pct'] = round(100 * totals['completed'] / totals['flights'], 1) if totals['flights'] else 0
    totals['mean_delay_min'] = round(totals['total_delay_min'] / totals['completed'], 2) if totals['completed'] else 0
    totals['cost_per_completed_flight'] = round(totals['estimated_vehicle_cost'] / totals['completed'], 2) if totals['completed'] else 0
    totals['estimated_vehicle_cost'] = round(totals['estimated_vehicle_cost'], 2)
    timeline.sort(key=lambda item: (item['minute'], item['flight_number'], item['phase']))
    return {
        'kpis': totals, 'flights': results, 'timeline': timeline,
        'strategy': strategy,
        'note': 'Prévision pédagogique des opérations réordonnées à la minute.'
    }
