"""V0.6+V0.7 incident scheduling, optimization and persistent snapshots."""
from types import SimpleNamespace as NS
from uuid import uuid4

from fastapi.testclient import TestClient
from app.main import app
from app.operations.service import forecast


def sample_resources():
    flights = [NS(id='flight-a', flight_number='AA101', scheduled_minute=20,
                  duration_minutes=18, aircraft_id=None)]
    runways = [NS(id='rw-a', designation='09/27', length_m=3200,
                  separation_min=3, active=True)]
    edges = [NS(id=f'e{i}', start_node=a, end_node=b, distance_m=d, active=True)
             for i, (a, b, d) in enumerate([(0, 1, 400), (1, 2, 100)])]
    vehicle_specs = [('bag', 'baggage'), ('fuel', 'fuel'), ('clean', 'cleaning'),
                     ('catering', 'catering'), ('tug', 'tug')]
    vehicles = [NS(id=code, code=code.upper(), kind=kind, speed_kmh=30,
                   capacity_units=20, fuel_pct=100, available=True,
                   maintenance=False, home_node=1, cost_per_hour=40)
                for code, kind in vehicle_specs]
    return flights, {}, runways, edges, vehicles, []


def incident(kind, target, start, end, delay=0, enabled=True):
    return NS(id=f'{kind}-{target}-{start}-{end}', kind=kind, target_id=target,
              start_minute=start, end_minute=end,
              delay_minutes=delay, enabled=enabled)


def test_baseline_no_incident_remains_deterministic():
    args = sample_resources()
    a = forecast(*args, strategy='optimized')
    b = forecast(*args, strategy='optimized')
    assert a == b
    assert a['kpis']['completed'] == 1
    assert a['kpis']['configured_incidents'] == 0
    assert a['kpis']['completion_rate_pct'] == 100
    assert a['kpis']['mean_delay_min'] >= 0
    assert a['kpis']['cost_per_completed_flight'] > 0


def test_temporary_runway_closure_delays_landing():
    args = sample_resources()
    regular = forecast(*args)
    changed = forecast(*args, incidents=[incident('runway_closure', 'rw-a', 10, 70)])
    assert changed['flights'][0]['landing_minute'] >= 73
    assert changed['flights'][0]['landing_minute'] > regular['flights'][0]['landing_minute']
    assert changed['kpis']['applied_incidents'] == 1
    assert changed['kpis']['incident_delay_min'] > 0
    assert any(e['phase'] == 'disruption' for e in changed['timeline'])


def test_taxiway_closure_waits_and_recovers():
    args = sample_resources()
    result = forecast(*args, incidents=[incident('taxiway_closure', 'e0', 0, 95)])
    assert result['kpis']['completed'] == 1
    at_gate = next(e for e in result['timeline'] if e['phase'] == 'at_gate')
    assert at_gate['minute'] >= 95
    assert result['kpis']['applied_incidents'] == 1


def test_vehicle_failure_replans_to_after_outage():
    args = sample_resources()
    result = forecast(*args, incidents=[incident('vehicle_failure', 'fuel', 0, 110)])
    assert result['kpis']['completed'] == 1
    fuel_job = next(o for o in result['flights'][0]['operations'] if o['kind'] == 'fuel')
    assert fuel_job['start'] >= 110
    assert result['kpis']['applied_incidents'] == 1


def test_flight_delay_applied_and_disabled_ignored():
    args = sample_resources()
    active = incident('flight_delay', 'flight-a', 0, 100, delay=35)
    extra = incident('runway_closure', 'rw-a', 0, 100, enabled=False)
    out = forecast(*args, incidents=[active, extra])
    assert out['flights'][0]['landing_minute'] >= 55
    assert out['kpis']['incident_delay_min'] >= 35
    assert out['kpis']['configured_incidents'] == 1
    assert out['kpis']['applied_incidents'] == 1


def test_baseline_vs_optimized_runway_selection():
    args = list(sample_resources())
    args[2].append(NS(id='rw-b', designation='18/36', length_m=3200,
                      separation_min=2, active=True))
    closure = incident('runway_closure', 'rw-a', 0, 100)
    baseline = forecast(*args, incidents=[closure], strategy='baseline')
    optimized = forecast(*args, incidents=[closure], strategy='optimized')
    assert baseline['flights'][0]['runway'] == '09/27'
    assert optimized['flights'][0]['runway'] == '18/36'
    assert optimized['flights'][0]['landing_minute'] < baseline['flights'][0]['landing_minute']


