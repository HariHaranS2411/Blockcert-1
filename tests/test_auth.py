import pytest
from app import create_app
from app.extensions import db
from app.models.user import User
from app.models.student import Student


@pytest.fixture
def client():
    app = create_app('testing')
    with app.test_client() as client:
        with app.app_context():
            db.create_all()
            yield client
            db.session.remove()
            db.drop_all()


def test_signup_student(client):
    res = client.post('/auth/signup', data={
        'name': 'Test Student',
        'email': 'student@example.com',
        'role': 'student',
        'roll_number': 'STU-001',
        'degree': 'B.Tech',
        'department': 'CS',
        'graduation_year': 2025,
        'password': 'Password@123',
        'confirm_password': 'Password@123'
    }, follow_redirects=True)
    assert res.status_code == 200

    user = User.query.filter_by(email='student@example.com').first()
    assert user is not None
    assert user.role == 'student'
    assert user.student_profile is not None
    assert user.student_profile.roll_number == 'STU-001'


def test_login_and_logout(client):
    # Create user first
    user = User(name='Admin User', email='admin@example.com', role='admin')
    user.set_password('Admin@123')
    db.session.add(user)
    db.session.commit()

    # Login success
    res = client.post('/auth/login', data={
        'email': 'admin@example.com',
        'password': 'Admin@123'
    }, follow_redirects=True)
    assert res.status_code == 200
    assert b"Admin Dashboard" in res.data or b"admin" in res.data

    # Logout
    res = client.get('/auth/logout', follow_redirects=True)
    assert res.status_code == 200
    assert b"logged out" in res.data or b"Sign In" in res.data
