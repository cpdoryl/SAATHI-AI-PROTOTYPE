"""
SAATHI AI — Crisis Detection Unit Tests
Target: <100ms scan time on all test cases
"""
import pytest
import time
from services.crisis_detection_service import CrisisDetectionService


@pytest.fixture
def crisis_service():
    return CrisisDetectionService()


def test_non_crisis_message(crisis_service):
    result = crisis_service.scan("I've been feeling a bit stressed at work lately")
    assert result["severity"] < 7.0
    assert result["escalate"] is False


def test_high_severity_crisis(crisis_service):
    result = crisis_service.scan("I want to kill myself")
    assert result["severity"] >= 9.0
    assert result["escalate"] is True
    assert len(result["detected_keywords"]) > 0


def test_moderate_crisis(crisis_service):
    result = crisis_service.scan("I feel so hopeless, I can't cope anymore")
    assert result["severity"] >= 5.0


def test_scan_speed(crisis_service):
    """Crisis detection must complete in <100ms."""
    start = time.time()
    for _ in range(100):
        crisis_service.scan("I've been having some dark thoughts lately")
    elapsed_ms = (time.time() - start) * 1000 / 100
    assert elapsed_ms < 100, f"Scan took {elapsed_ms:.1f}ms — must be <100ms"


def test_hinglish_crisis(crisis_service):
    result = crisis_service.scan("Mar jaana chahta hoon")
    assert result["severity"] >= 7.0
    assert result["escalate"] is True


def test_empty_message(crisis_service):
    result = crisis_service.scan("")
    assert result["severity"] == 0.0
    assert result["escalate"] is False


def test_multiple_keywords_accumulate(crisis_service):
    result = crisis_service.scan("I feel hopeless and worthless, I want to die")
    single = CrisisDetectionService().scan("I want to die")
    # Multiple keywords should score higher or equal
    assert result["severity"] >= single["severity"]