def test_incident_api_validation_and_history_snapshot():
    with TestClient(app) as c:
        runway = c.get('/api/operations/runways').json()[0]
        before = c.get('/api/operations/forecast').json()
        payload = {'kind': 'runway_closure', 'target_id': runway['id'],
                   'start_minute': 0, 'end_minute': 140, 'description': 'Inspection périodique'}
        assert c.post('/api/operations/incidents', json={**payload, 'end_minute': 0}).status_code == 422
        assert c.post('/api/operations/incidents', json={**payload, 'target_id': 'missing'}).status_code == 404
        assert c.post('/api/operations/incidents', json={**payload, 'delay_minutes': 20}).status_code == 422
        created = c.post('/api/operations/incidents', json=payload)
        assert created.status_code == 201
        incident_id = created.json()['id']
        try:
            assert any(x['id'] == incident_id for x in c.get('/api/operations/incidents').json())
            after = c.get('/api/operations/forecast').json()
            assert after['kpis']['configured_incidents'] >= 1
            clean = c.get('/api/operations/forecast?use_incidents=false').json()
            assert clean['kpis']['configured_incidents'] == 0
            assert before['kpis']['flights'] == clean['kpis']['flights']
            compare = c.get('/api/operations/analytics/compare')
            assert compare.status_code == 200
            obj = compare.json()
            assert {'baseline', 'optimized', 'without_incidents', 'delta'} <= set(obj)
            assert obj['without_incidents']['kpis']['configured_incidents'] == 0
            assert c.post('/api/operations/analytics/history', json={'strategy': 'unknown'}).status_code == 422
            saved = c.post('/api/operations/analytics/history',
                           json={'strategy': 'optimized', 'label': 'Avant suppression'})
            assert saved.status_code == 201
            record = saved.json()
            assert record['incident_count'] >= 1
            assert record['result']['kpis']['configured_incidents'] >= 1
            assert any(x['id'] == record['id'] for x in c.get('/api/operations/analytics/history').json())
            assert c.patch('/api/operations/incidents/' + incident_id,
                           json={**payload, 'enabled': False}).status_code == 200
            new = c.get('/api/operations/forecast').json()
            assert new['kpis']['configured_incidents'] == 0
            assert record['result']['kpis']['configured_incidents'] >= 1
            assert c.delete('/api/operations/analytics/history/' + record['id']).status_code == 204
        finally:
            assert c.delete('/api/operations/incidents/' + incident_id).status_code == 204
        assert c.delete('/api/operations/incidents/' + incident_id).status_code == 404
        assert c.get('/api/operations/analytics/history?limit=0').status_code == 422


def test_planned_flight_delay_incident_target_is_validated():
    with TestClient(app) as c:
        payload = {'flight_number': 'I' + uuid4().hex[:7].upper(), 'airline':'Example',
                   'origin':'CDG', 'destination':'AMS', 'scheduled_minute':250,
                   'duration_minutes':18}
        new_flight = c.post('/api/flight-plans', json=payload)
        assert new_flight.status_code == 201
        fid = new_flight.json()['id']
        event = {'kind': 'flight_delay', 'target_id': fid,
                 'start_minute': 240, 'end_minute': 300, 'delay_minutes': 25}
        try:
            response = c.post('/api/operations/incidents', json=event)
            assert response.status_code == 201
            ident = response.json()['id']
            result = c.get('/api/operations/forecast').json()
            assert result['kpis']['incident_delay_min'] >= 25
            assert c.delete('/api/operations/incidents/' + ident).status_code == 204
        finally:
            assert c.delete('/api/flight-plans/' + fid).status_code == 204


def test_runway_slots_never_overlap_with_separation_under_contention():
    """Multiple simultaneous arrivals/departures obey the shared runway calendar."""
    args = list(sample_resources())
    args[0] = [NS(id=f'flight-{i}', flight_number=f'R{i:03}',
                  scheduled_minute=20, duration_minutes=20, aircraft_id=None)
               for i in range(7)]
    result = forecast(*args, strategy='optimized')
    intervals = sorted((event['minute'], event['minute'] + 2)
                       for event in result['timeline']
                       if event['phase'] in ('landing', 'takeoff'))
    assert len(intervals) >= 7
    assert all(end + 3 <= next_start for (_, end), (next_start, _) in
               zip(intervals, intervals[1:]))
    assert result['kpis']['runway_conflicts_avoided'] > 0
    assert result['kpis']['completed'] + result['kpis']['blocked'] == 7


def test_taxiway_closure_on_unrelated_link_does_not_delay_flight():
    args = list(sample_resources())
    args[3].append(NS(id='dead-end', start_node=5, end_node=6,
                      distance_m=120, active=True))
    normal = forecast(*args)
    closed = forecast(*args, incidents=[incident('taxiway_closure', 'dead-end', 0, 300)])
    assert closed['flights'] == normal['flights']
    assert closed['kpis']['applied_incidents'] == 0


