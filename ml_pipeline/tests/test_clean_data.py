"""
ml_pipeline/tests/test_clean_data.py
Tests for the clean_data.py pipeline.

Run:
    pytest ml_pipeline/tests/test_clean_data.py -v
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

# Make scripts importable without installing as package
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from clean_data import (
    CleaningStats,
    _count_turns,
    _detect_pii,
    _first_user_message,
    _full_text,
    _is_valid_format,
    clean_dataset,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_record(turns: list[tuple[str, str]]) -> dict:
    """Build a messages-format record from (role, content) pairs."""
    return {"messages": [{"role": r, "content": c} for r, c in turns]}


def write_jsonl(path: Path, records: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for rec in records:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")


def read_jsonl(path: Path) -> list[dict]:
    with path.open("r", encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


# ---------------------------------------------------------------------------
# Unit tests — _is_valid_format
# ---------------------------------------------------------------------------

class TestIsValidFormat:
    def test_valid_record(self):
        rec = make_record([("user", "Hello"), ("assistant", "Hi")])
        ok, reason = _is_valid_format(rec)
        assert ok
        assert reason == ""

    def test_not_a_dict(self):
        ok, reason = _is_valid_format(["messages"])
        assert not ok
        assert "not a dict" in reason

    def test_missing_messages_key(self):
        ok, reason = _is_valid_format({"data": []})
        assert not ok
        assert "missing" in reason

    def test_empty_messages_list(self):
        ok, reason = _is_valid_format({"messages": []})
        assert not ok

    def test_message_missing_role(self):
        rec = {"messages": [{"content": "hi"}]}
        ok, reason = _is_valid_format(rec)
        assert not ok
        assert "role" in reason

    def test_message_missing_content(self):
        rec = {"messages": [{"role": "user"}]}
        ok, reason = _is_valid_format(rec)
        assert not ok
        assert "content" in reason

    def test_unknown_role(self):
        rec = {"messages": [{"role": "bot", "content": "hi"}]}
        ok, reason = _is_valid_format(rec)
        assert not ok
        assert "unknown role" in reason

    def test_system_role_allowed(self):
        rec = {"messages": [
            {"role": "system", "content": "You are a therapist."},
            {"role": "user", "content": "Hello"},
        ]}
        ok, _ = _is_valid_format(rec)
        assert ok

    def test_non_string_content(self):
        rec = {"messages": [{"role": "user", "content": 123}]}
        ok, reason = _is_valid_format(rec)
        assert not ok
        assert "not a string" in reason


# ---------------------------------------------------------------------------
# Unit tests — _count_turns
# ---------------------------------------------------------------------------

class TestCountTurns:
    def test_two_turns(self):
        rec = make_record([("user", "Hi"), ("assistant", "Hello")])
        assert _count_turns(rec) == 2

    def test_five_turns(self):
        rec = make_record([
            ("user", "A"), ("assistant", "B"),
            ("user", "C"), ("assistant", "D"),
            ("user", "E"),
        ])
        assert _count_turns(rec) == 5


# ---------------------------------------------------------------------------
# Unit tests — _first_user_message
# ---------------------------------------------------------------------------

class TestFirstUserMessage:
    def test_finds_first_user(self):
        rec = make_record([("assistant", "Welcome"), ("user", "I need help")])
        assert _first_user_message(rec) == "I need help"

    def test_no_user_message(self):
        rec = {"messages": [{"role": "assistant", "content": "Hi"}]}
        assert _first_user_message(rec) is None


# ---------------------------------------------------------------------------
# Unit tests — _detect_pii
# ---------------------------------------------------------------------------

class TestDetectPii:
    def test_no_pii(self):
        findings = _detect_pii("I have been feeling anxious lately.", 1)
        assert findings == []

    def test_detects_email(self):
        findings = _detect_pii("Contact me at user@example.com please", 1)
        types = [f["type"] for f in findings]
        assert "email" in types

    def test_detects_indian_phone_10_digit(self):
        findings = _detect_pii("Call me at 9876543210 anytime", 1)
        types = [f["type"] for f in findings]
        assert "phone" in types

    def test_detects_indian_phone_with_prefix(self):
        findings = _detect_pii("My number is +91 9876543210", 1)
        types = [f["type"] for f in findings]
        assert "phone" in types

    def test_detects_aadhaar_12digit(self):
        findings = _detect_pii("My Aadhaar is 123456789012", 1)
        types = [f["type"] for f in findings]
        assert "aadhaar" in types

    def test_detects_aadhaar_spaced(self):
        findings = _detect_pii("ID: 1234 5678 9012", 1)
        types = [f["type"] for f in findings]
        assert "aadhaar" in types

    def test_aadhaar_match_redacted(self):
        findings = _detect_pii("123456789012", 1)
        aadhaar_findings = [f for f in findings if f["type"] == "aadhaar"]
        assert aadhaar_findings
        assert aadhaar_findings[0]["match"].startswith("*")

    def test_multiple_pii(self):
        text = "Email me at foo@bar.com or call 9876543210"
        findings = _detect_pii(text, 1)
        types = {f["type"] for f in findings}
        assert "email" in types
        assert "phone" in types

    def test_phone_not_matched_in_short_number(self):
        # 7-digit number should NOT trigger phone detection
        findings = _detect_pii("Code is 1234567", 1)
        phone_findings = [f for f in findings if f["type"] == "phone"]
        assert phone_findings == []

    def test_invalid_mobile_prefix(self):
        # Numbers starting with 5 are not valid Indian mobile numbers
        findings = _detect_pii("Number 5123456789", 1)
        phone_findings = [f for f in findings if f["type"] == "phone"]
        assert phone_findings == []


# ---------------------------------------------------------------------------
# Integration tests — clean_dataset (uses tmp_path fixture)
# ---------------------------------------------------------------------------

class TestCleanDataset:
    def test_keeps_valid_records(self, tmp_path):
        records = [
            make_record([("user", "I feel sad"), ("assistant", "Tell me more"), ("user", "Every day")]),
            make_record([("user", "Anxious often"), ("assistant", "I understand"), ("user", "Yes a lot")]),
        ]
        inp = tmp_path / "in.jsonl"
        out = tmp_path / "out.jsonl"
        write_jsonl(inp, records)

        stats = clean_dataset(inp, out, min_turns=3, max_tokens=2048)

        assert stats.kept == 2
        assert stats.invalid_format == 0
        assert stats.pii_flagged == 0
        assert len(read_jsonl(out)) == 2

    def test_removes_invalid_format(self, tmp_path):
        records = [
            {"bad_key": []},
            make_record([("user", "Valid"), ("assistant", "Yes"), ("user", "More")]),
        ]
        inp = tmp_path / "in.jsonl"
        out = tmp_path / "out.jsonl"
        write_jsonl(inp, records)

        stats = clean_dataset(inp, out, min_turns=3, max_tokens=2048)

        assert stats.invalid_format == 1
        assert stats.kept == 1

    def test_removes_duplicates(self, tmp_path):
        rec = make_record([("user", "I feel anxious"), ("assistant", "I hear you"), ("user", "Yes")])
        records = [rec, rec, rec]
        inp = tmp_path / "in.jsonl"
        out = tmp_path / "out.jsonl"
        write_jsonl(inp, records)

        stats = clean_dataset(inp, out, min_turns=3, max_tokens=2048)

        assert stats.duplicate == 2
        assert stats.kept == 1

    def test_removes_short_conversations(self, tmp_path):
        records = [
            make_record([("user", "Hi"), ("assistant", "Hello")]),   # 2 turns — too short
            make_record([("user", "Hello"), ("assistant", "Hi"), ("user", "Tell me")]),  # 3 turns — ok
        ]
        inp = tmp_path / "in.jsonl"
        out = tmp_path / "out.jsonl"
        write_jsonl(inp, records)

        stats = clean_dataset(inp, out, min_turns=3, max_tokens=2048)

        assert stats.too_short == 1
        assert stats.kept == 1

    def test_removes_pii_email(self, tmp_path):
        records = [
            make_record([
                ("user", "Email me at patient@gmail.com"),
                ("assistant", "I understand"),
                ("user", "Thanks"),
            ]),
            make_record([
                ("user", "I feel lonely"),
                ("assistant", "Tell me more"),
                ("user", "Yes always"),
            ]),
        ]
        inp = tmp_path / "in.jsonl"
        out = tmp_path / "out.jsonl"
        write_jsonl(inp, records)

        stats = clean_dataset(inp, out, min_turns=3, max_tokens=2048)

        assert stats.pii_flagged == 1
        assert stats.kept == 1

    def test_removes_pii_phone(self, tmp_path):
        records = [
            make_record([
                ("user", "Call me on 9988776655"),
                ("assistant", "I understand"),
                ("user", "Please"),
            ]),
        ]
        inp = tmp_path / "in.jsonl"
        out = tmp_path / "out.jsonl"
        write_jsonl(inp, records)

        stats = clean_dataset(inp, out, min_turns=3, max_tokens=2048)

        assert stats.pii_flagged == 1
        assert stats.kept == 0

    def test_removes_pii_aadhaar(self, tmp_path):
        records = [
            make_record([
                ("user", "My Aadhaar is 234567890123"),
                ("assistant", "OK"),
                ("user", "Yes"),
            ]),
        ]
        inp = tmp_path / "in.jsonl"
        out = tmp_path / "out.jsonl"
        write_jsonl(inp, records)

        stats = clean_dataset(inp, out, min_turns=3, max_tokens=2048)

        assert stats.pii_flagged == 1
        assert stats.kept == 0

    def test_removes_too_long(self, tmp_path):
        # Create a very long conversation that exceeds 2048 tokens
        long_content = "word " * 3000  # ~3000 words ≈ 3000 tokens
        records = [
            make_record([
                ("user", long_content),
                ("assistant", "I see"),
                ("user", "Thank you"),
            ]),
            make_record([
                ("user", "Short message"),
                ("assistant", "I understand"),
                ("user", "Thanks"),
            ]),
        ]
        inp = tmp_path / "in.jsonl"
        out = tmp_path / "out.jsonl"
        write_jsonl(inp, records)

        stats = clean_dataset(inp, out, min_turns=3, max_tokens=2048)

        assert stats.too_long == 1
        assert stats.kept == 1

    def test_skips_blank_lines(self, tmp_path):
        rec = make_record([("user", "Hello"), ("assistant", "Hi"), ("user", "More")])
        inp = tmp_path / "in.jsonl"
        inp.write_text(
            "\n" + json.dumps(rec) + "\n\n",
            encoding="utf-8",
        )
        out = tmp_path / "out.jsonl"

        stats = clean_dataset(inp, out, min_turns=3, max_tokens=2048)

        assert stats.total_read == 1
        assert stats.kept == 1

    def test_invalid_json_line(self, tmp_path):
        inp = tmp_path / "in.jsonl"
        inp.write_text(
            '{"messages": [{"role": "user", "content": "hi"}]}\n'
            "NOT VALID JSON\n",
            encoding="utf-8",
        )
        out = tmp_path / "out.jsonl"

        stats = clean_dataset(inp, out, min_turns=1, max_tokens=2048)

        assert stats.invalid_format == 1

    def test_output_is_valid_jsonl(self, tmp_path):
        records = [
            make_record([("user", f"Message {i}"), ("assistant", "OK"), ("user", "Yes")])
            for i in range(5)
        ]
        inp = tmp_path / "in.jsonl"
        out = tmp_path / "out.jsonl"
        write_jsonl(inp, records)

        clean_dataset(inp, out, min_turns=3, max_tokens=2048)

        # Every line must be valid JSON with messages key
        for rec in read_jsonl(out):
            assert "messages" in rec
            assert isinstance(rec["messages"], list)

    def test_stats_summary_contains_key_fields(self, tmp_path):
        inp = tmp_path / "in.jsonl"
        out = tmp_path / "out.jsonl"
        write_jsonl(inp, [])
        stats = CleaningStats(total_read=10, kept=7, duplicate=2, pii_flagged=1)
        summary = stats.summary()
        assert "10" in summary
        assert "7" in summary
        assert "2" in summary
        assert "1" in summary


# ---------------------------------------------------------------------------
# CLI tests — main()
# ---------------------------------------------------------------------------

class TestMain:
    def test_missing_input_returns_1(self, tmp_path):
        from clean_data import main

        result = main([
            "--input", str(tmp_path / "nonexistent.jsonl"),
            "--output", str(tmp_path / "out.jsonl"),
        ])
        assert result == 1

    def test_clean_run_returns_0(self, tmp_path):
        from clean_data import main

        records = [
            make_record([("user", "I need help"), ("assistant", "Sure"), ("user", "Thanks")]),
        ]
        inp = tmp_path / "in.jsonl"
        out = tmp_path / "out.jsonl"
        write_jsonl(inp, records)

        result = main(["--input", str(inp), "--output", str(out)])
        assert result == 0

    def test_pii_run_returns_1(self, tmp_path):
        from clean_data import main

        records = [
            make_record([
                ("user", "Call 9876543210"),
                ("assistant", "Sure"),
                ("user", "OK"),
            ]),
        ]
        inp = tmp_path / "in.jsonl"
        out = tmp_path / "out.jsonl"
        write_jsonl(inp, records)

        result = main(["--input", str(inp), "--output", str(out)])
        assert result == 1

    def test_pii_report_written(self, tmp_path):
        from clean_data import main

        records = [
            make_record([
                ("user", "email: test@example.com"),
                ("assistant", "Sure"),
                ("user", "OK"),
            ]),
        ]
        inp = tmp_path / "in.jsonl"
        out = tmp_path / "out.jsonl"
        pii_report = tmp_path / "pii.json"
        write_jsonl(inp, records)

        main([
            "--input", str(inp),
            "--output", str(out),
            "--pii-report", str(pii_report),
        ])

        assert pii_report.exists()
        findings = json.loads(pii_report.read_text())
        assert isinstance(findings, list)
        assert len(findings) >= 1
        assert findings[0]["type"] == "email"
