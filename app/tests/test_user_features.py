import sys
import os
import pytest
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
from app import main
from app.db.db_executor import get_db_connection

@pytest.fixture(autouse=True)
def clean_db():
    conn = get_db_connection()
    conn.execute('DELETE FROM user_watchlist')
    conn.execute('DELETE FROM users')
    conn.commit()
    conn.close()

@pytest.fixture
def client():
    main.app.config['TESTING'] = True
    with main.app.test_client() as client:
        yield client

def test_register(client):
    response = client.post('/api/register', json={
        'username': 'testuser',
        'email': 'testuser@example.com',
        'password': 'testpass123'
    })
    assert response.status_code == 201
    assert b'User registered successfully' in response.data

def test_login(client):
    client.post('/api/register', json={
        'username': 'testuser2',
        'email': 'testuser2@example.com',
        'password': 'testpass123'
    })
    response = client.post('/api/login', json={
        'username': 'testuser2',
        'password': 'testpass123'
    })
    assert response.status_code == 200
    assert b'Login successful' in response.data

def test_watchlist(client):
    client.post('/api/register', json={
        'username': 'testuser3',
        'email': 'testuser3@example.com',
        'password': 'testpass123'
    })
    client.post('/api/login', json={
        'username': 'testuser3',
        'password': 'testpass123'
    })
    response = client.post('/api/watchlist', json={'security_id': 'ABB.BO'})
    assert response.status_code == 201
    response = client.get('/api/watchlist')
    assert response.status_code == 200
    assert 'ABB.BO' in response.get_json()['watchlist']
    response = client.delete('/api/watchlist', json={'security_id': 'ABB.BO'})
    assert response.status_code == 200
    assert b'Stock removed from watchlist' in response.data
