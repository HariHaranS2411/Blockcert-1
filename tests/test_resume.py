import pytest
from app import create_app
from app.extensions import db
from app.models.user import User
from app.models.student import Student
from app.models.certificate import Certificate
from app.models.resume import Resume
from app.services.ai_resume_service import AIResumeService


@pytest.fixture
def client():
    app = create_app('testing')
    with app.test_client() as client:
        with app.app_context():
            db.create_all()
            yield client
            db.session.remove()
            db.drop_all()


def test_cgpa_strategy_analysis():
    high = AIResumeService.analyze_cgpa_strategy(9.2)
    assert high['tier'] == 'high_distinction'
    assert high['highlight_education'] is True

    moderate = AIResumeService.analyze_cgpa_strategy(7.6)
    assert moderate['tier'] == 'balanced'

    lower = AIResumeService.analyze_cgpa_strategy(6.5)
    assert lower['tier'] == 'project_first'
    assert lower['highlight_education'] is False


def test_ai_text_polishing():
    rough_input = "i made website for college using python"
    polished = AIResumeService.polish_text_with_ai(rough_input, context_type="project")
    assert "developed" in polished.lower() or "engineered" in polished.lower()
    assert "python" in polished.lower()


def test_extract_skills_from_certificates():
    class DummyCert:
        def __init__(self, course):
            self.course = course

    certs = [
        DummyCert("Python Programming & Advanced Data Structures"),
        DummyCert("Full Stack Web Development & REST APIs"),
        DummyCert("Blockchain & Solidity Engineering")
    ]

    skills = AIResumeService.extract_skills_from_certificates(certs)
    assert "Python" in skills
    assert "Solidity" in skills or "Smart Contracts" in skills


def test_resume_builder_endpoints(client):
    # Create test student user and profile
    student_user = User(name='Alex Student', email='alex@resume.com', role='student')
    student_user.set_password('Pass@123')
    db.session.add(student_user)
    db.session.flush()

    student_profile = Student(
        user_id=student_user.id,
        roll_number='STU-RESUME-01',
        degree='B.S. Computer Science',
        department='Computer Science',
        graduation_year=2025,
        cgpa=8.8
    )
    db.session.add(student_profile)
    db.session.commit()

    # 1. Login student
    client.post('/auth/login', data={'email': 'alex@resume.com', 'password': 'Pass@123'}, follow_redirects=True)

    # 2. Access Resume Builder
    res = client.get('/student/resume')
    assert res.status_code == 200
    assert b"AI Resume Maker" in res.data

    # 3. Test AI Interview Step
    interview_res = client.post('/student/resume/interview', json={
        'step': 0,
        'message': '',
        'state': {}
    })
    assert interview_res.status_code == 200
    data = interview_res.get_json()
    assert data['success'] is True
    assert data['next_step'] == 1
    assert "BlockCert AI Career Coach" in data['ai_message']

    # 4. Test Polish Endpoint
    polish_res = client.post('/student/resume/polish', json={
        'text': 'i made attendance app with flask and mysql',
        'context_type': 'project'
    })
    assert polish_res.status_code == 200
    p_data = polish_res.get_json()
    assert p_data['success'] is True
    assert len(p_data['polished']) > 0

    # 5. Test Save Resume Endpoint
    save_res = client.post('/student/resume/save', json={
        'title': 'Alex Tech Resume',
        'resume_data': {
            'summary': 'Software engineer specializing in backend systems.',
            'academic': {'degree': 'B.S. Computer Science', 'cgpa': 8.8},
            'projects': [{'title': 'Attendance System', 'polished_bullets': ['Engineered database workflows.']}]
        }
    })
    assert save_res.status_code == 200
    s_data = save_res.get_json()
    assert s_data['success'] is True

    # 6. Test Preview Endpoint
    prev_res = client.get('/student/resume/preview')
    assert prev_res.status_code == 200
    assert b"Alex Student" in prev_res.data
    assert b"Blockchain Verified" in prev_res.data or b"Education" in prev_res.data
