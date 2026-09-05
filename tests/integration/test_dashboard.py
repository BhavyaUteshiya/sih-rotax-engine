from fastapi.testclient import TestClient
from app.server import app

client = TestClient(app)

def test_dashboard_home():
    r = client.get('/')
    assert r.status_code == 200
    assert 'ROTAX 914' in r.text

def test_dashboard_state_and_step():
    assert client.get('/api/state').status_code == 200
    r = client.post('/api/controls', json={
        'throttle_1': 50, 'throttle_2': 25, 'starter_1': True, 'starter_2': True,
        'altitude_m': 3000, 'temp_offset_c': 10, 'humidity_pct': 40,
        'wind_m_s': 0, 'flight_path_angle_deg': 2
    })
    assert r.status_code == 200
    r = client.post('/api/run')
    assert r.status_code == 200
    data = r.json()
    assert data['environment']['altitude_m'] == 3000
    assert data['environment']['humidity_pct'] == 40
    assert data['engines']['1']['throttle_pct'] == 50
