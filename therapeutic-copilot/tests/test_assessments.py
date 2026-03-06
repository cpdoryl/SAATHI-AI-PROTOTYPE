"""SAATHI AI — Clinical Assessment Unit Tests"""
import pytest
from services.assessment_service import AssessmentService


@pytest.fixture
def service():
    return AssessmentService()


def test_phq9_minimal(service):
    responses = [0, 0, 0, 0, 0, 0, 0, 0, 0]
    result = service.score("PHQ-9", responses)
    assert result["severity"] == "None–minimal"
    assert result["total_score"] == 0


def test_phq9_severe(service):
    responses = [3, 3, 3, 3, 3, 3, 3, 3, 3]
    result = service.score("PHQ-9", responses)
    assert result["severity"] == "Severe"
    assert result["total_score"] == 27


def test_gad7_mild(service):
    responses = [1, 1, 1, 1, 1, 1, 1]
    result = service.score("GAD-7", responses)
    assert result["severity"] == "Mild"


def test_unknown_assessment(service):
    result = service.score("UNKNOWN", [1, 2, 3])
    assert "error" in result


def test_get_questions_phq9(service):
    questions = service.get_questions("PHQ-9")
    assert len(questions) == 9
    assert all("text" in q for q in questions)
