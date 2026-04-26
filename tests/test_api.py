import pytest
from app import create_app
from app.extensions import db

@pytest.fixture
def client():
    app = create_app('testing')
    with app.test_client() as client:
        with app.app_context():
            db.create_all()
        yield client
        with app.app_context():
            db.session.remove()
            db.drop_all()

def test_health_check(client):
    rv = client.get('/health')
    assert rv.status_code == 200
    assert rv.json['status'] == 'ok'

def test_registration_and_login(client):
    # Register
    rv = client.post('/api/auth/register', json={
        'email': 'student@example.com',
        'name': 'Student',
        'password': 'password123'
    })
    assert rv.status_code == 201

    # Login
    rv = client.post('/api/auth/login', json={
        'email': 'student@example.com',
        'password': 'password123'
    })
    assert rv.status_code == 200
    assert 'access_token' in rv.json

def test_courses_list(client):
    rv = client.get('/api/courses/')
    assert rv.status_code == 200
    assert type(rv.json) == list
