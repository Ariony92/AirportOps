"""V0.5 integration coverage: persistent infrastructure, scheduling and catalogs."""
from fastapi.testclient import TestClient
from app.main import app, Base, engine
from app.operations.service import shortest_path, reserve_slot
from types import SimpleNamespace
from uuid import uuid4

Base.metadata.create_all(engine)

def runways(c):
    return c.get('/api/operations/runways').json()


def test_demo_and_catalog():
    with TestClient(app) as c:
        assert c.get('/health').status_code == 200
        assert len(runways(c)) >= 1
        assert len(c.get('/api/operations/taxiways').json()) >= 6
        assert len(c.get('/api/operations/vehicles').json()) >= 6
        airline = c.get('/api/catalog/airlines').json()
        assert len(airline['airlines']) == 10
        assert airline['airlines'][0] == 'Singapore Airlines'
        catalog = c.get('/api/catalog/aircraft-models').json()
        assert len(catalog['models']) >= 150
        assert any(item['model'] == 'A320neo' for item in catalog['models'])
        assert catalog['free_entry_allowed'] is True


def test_runway_crud_and_validation():
    with TestClient(app) as c:
        code = 'R' + uuid4().hex[:7].upper()
        bad = c.post('/api/operations/runways', json={'designation': code, 'length_m': 100})
        assert bad.status_code == 422
        first = c.post('/api/operations/runways', json={'designation': code, 'length_m': 2100, 'separation_min': 3})
        assert first.status_code == 201
        rid = first.json()['id']
        assert c.post('/api/operations/runways', json={'designation': code, 'length_m': 2100}).status_code == 409
        assert c.patch('/api/operations/runways/'+rid, json={'active': False}).json()['active'] is False
        assert c.patch('/api/operations/runways/'+rid, json={}).status_code == 422
        assert c.delete('/api/operations/runways/'+rid).status_code == 204
        assert c.delete('/api/operations/runways/'+rid).status_code == 404


def test_vehicle_crud_and_validation():
    with TestClient(app) as c:
        code = 'TEST-' + uuid4().hex[:8].upper()
        item = {'code': code, 'kind': 'baggage', 'speed_kmh': 33, 'capacity_units': 7, 'fuel_pct': 15, 'cost_per_hour': 25}
        assert c.post('/api/operations/vehicles', json={**item, 'fuel_pct': 200}).status_code == 422
        response = c.post('/api/operations/vehicles', json=item)
        assert response.status_code == 201
        vid = response.json()['id']
        assert c.post('/api/operations/vehicles', json=item).status_code == 409
        assert c.patch('/api/operations/vehicles/'+vid, json={'maintenance': True}).json()['maintenance'] is True
        assert c.patch('/api/operations/vehicles/'+vid, json={'speed_kmh': 0}).status_code == 422
        assert c.patch('/api/operations/vehicles/'+vid, json={}).status_code == 422
        assert c.delete('/api/operations/vehicles/'+vid).status_code == 204


def test_taxiway_crud_and_pathfinding():
    with TestClient(app) as c:
        current = c.get('/api/operations/taxiways').json()
        assert shortest_path([SimpleNamespace(**row) for row in current], 0, 6) is not None
        payload = {'start_node': 2, 'end_node': 5, 'distance_m': 201}
        created = c.post('/api/operations/taxiways', json=payload)
        assert created.status_code == 201
        tid = created.json()['id']
        assert c.post('/api/operations/taxiways', json={**payload, 'start_node': 5, 'end_node': 2}).status_code == 409
        assert c.patch('/api/operations/taxiways/'+tid, json={'distance_m': 130}).json()['distance_m'] == 130
        assert c.patch('/api/operations/taxiways/'+tid, json={'active': False}).status_code == 200
        assert c.delete('/api/operations/taxiways/'+tid).status_code == 204
        assert c.post('/api/operations/taxiways', json={'start_node': 1, 'end_node': 1, 'distance_m': 1}).status_code == 422
    empty = [SimpleNamespace(start_node=0,end_node=1,distance_m=20,active=False)]
    assert shortest_path(empty, 0, 1) is None
    slots = [(20,22), (50,52)]
    assert reserve_slot(slots, 24, 2, 3) == 25
    assert reserve_slot(slots, 45, 2, 3) == 45


