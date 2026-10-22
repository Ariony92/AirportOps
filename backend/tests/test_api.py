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
