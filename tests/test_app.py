# test_app.py
import pytest
from app import app
from fire_monitoring.app.database import SessionLocal, Base, engine
from models import User

@pytest.fixture
def client():
    app.config['TESTING'] = True
    with app.test_client() as client:
        with SessionLocal() as db:
            Base.metadata.create_all(bind=engine)
            yield client
            Base.metadata.drop_all(bind=engine)

def test_login(client):
    # Создаем тестового пользователя
    with SessionLocal() as db:
        user = User(username='testuser', role='admin')
        user.set_password('Test1234')
        db.add(user)
        db.commit()

    response = client.post('/login', data={'username': 'testuser', 'password': 'Test1234'})
    assert response.status_code == 200
    assert response.json['success'] == True
    assert 'token' in response.headers.get('Set-Cookie')

def test_access_denied(client):
    response = client.get('/api/logs')  # Без токена
    assert response.status_code == 401