import os
import tempfile
os.environ['DATABASE_URL']='sqlite:///'+os.path.join(tempfile.gettempdir(),'airportops_test_api_'+__import__('uuid').uuid4().hex+'.sqlite')
from fastapi.testclient import TestClient
from app.main import app,Base,engine
Base.metadata.create_all(engine)
client=TestClient(app)
def test_health():assert client.get('/health').json()=={'status':'ok'}
def test_scenario():
    response=client.post('/api/scenarios',json={'name':'Test','delay':30})
    assert response.status_code==201
    sid=response.json()['id']
    assert client.get(f'/api/scenarios/{sid}').status_code==200
    saved=client.post(f'/api/scenarios/{sid}/runs',json={'strategy':'optimized','finished':10,'total_delay':30,'conflicts':0,'vehicle_missions':10})
    assert saved.status_code==201
    assert len(client.get(f'/api/scenarios/{sid}/runs').json())==1
    assert client.delete(f'/api/scenarios/{sid}').status_code==204

def test_airports_and_validation():
    airport=client.post('/api/airports',json={'name':'Demo Airport','code':'DEM','layout':{'stands':5}})
    assert airport.status_code==201
    assert client.post('/api/airports',json={'name':'Other','code':'DEM'}).status_code==409
    assert client.post('/api/scenarios',json={'name':'Invalid','delay':500}).status_code==422

def test_scenario_duplication_and_comparison():
    r=client.post('/api/scenarios',json={'name':'Compare','delay':5})
    sid=r.json()['id']
    duplicate=client.post(f'/api/scenarios/{sid}/duplicate')
    assert duplicate.status_code==201
    assert duplicate.json()['name']=='Compare (copie)'
    first=client.post(f'/api/scenarios/{sid}/runs',json={'strategy':'baseline','finished':10,'total_delay':100,'conflicts':4,'vehicle_missions':10}).json()
    second=client.post(f'/api/scenarios/{sid}/runs',json={'strategy':'optimized','finished':10,'total_delay':70,'conflicts':2,'vehicle_missions':10}).json()
    result=client.post('/api/comparisons',json={'baseline_run_id':first['id'],'optimized_run_id':second['id']})
    assert result.status_code==200
    assert result.json()['delta']['total_delay']==-30
    assert client.get('/api/audit').status_code==200
    assert client.patch(f'/api/scenarios/{sid}',json={'name':'New','delay':10}).json()['name']=='New'
    assert client.delete(f'/api/scenarios/{sid}').status_code==204


def test_flight_plan_crud_and_validation():
    base = {'flight_number':'AO123', 'airline':'AirportOps', 'origin':'CDG',
            'destination':'AMS', 'scheduled_minute':25, 'duration_minutes':20}
    bad = {**base, 'origin':'ZZ'}
    assert client.post('/api/flight-plans', json=bad).status_code == 422
    created = client.post('/api/flight-plans', json=base)
    assert created.status_code == 201
    fid = created.json()['id']
    assert client.post('/api/flight-plans', json=base).status_code == 409
    assert client.patch(f'/api/flight-plans/{fid}', json={}).status_code == 422
    assert client.patch(f'/api/flight-plans/{fid}', json={'scheduled_minute':50}).json()['scheduled_minute'] == 50
    assert any(item['id'] == fid for item in client.get('/api/flight-plans').json())
    assert client.delete(f'/api/flight-plans/{fid}').status_code == 204
    assert client.delete(f'/api/flight-plans/{fid}').status_code == 404


def test_flight_plan_capacity_and_sort():
    for i in range(10):
        r=client.post('/api/flight-plans',json={'flight_number':f'AX{i:03}', 'airline':'Example',
                'origin':'ORY','destination':'LHR', 'scheduled_minute':100-i, 'duration_minutes':15})
        assert r.status_code == 201
    data=client.get('/api/flight-plans').json()
    assert [x['scheduled_minute'] for x in data] == sorted(x['scheduled_minute'] for x in data)
    assert client.post('/api/flight-plans',json={'flight_number':'AX999','airline':'Example',
                'origin':'ORY','destination':'LHR','scheduled_minute':200,'duration_minutes':15}).status_code==409
    for item in data:
        assert client.delete('/api/flight-plans/'+item['id']).status_code == 204


def aircraft_payload(registration='F-AO01'):
    return {'registration': registration, 'airline': 'AirportOps Airlines',
            'manufacturer': 'Airbus', 'model': 'A320neo',
            'category': 'narrow_body', 'seats': 180}