def test_taxiway_closure_selects_detour_instead_of_waiting():
    args = list(sample_resources())
    args[3] = [
        NS(id='short-a', start_node=0, end_node=1, distance_m=100, active=True),
        NS(id='short-b', start_node=1, end_node=2, distance_m=100, active=True),
        NS(id='detour-a', start_node=0, end_node=3, distance_m=400, active=True),
        NS(id='detour-b', start_node=3, end_node=2, distance_m=400, active=True),
        NS(id='service', start_node=1, end_node=3, distance_m=300, active=True),
    ]
    normal = forecast(*args)
    result = forecast(*args, incidents=[incident('taxiway_closure', 'short-a', 0, 200)])
    assert result['kpis']['completed'] == 1
    assert result['flights'][0]['landing_minute'] == normal['flights'][0]['landing_minute']
    assert result['kpis']['taxi_distance_m'] > normal['kpis']['taxi_distance_m']
    assert result['kpis']['applied_incidents'] == 1


def test_multiple_vehicle_outages_respect_full_service_duration():
    args = sample_resources()
    outages = [incident('vehicle_failure', 'fuel', 17, 47),
               incident('vehicle_failure', 'fuel', 45, 95)]
    result = forecast(*args, incidents=outages)
    assert result['kpis']['completed'] == 1
    job = next(op for op in result['flights'][0]['operations'] if op['kind'] == 'fuel')
    assert job['start'] >= 95
    assert result['kpis']['applied_incidents'] == 2


def test_optimizer_picks_lower_cost_vehicle_for_equivalent_availability():
    args = list(sample_resources())
    costly = NS(id='bag-expensive', code='A-EXP', kind='baggage', speed_kmh=30,
                capacity_units=20, fuel_pct=100, available=True, maintenance=False,
                home_node=1, cost_per_hour=3600)
    cheap = NS(id='bag-affordable', code='Z-CHEAP', kind='baggage', speed_kmh=30,
               capacity_units=20, fuel_pct=100, available=True, maintenance=False,
               home_node=1, cost_per_hour=6)
    args[4] = [costly, cheap, *[v for v in args[4] if v.kind != 'baggage']]
    baseline = forecast(*args, strategy='baseline')
    optimized = forecast(*args, strategy='optimized')
    assert baseline['kpis']['completed'] == optimized['kpis']['completed'] == 1
    assert optimized['kpis']['estimated_vehicle_cost'] < baseline['kpis']['estimated_vehicle_cost']
    assert next(op for op in optimized['flights'][0]['operations'] if op['kind'] == 'baggage')['vehicle'] == 'Z-CHEAP'
    assert next(op for op in baseline['flights'][0]['operations'] if op['kind'] == 'baggage')['vehicle'] == 'A-EXP'


def test_forecast_is_pure_and_deterministic_with_active_incidents():
    import copy
    args = sample_resources()
    outages = [incident('runway_closure', 'rw-a', 25, 60),
               incident('vehicle_failure', 'tug', 45, 70)]
    before = copy.deepcopy((args, outages))
    first = forecast(*args, incidents=outages)
    second = forecast(*args, incidents=outages)
    assert first == second
    assert (args, outages) == before
    assert first['kpis']['flights'] == first['kpis']['completed'] + first['kpis']['blocked']
    assert first['kpis']['mean_delay_min'] == round(first['kpis']['total_delay_min'] / first['kpis']['completed'], 2)


def test_analytics_api_uses_identical_inputs_and_persists_immutable_snapshot():
    with TestClient(app) as client:
        runway = client.get('/api/operations/runways').json()[0]
        payload = {'kind': 'runway_closure', 'target_id': runway['id'],
                   'start_minute': 1, 'end_minute': 130, 'description': 'Contrôle opérationnel'}
        created = client.post('/api/operations/incidents', json=payload)
        assert created.status_code == 201
        identity = created.json()['id']
        try:
            results = client.get('/api/operations/analytics/compare').json()
            assert results['baseline']['kpis']['configured_incidents'] >= 1
            assert results['optimized']['kpis']['configured_incidents'] >= 1
            assert results['without_incidents']['kpis']['configured_incidents'] == 0
            for metric in results['delta']:
                actual = results['optimized']['kpis'][metric] - results['baseline']['kpis'][metric]
                assert results['delta'][metric] == round(actual, 2)
            saved = client.post('/api/operations/analytics/history', json={
                'label': 'Avant changement', 'strategy': 'optimized'})
            assert saved.status_code == 201
            original = saved.json()
            assert original['result'] == results['optimized']
            client.patch(f'/api/operations/incidents/{identity}', json={**payload, 'enabled': False})
            history = client.get('/api/operations/analytics/history').json()
            assert next(row for row in history if row['id'] == original['id'])['result'] == original['result']
            assert client.delete('/api/operations/analytics/history/'+original['id']).status_code == 204
        finally:
            assert client.delete('/api/operations/incidents/'+identity).status_code == 204


