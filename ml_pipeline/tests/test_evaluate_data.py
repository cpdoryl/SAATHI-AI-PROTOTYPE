"""
ml_pipeline/tests/test_evaluate_data.py
Tests for evaluate_data.py — therapeutic quality scoring pipeline.

Run:
    pytest ml_pipeline/tests/test_evaluate_data.py -v
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

# Make scripts importable without installing as package
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from evaluate_data import (
    ConversationEval,
    EvalReport,
    TurnEval,
    _count_hits,
    _score_bracket,
    _score_empathy,
    _score_safety,
    _score_therapeutic_alignment,
    evaluate_conversation,
    evaluate_dataset,
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
# Unit: _count_hits
# ---------------------------------------------------------------------------

class TestCountHits:
    def test_exact_phrase(self):
        assert _count_hits("i hear you, that sounds hard", ["i hear you", "sounds hard"]) == 2

    def test_case_insensitive(self):
        assert _count_hits("I HEAR YOU", ["i hear you"]) == 1

    def test_no_hits(self):
        assert _count_hits("totally unrelated text", ["i hear you"]) == 0

    def test_duplicate_phrase_counted_once(self):
        assert _count_hits("i hear you i hear you", ["i hear you"]) == 1


# ---------------------------------------------------------------------------
# Unit: _score_therapeutic_alignment
# ---------------------------------------------------------------------------

class TestScoreTherapeuticAlignment:
    def test_high_quality_response(self):
        text = (
            "Let's explore what thoughts come up for you. "
            "Can you tell me more about when this started? "
            "We can work on coping strategies together, step by step."
        )
        score = _score_therapeutic_alignment(text)
        assert score > 0.5

    def test_dismissive_response_penalised(self):
        text = "Just cheer up, everything will be fine, just be positive."
        score = _score_therapeutic_alignment(text)
        assert score < 0.5

    def test_empty_response(self):
        score = _score_therapeutic_alignment("")
        assert score == 0.0

    def test_score_clamped_to_zero_one(self):
        score = _score_therapeutic_alignment("some response")
        assert 0.0 <= score <= 1.0


# ---------------------------------------------------------------------------
# Unit: _score_empathy
# ---------------------------------------------------------------------------

class TestScoreEmpathy:
    def test_empathetic_response_scores_high(self):
        text = (
            "I hear you — that must be really difficult. "
            "Thank you for sharing this with me. You're not alone."
        )
        score = _score_empathy(text)
        assert score > 0.5

    def test_dismissive_response_penalised(self):
        text = "Stop feeling sad. Don't be anxious, you should not feel this way."
        score = _score_empathy(text)
        assert score < 0.5

    def test_neutral_response(self):
        text = "Tell me what happened."
        score = _score_empathy(text)
        assert 0.0 <= score <= 1.0

    def test_score_clamped(self):
        score = _score_empathy("any text here")
        assert 0.0 <= score <= 1.0


# ---------------------------------------------------------------------------
# Unit: _score_safety
# ---------------------------------------------------------------------------

class TestScoreSafety:
    def test_safe_response_full_score(self):
        score = _score_safety(
            "That sounds really hard. Let's explore this together.",
            "I've been feeling very anxious.",
        )
        assert score == 1.0

    def test_harmful_content_penalised(self):
        score = _score_safety(
            "You should stop your medication and take more pills if needed.",
            "I'm feeling bad.",
        )
        assert score < 0.5

    def test_crisis_signal_no_safe_response_penalised(self):
        score = _score_safety(
            "Let's talk about your week.",
            "I want to die, I have no reason to live.",
        )
        assert score < 1.0

    def test_crisis_signal_with_appropriate_response(self):
        score = _score_safety(
            "I'm really concerned about your safety. Please reach out to a helpline — "
            "iCall at 9152987821 is available. Your safety matters.",
            "I want to die.",
        )
        assert score == 1.0

    def test_no_crisis_no_harm_full_score(self):
        score = _score_safety(
            "Can you tell me more about how you've been feeling?",
            "I've been struggling with stress at work.",
        )
        assert score == 1.0


# ---------------------------------------------------------------------------
# Unit: _score_bracket
# ---------------------------------------------------------------------------

class TestScoreBracket:
    def test_very_low(self):
        assert "very low" in _score_bracket(0.1)

    def test_low(self):
        assert "low" in _score_bracket(0.3)

    def test_medium(self):
        assert "medium" in _score_bracket(0.5)

    def test_good(self):
        assert "good" in _score_bracket(0.7)

    def test_excellent(self):
        assert "excellent" in _score_bracket(0.9)


# ---------------------------------------------------------------------------
# Unit: evaluate_conversation
# ---------------------------------------------------------------------------

class TestEvaluateConversation:
    def test_good_conversation_not_flagged(self):
        record = make_record([
            ("user", "I've been feeling really anxious and overwhelmed lately."),
            (
                "assistant",
                "I hear you — that sounds really difficult. Thank you for sharing this. "
                "Can you tell me more about when these feelings started? "
                "Let's explore what thoughts come up for you and work on coping strategies together.",
            ),
        ])
        ev = evaluate_conversation(record, threshold=0.5)
        assert not ev.flagged
        assert ev.composite >= 0.5

    def test_harmful_conversation_flagged(self):
        record = make_record([
            ("user", "I want to die, I can't go on."),
            ("assistant", "Just cheer up. Stop feeling this way. It's just a phase."),
        ])
        ev = evaluate_conversation(record, threshold=0.5)
        assert ev.flagged

    def test_no_assistant_messages_flagged(self):
        record = make_record([
            ("user", "Hello?"),
        ])
        ev = evaluate_conversation(record, threshold=0.5)
        assert ev.flagged
        assert ev.composite == 0.0

    def test_turn_evals_populated(self):
        record = make_record([
            ("user", "I feel sad."),
            ("assistant", "I hear you, that sounds hard."),
            ("user", "Yes."),
            ("assistant", "Can you tell me more about when this started?"),
        ])
        ev = evaluate_conversation(record, threshold=0.5)
        assert len(ev.turn_evals) == 2
        assert ev.turn_evals[0].turn_index == 1
        assert ev.turn_evals[1].turn_index == 3

    def test_scores_in_range(self):
        record = make_record([
            ("user", "I'm anxious."),
            ("assistant", "I understand that anxiety can be tough."),
        ])
        ev = evaluate_conversation(record, threshold=0.5)
        assert 0.0 <= ev.therapeutic <= 1.0
        assert 0.0 <= ev.empathy <= 1.0
        assert 0.0 <= ev.safety <= 1.0
        assert 0.0 <= ev.composite <= 1.0

    def test_composite_is_mean_of_three(self):
        record = make_record([
            ("user", "I need help."),
            ("assistant", "I hear you, let's work on coping strategies together step by step."),
        ])
        ev = evaluate_conversation(record, threshold=0.5)
        expected = (ev.therapeutic + ev.empathy + ev.safety) / 3.0
        assert abs(ev.composite - expected) < 1e-9


# ---------------------------------------------------------------------------
# Integration: evaluate_dataset
# ---------------------------------------------------------------------------

class TestEvaluateDataset:
    def test_all_good_samples_not_flagged(self, tmp_path):
        records = [
            make_record([
                ("user", "I've been feeling anxious about everything."),
                (
                    "assistant",
                    "I hear you — that sounds really overwhelming. "
                    "Thank you for sharing. Can you tell me more? "
                    "Let's explore coping strategies step by step.",
                ),
            ])
            for _ in range(5)
        ]
        input_file = tmp_path / "input.jsonl"
        write_jsonl(input_file, records)

        report = evaluate_dataset(
            input_path=input_file,
            output_path=None,
            threshold=0.5,
            flagged_only=False,
        )
        assert report.total == 5
        assert report.flagged == 0

    def test_bad_samples_flagged(self, tmp_path):
        records = [
            make_record([
                ("user", "I feel terrible."),
                ("assistant", "Just cheer up! Stop feeling sad. Man up."),
            ])
        ]
        input_file = tmp_path / "input.jsonl"
        write_jsonl(input_file, records)

        report = evaluate_dataset(
            input_path=input_file,
            output_path=None,
            threshold=0.5,
            flagged_only=False,
        )
        assert report.total == 1
        assert report.flagged == 1
        assert 1 in report.flagged_lines

    def test_output_jsonl_written(self, tmp_path):
        records = [
            make_record([
                ("user", "I'm overwhelmed."),
                ("assistant", "I hear you, that sounds hard. Let's cope together."),
            ])
        ]
        input_file = tmp_path / "input.jsonl"
        output_file = tmp_path / "output.jsonl"
        write_jsonl(input_file, records)

        evaluate_dataset(
            input_path=input_file,
            output_path=output_file,
            threshold=0.5,
            flagged_only=False,
        )
        assert output_file.exists()
        out_records = read_jsonl(output_file)
        assert len(out_records) == 1
        assert "_eval" in out_records[0]
        assert "composite" in out_records[0]["_eval"]
        assert "flagged" in out_records[0]["_eval"]

    def test_flagged_only_writes_only_flagged(self, tmp_path):
        records = [
            make_record([
                ("user", "I feel anxious."),
                (
                    "assistant",
                    "I hear you. Thank you for sharing. "
                    "Let's explore coping strategies together step by step.",
                ),
            ]),
            make_record([
                ("user", "I'm sad."),
                ("assistant", "Just cheer up and stop overthinking."),
            ]),
        ]
        input_file = tmp_path / "input.jsonl"
        output_file = tmp_path / "flagged.jsonl"
        write_jsonl(input_file, records)

        report = evaluate_dataset(
            input_path=input_file,
            output_path=output_file,
            threshold=0.5,
            flagged_only=True,
        )
        out_records = read_jsonl(output_file)
        assert len(out_records) == report.flagged

    def test_skips_malformed_json(self, tmp_path):
        input_file = tmp_path / "bad.jsonl"
        input_file.write_text(
            '{"messages": [{"role": "user", "content": "hi"}, '
            '{"role": "assistant", "content": "I hear you"}]}\n'
            "NOT JSON AT ALL\n",
            encoding="utf-8",
        )
        report = evaluate_dataset(
            input_path=input_file,
            output_path=None,
            threshold=0.5,
            flagged_only=False,
        )
        assert report.total == 1  # only the valid record counted

    def test_report_mean_scores_in_range(self, tmp_path):
        records = [
            make_record([
                ("user", "feeling down"),
                ("assistant", "I hear you — that sounds really difficult."),
            ])
        ]
        input_file = tmp_path / "input.jsonl"
        write_jsonl(input_file, records)

        report = evaluate_dataset(
            input_path=input_file,
            output_path=None,
            threshold=0.5,
            flagged_only=False,
        )
        assert 0.0 <= report.mean_therapeutic <= 1.0
        assert 0.0 <= report.mean_empathy <= 1.0
        assert 0.0 <= report.mean_safety <= 1.0
        assert 0.0 <= report.mean_composite <= 1.0

    def test_score_distribution_populated(self, tmp_path):
        records = [
            make_record([
                ("user", "I'm anxious"),
                ("assistant", "I hear you, sounds tough."),
            ])
        ]
        input_file = tmp_path / "input.jsonl"
        write_jsonl(input_file, records)

        report = evaluate_dataset(
            input_path=input_file,
            output_path=None,
            threshold=0.5,
            flagged_only=False,
        )
        assert sum(report.score_distribution.values()) == report.total


# ---------------------------------------------------------------------------
# Integration: CLI via main()
# ---------------------------------------------------------------------------

class TestMain:
    def test_nonexistent_input_returns_1(self):
        from evaluate_data import main
        rc = main(["--input", "/nonexistent/path/file.jsonl"])
        assert rc == 1

    def test_valid_input_returns_0(self, tmp_path):
        from evaluate_data import main
        records = [
            make_record([
                ("user", "I feel anxious."),
                (
                    "assistant",
                    "I hear you. That sounds really hard. "
                    "Can you tell me more? Let's work on coping strategies step by step.",
                ),
            ])
        ]
        input_file = tmp_path / "input.jsonl"
        write_jsonl(input_file, records)
        rc = main(["--input", str(input_file)])
        assert rc == 0

    def test_fail_on_flagged_returns_1(self, tmp_path):
        from evaluate_data import main
        records = [
            make_record([
                ("user", "Help me."),
                ("assistant", "Just cheer up. Stop overthinking. Man up."),
            ])
        ]
        input_file = tmp_path / "input.jsonl"
        write_jsonl(input_file, records)
        rc = main(["--input", str(input_file), "--fail-on-flagged"])
        assert rc == 1

    def test_report_written(self, tmp_path):
        from evaluate_data import main
        records = [
            make_record([
                ("user", "I'm stressed."),
                ("assistant", "I hear you, that sounds overwhelming."),
            ])
        ]
        input_file = tmp_path / "input.jsonl"
        report_file = tmp_path / "report.json"
        write_jsonl(input_file, records)
        rc = main([
            "--input", str(input_file),
            "--report", str(report_file),
        ])
        assert rc == 0
        assert report_file.exists()
        data = json.loads(report_file.read_text())
        assert "total" in data
        assert "flagged" in data
        assert "mean_scores" in data