def flight_payload(number, minute, aircraft_id=None, duration=30):
    return {'flight_number': number, 'airline': 'AirportOps Airlines',
            'origin': 'CDG', 'destination': 'AMS',
            'scheduled_minute': minute, 'duration_minutes': duration,
            'aircraft_id': aircraft_id}


def test_aircraft_crud_and_validation():
    invalid = client.post('/api/aircraft', json={**aircraft_payload(), 'seats': 0})
    assert invalid.status_code == 422
    result = client.post('/api/aircraft', json=aircraft_payload())
    assert result.status_code == 201
    aircraft_id = result.json()['id']
    assert client.get('/api/aircraft/'+aircraft_id).json()['registration'] == 'F-AO01'
    assert client.post('/api/aircraft', json=aircraft_payload()).status_code == 409
    assert client.patch('/api/aircraft/'+aircraft_id, json={}).status_code == 422
    updated = client.patch('/api/aircraft/'+aircraft_id,
                           json={'model': 'A321', 'seats': 220})
    assert updated.status_code == 200
    assert updated.json()['seats'] == 220
    assert any(x['id'] == aircraft_id for x in client.get('/api/aircraft').json())
    assert client.delete('/api/aircraft/'+aircraft_id).status_code == 204
    assert client.get('/api/aircraft/'+aircraft_id).status_code == 404


def test_aircraft_assignment_and_overlap():
    aircraft_id = client.post('/api/aircraft', json=aircraft_payload('F-AO02')).json()['id']
    a = client.post('/api/flight-plans', json=flight_payload('FA100', 120, aircraft_id))
    assert a.status_code == 201
    first_id = a.json()['id']
    assert a.json()['aircraft_id'] == aircraft_id
    assert client.post('/api/flight-plans',
                       json=flight_payload('FA101', 130, aircraft_id)).status_code == 409
    b = client.post('/api/flight-plans', json=flight_payload('FA102', 150, aircraft_id))
    assert b.status_code == 201
    second_id = b.json()['id']
    assert client.patch(f'/api/flight-plans/{second_id}',
                        json={'scheduled_minute': 140}).status_code == 409
    assert client.delete('/api/aircraft/'+aircraft_id).status_code == 409
    assert client.patch(f'/api/flight-plans/{first_id}', json={'aircraft_id': None}).status_code == 200
    assert client.patch(f'/api/flight-plans/{first_id}', json={'aircraft_id': None}).json()['aircraft_id'] is None
    assert client.patch(f'/api/flight-plans/{first_id}',
                        json={'aircraft_id': 'not-an-id'}).status_code == 404
    assert client.delete(f'/api/flight-plans/{first_id}').status_code == 204
    assert client.delete(f'/api/flight-plans/{second_id}').status_code == 204
    assert client.delete('/api/aircraft/'+aircraft_id).status_code == 204


def test_aircraft_delete_protection_and_assignment_change():
    first_aircraft = client.post('/api/aircraft', json=aircraft_payload('F-AO03')).json()['id']
    second_aircraft = client.post('/api/aircraft', json=aircraft_payload('F-AO04')).json()['id']
    created = client.post('/api/flight-plans', json=flight_payload('FA103', 45))
    assert created.status_code == 201
    fid = created.json()['id']
    assert created.json()['aircraft_id'] is None
    r = client.patch('/api/flight-plans/'+fid, json={'aircraft_id': first_aircraft})
    assert r.status_code == 200 and r.json()['aircraft_id'] == first_aircraft
    assert client.delete('/api/aircraft/'+first_aircraft).status_code == 409
    assert client.patch('/api/flight-plans/'+fid, json={'aircraft_id': second_aircraft}).status_code == 200
    assert client.delete('/api/aircraft/'+first_aircraft).status_code == 204
    assert client.delete('/api/flight-plans/'+fid).status_code == 204
    assert client.delete('/api/aircraft/'+second_aircraft).status_code == 204


def test_aircraft_registration_collision_on_update():
    first = client.post('/api/aircraft', json=aircraft_payload('F-AO05')).json()['id']
    second = client.post('/api/aircraft', json=aircraft_payload('F-AO06')).json()['id']
    assert client.patch('/api/aircraft/'+second, json={'registration': 'F-AO05'}).status_code == 409
    assert client.get('/api/aircraft/'+second).json()['registration'] == 'F-AO06'
    assert client.delete('/api/aircraft/'+first).status_code == 204
    assert client.delete('/api/aircraft/'+second).status_code == 204
