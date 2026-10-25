"""Public API contract, server-side replay and input validation regression."""
import os
import tempfile
import uuid
os.environ['DATABASE_URL'] = 'sqlite:///' + os.path.join(tempfile.gettempdir(), 'airportops_playback_' + uuid.uuid4().hex + '.sqlite')
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from app.db import Base, engine
from app.main import app
from app.operations.playback import project_playback
from app.operations.router import initialize_demo_infrastructure

Base.metadata.create_all(engine)
with Session(engine) as db:
    initialize_demo_infrastructure(db)

client = TestClient(app)


def test_server_replay_coherent_with_forecast():
    forecast = client.get('/api/operations/forecast').json()
    playback = client.get('/api/operations/playback').json()
    assert playback['kpis'] == forecast['kpis']
    assert playback['timeline'] == forecast['timeline']
    assert playback['duration_minutes'] > 0
    assert all(t['keyframes'] == sorted(t['keyframes'], key=lambda k: k['minute']) for t in playback['tracks'])
    assert sum(t['kind'] == 'aircraft' for t in playback['tracks']) == len(forecast['flights'])
    assert any(t['kind'] == 'vehicle' for t in playback['tracks'])
    for track in (t for t in playback['tracks'] if t['kind'] == 'vehicle'):
        motion_starts = [x for x in track['keyframes'] if x['phase'] == 'dispatch']
        # The backend schedules vehicles only when a mission dispatch was emitted.
        assert len(motion_starts) <= len([e for e in forecast['timeline'] if e['vehicle'] == track['id'] and e['phase'] == 'vehicle_dispatch'])


def test_replay_does_not_mutate_planning():
    before = client.get('/api/flight-plans').json()
    one = client.get('/api/operations/playback').json()
    two = client.get('/api/operations/playback').json()
    assert one == two
    assert client.get('/api/flight-plans').json() == before


def test_invalid_strategy_is_rejected():
    assert client.get('/api/operations/playback?strategy=invalid').status_code == 422


def test_scenario_run_is_computed_by_server():
    item = client.post('/api/scenarios', json={'name':'Server generated'}).json()
    result = client.post('/api/scenarios/'+item['id']+'/generate',json={'strategy':'optimized'})
    assert result.status_code == 201
    body = result.json()
    assert body['result']['kpis']['flights'] == 10
    assert body['result']['strategy'] == 'optimized'
    assert len(client.get('/api/scenarios/'+item['id']+'/runs').json()) == 1
    assert client.delete('/api/scenarios/'+item['id']).status_code == 204


def test_public_api_does_not_require_a_login():
    assert client.get('/api/operations/playback').status_code == 200
    assert client.get('/api/flight-plans').status_code == 200
    assert client.get('/api/auth/login').status_code == 404
    assert client.get('/api/auth/status').status_code == 404


def test_public_scenario_workflow():
    created = client.post('/api/scenarios', json={'name': 'Public demonstration'})
    assert created.status_code == 201
    identity = created.json()['id']
    try:
        computed = client.post('/api/scenarios/' + identity + '/generate', json={'strategy': 'baseline'})
        assert computed.status_code == 201
        assert computed.json()['result']['kpis']['flights'] == 10
    finally:
        assert client.delete('/api/scenarios/' + identity).status_code == 204


def test_comparison_gains_are_business_calculations_in_backend():
    response = client.get('/api/operations/analytics/compare')
    assert response.status_code == 200
    data = response.json()
    assert data['gains']['delaySavedMinutes'] == data['baseline']['kpis']['total_delay_min'] - data['optimized']['kpis']['total_delay_min']
    assert data['gains']['costSavedEuros'] == round(data['baseline']['kpis']['estimated_vehicle_cost'] - data['optimized']['kpis']['estimated_vehicle_cost'],2)


def test_scenario_settings_affect_the_planned_events_without_mutating_global_data():
    baseline = client.get('/api/operations/forecast').json()
    a = client.post('/api/scenarios', json={
        'name': 'Sans perturbation', 'delay': 0, 'breakdown': False, 'seed': 42}).json()
    b = client.post('/api/scenarios', json={
        'name': 'Retard déterministe', 'delay': 90, 'breakdown': False, 'seed': 42}).json()
    try:
        first = client.post(f"/api/scenarios/{a['id']}/generate", json={'strategy': 'optimized'})
        second = client.post(f"/api/scenarios/{b['id']}/generate", json={'strategy': 'optimized'})
        assert first.status_code == second.status_code == 201
        normal = first.json()['result']
        delayed = second.json()['result']
        assert normal['scenario_inputs']['delayed_flight'] is None
        assert delayed['scenario_inputs']['delay_minutes'] == 90
        assert delayed['scenario_inputs']['delayed_flight'] is not None
        assert delayed['kpis']['incident_delay_min'] >= normal['kpis']['incident_delay_min'] + 90
        assert any(e['phase'] == 'disruption' and '90' in e['details'] for e in delayed['timeline'])
        repeated = client.post(f"/api/scenarios/{b['id']}/generate", json={'strategy': 'optimized'}).json()['result']
        assert repeated == delayed
        assert client.get('/api/operations/forecast').json() == baseline
    finally:
        client.delete(f"/api/scenarios/{a['id']}")
        client.delete(f"/api/scenarios/{b['id']}")


def test_breakdown_and_seed_have_a_traceable_scenario_effect():
    obj = client.post('/api/scenarios', json={
        'name': 'Panne', 'delay': 0, 'breakdown': True, 'seed': 17}).json()
    try:
        run = client.post(f"/api/scenarios/{obj['id']}/generate", json={'strategy': 'optimized'})
        assert run.status_code == 201
        data = run.json()['result']
        assert data['scenario_inputs']['breakdown_enabled'] is True
        assert data['scenario_inputs']['seed'] == 17
        assert data['scenario_inputs']['failed_vehicle'] is not None
        assert data['scenario_inputs']['failure_window_minutes'] == [0, 240]
        assert data['kpis']['configured_incidents'] >= 1
        assert data['kpis']['applied_incidents'] >= 1
        updated = client.patch(f"/api/scenarios/{obj['id']}", json={
            'name': 'Panne', 'delay': 0, 'breakdown': False, 'seed': 17})
        assert updated.status_code == 200
        no_failure = client.post(f"/api/scenarios/{obj['id']}/generate", json={'strategy': 'optimized'})
        assert no_failure.status_code == 201
        assert no_failure.json()['result']['scenario_inputs']['failed_vehicle'] is None
        assert no_failure.json()['result']['kpis'] != data['kpis']
    finally:
        client.delete(f"/api/scenarios/{obj['id']}")