def test_tasks_and_forecast():
    with TestClient(app) as c:
        num = 'GT' + uuid4().hex[:6].upper()
        aircraft = c.post('/api/aircraft', json={
            'registration':'X'+uuid4().hex[:9].upper(), 'airline':'Example', 'manufacturer':'Airbus',
            'model':'A320neo','category':'narrow_body','seats':180}).json()
        flight = c.post('/api/flight-plans', json={'flight_number':num,'airline':'Example','origin':'CDG','destination':'AMS',
            'scheduled_minute':310,'duration_minutes':45,'aircraft_id':aircraft['id']})
        assert flight.status_code == 201
        fid = flight.json()['id']
        assert c.post('/api/operations/tasks', json={'flight_plan_id':'bad', 'kind':'fuel', 'duration_min':5}).status_code == 404
        task = c.post('/api/operations/tasks', json={'flight_plan_id':fid,'kind':'baggage','duration_min':12,'units':2})
        assert task.status_code == 201
        tid = task.json()['id']
        assert c.patch('/api/operations/tasks/'+tid, json={'duration_min':14}).json()['duration_min'] == 14
        assert any(x['id'] == tid for x in c.get('/api/operations/tasks?flight_plan_id='+fid).json())
        result = c.get('/api/operations/forecast').json()
        expected = next(x for x in result['flights'] if x['flight_number'] == num)
        assert expected['status'] == 'completed'
        assert expected['landing_minute'] is not None and expected['takeoff_minute'] > expected['landing_minute']
        assert 'takeoff' in {e['phase'] for e in result['timeline'] if e['flight_number'] == num}
        assert result['kpis']['completed'] > 0
        assert result['kpis']['vehicle_missions'] > 0
        assert c.delete('/api/flight-plans/'+fid).status_code == 204
        assert not c.get('/api/operations/tasks?flight_plan_id='+fid).json()
        assert c.delete('/api/aircraft/'+aircraft['id']).status_code == 204


def test_forecast_blocking_when_no_eligible_runway():
    with TestClient(app) as c:
        existing = runways(c)
        old = [(r['id'], r['active']) for r in existing]
        try:
            for rid, _ in old:
                assert c.patch('/api/operations/runways/'+rid, json={'active': False}).status_code == 200
            result = c.get('/api/operations/forecast').json()
            assert result['kpis']['completed'] == 0
            assert result['kpis']['blocked'] == result['kpis']['flights']
        finally:
            for rid, old_status in old:
                c.patch('/api/operations/runways/'+rid, json={'active': old_status})


def test_forecast_resource_constraints_and_disconnected_graph():
    from app.operations.service import forecast
    flight = SimpleNamespace(id='f01', flight_number='CM001', scheduled_minute=25,
                             duration_minutes=30, aircraft_id='plane-1')
    airplane = SimpleNamespace(category='wide_body', registration='F-TEST')
    short = SimpleNamespace(id='runway', designation='18/36', length_m=1500, separation_min=3, active=True)
    full = SimpleNamespace(id='runway', designation='18/36', length_m=3200, separation_min=3, active=True)
    edges = [SimpleNamespace(start_node=a,end_node=b,distance_m=d,active=True) for a,b,d in [(0,1,100),(1,2,100)]]
    bag = SimpleNamespace(id='bag',code='B-1', kind='baggage', speed_kmh=30,
                          capacity_units=1, fuel_pct=100, available=True,
                          maintenance=False, home_node=1, cost_per_hour=40)
    tug = SimpleNamespace(id='tug',code='T-1', kind='tug', speed_kmh=30,
                          capacity_units=2, fuel_pct=100, available=True,
                          maintenance=False, home_node=1, cost_per_hour=40)
    jobs = [SimpleNamespace(flight_plan_id='f01', kind='baggage',duration_min=12,units=2)]
    assert forecast([flight], {'plane-1': airplane}, [short], edges, [bag,tug], jobs)['kpis']['blocked'] == 1
    assert 'piste' in forecast([flight], {'plane-1': airplane}, [short], edges, [bag,tug], jobs)['flights'][0]['reason'].lower()
    assert forecast([flight], {'plane-1': airplane}, [full], edges, [bag,tug], jobs)['kpis']['blocked'] == 1
    assert forecast([flight], {'plane-1': airplane}, [full], [], [bag,tug], jobs)['kpis']['blocked'] == 1
    bag.capacity_units = 5
    assert forecast([flight], {'plane-1': airplane}, [full], edges, [bag,tug], jobs)['kpis']['completed'] == 1
    bag.maintenance = True
    assert forecast([flight], {'plane-1': airplane}, [full], edges, [bag,tug], jobs)['kpis']['completed'] == 0
    bag.maintenance = False
    bag.fuel_pct = 0
    assert forecast([flight], {'plane-1': airplane}, [full], edges, [bag,tug], jobs)['kpis']['blocked'] == 1