def test_invalid_incident_payloads_do_not_persist():
    with TestClient(app) as client:
        resource = client.get('/api/operations/runways').json()[0]
        before = {row['id'] for row in client.get('/api/operations/incidents').json()}
        basic = {'kind': 'runway_closure', 'target_id': resource['id'],
                 'start_minute': 30, 'end_minute': 90}
        bad = [
            {**basic, 'kind': 'unrecognized'},
            {**basic, 'start_minute': 90},
            {**basic, 'start_minute': -1},
            {**basic, 'end_minute': 1500},
            {**basic, 'delay_minutes': 20},
            {**basic, 'target_id': 'missing'},
            {**basic, 'start_minute': 90, 'end_minute': 30},
        ]
        for item in bad:
            response = client.post('/api/operations/incidents', json=item)
            assert response.status_code in (404, 422), item
        after = {row['id'] for row in client.get('/api/operations/incidents').json()}
        assert after == before


def test_runway_calendar_fuzzed_requests_preserve_interval_invariant():
    """Stress real slot reservations with unsorted arrival order and variable gaps."""
    import random
    from app.operations.service import reserve_slot
    randomizer = random.Random(2077)
    for _ in range(15):
        booked = []
        separation = randomizer.randint(1, 5)
        for _ in range(65):
            requested = randomizer.randint(0, 500)
            duration = randomizer.randint(1, 7)
            actual = reserve_slot(booked, requested, duration, separation)
            assert actual >= requested
        for (_, end), (next_start, _) in zip(sorted(booked), sorted(booked)[1:]):
            assert next_start >= end + separation


def test_route_utility_chooses_shortest_active_path_and_respects_closed_links():
    """Cycle plus dead-end: closed shortcut must result in a valid longer detour."""
    from app.operations.service import shortest_path
    edges = [
        NS(start_node=0, end_node=1, distance_m=5, active=True),
        NS(start_node=1, end_node=2, distance_m=10, active=True),
        NS(start_node=0, end_node=3, distance_m=9, active=True),
        NS(start_node=3, end_node=2, distance_m=10, active=True),
        NS(start_node=1, end_node=3, distance_m=5, active=True),
        NS(start_node=4, end_node=5, distance_m=1, active=True),
    ]
    assert shortest_path(edges, 0, 2) == 15
    edges[1].active = False
    assert shortest_path(edges, 0, 2) == 19
    assert shortest_path(edges, 0, 5) is None
    assert shortest_path(edges, 0, 0) == 0


def test_incident_references_prevent_deleting_target_resources():
    """Protect long-lived forecast inputs from silently orphaning incidents."""
    with TestClient(app) as client:
        code = 'RW' + uuid4().hex[:6].upper()
        resource = client.post('/api/operations/runways', json={
            'designation': code, 'length_m': 3000, 'separation_min': 3})
        assert resource.status_code == 201
        runway_id = resource.json()['id']
        inc = client.post('/api/operations/incidents', json={
            'kind': 'runway_closure', 'target_id': runway_id,
            'start_minute': 20, 'end_minute': 80})
        assert inc.status_code == 201
        ident = inc.json()['id']
        try:
            assert client.delete('/api/operations/runways/'+runway_id).status_code == 409
            assert any(r['id'] == runway_id for r in client.get('/api/operations/runways').json())
            assert client.patch('/api/operations/incidents/'+ident, json={
                'kind': 'runway_closure', 'target_id': runway_id,
                'start_minute': 20, 'end_minute': 80, 'enabled': False}).status_code == 200
            assert client.delete('/api/operations/runways/'+runway_id).status_code == 409
        finally:
            assert client.delete('/api/operations/incidents/'+ident).status_code == 204
            assert client.delete('/api/operations/runways/'+runway_id).status_code == 204


def test_flight_with_delay_incident_cannot_be_removed_until_incident_deleted():
    with TestClient(app) as client:
        number = 'T' + uuid4().hex[:8].upper()
        created = client.post('/api/flight-plans', json={
            'flight_number': number, 'airline': 'Example', 'origin': 'CDG',
            'destination': 'AMS', 'scheduled_minute': 250, 'duration_minutes': 30})
        assert created.status_code == 201
        flight_id = created.json()['id']
        inc = client.post('/api/operations/incidents', json={
            'kind': 'flight_delay', 'target_id': flight_id,
            'start_minute': 200, 'end_minute': 300, 'delay_minutes': 30})
        assert inc.status_code == 201
        try:
            assert client.delete('/api/flight-plans/'+flight_id).status_code == 409
            assert any(f['id'] == flight_id for f in client.get('/api/flight-plans').json())
        finally:
            assert client.delete('/api/operations/incidents/'+inc.json()['id']).status_code == 204
            assert client.delete('/api/flight-plans/'+flight_id).status_code == 204
