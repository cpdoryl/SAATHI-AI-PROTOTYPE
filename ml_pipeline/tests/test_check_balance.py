"""
ml_pipeline/tests/test_check_balance.py
Tests for check_balance.py — dataset balance analysis pipeline.

Run:
    pytest ml_pipeline/tests/test_check_balance.py -v
"""

from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

import pytest

# Make scripts importable without installing as package
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from check_balance import (
    BalanceReport,
    DimensionReport,
    _classify_length,
    _detect_language,
    _detect_topic,
    _full_text,
    check_balance,
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


# ---------------------------------------------------------------------------
# Unit tests — _detect_topic
# ---------------------------------------------------------------------------

class TestDetectTopic:
    def test_depression_keyword(self):
        assert _detect_topic("I have been feeling very depressed and hopeless") == "depression"

    def test_anxiety_keyword(self):
        assert _detect_topic("I suffer from severe anxiety and panic attacks") == "anxiety"

    def test_ocd_keyword(self):
        assert _detect_topic("I have intrusive thoughts and compulsive rituals") == "ocd"

    def test_ptsd_keyword(self):
        assert _detect_topic("I experience flashbacks from the trauma") == "ptsd"

    def test_relationship_keyword(self):
        assert _detect_topic("My marriage is falling apart and my family disagrees") == "relationship"

    def test_other_fallback(self):
        assert _detect_topic("The weather is nice today") == "other"

    def test_case_insensitive(self):
        assert _detect_topic("ANXIETY is overwhelming me") == "anxiety"

    def test_empty_text_returns_other(self):
        assert _detect_topic("") == "other"

    def test_first_match_wins(self):
        # 'depressed' appears first in keyword order; relationship keyword also present
        text = "I feel depressed because my relationship is bad"
        assert _detect_topic(text) == "depression"


# ---------------------------------------------------------------------------
# Unit tests — _classify_length
# ---------------------------------------------------------------------------

class TestClassifyLength:
    def test_short_lower_bound(self):
        assert _classify_length(3) == "short (3-8)"

    def test_short_upper_bound(self):
        assert _classify_length(8) == "short (3-8)"

    def test_medium_lower_bound(self):
        assert _classify_length(9) == "medium (9-15)"

    def test_medium_upper_bound(self):
        assert _classify_length(15) == "medium (9-15)"

    def test_long_starts_at_16(self):
        assert _classify_length(16) == "long (16+)"

    def test_very_long(self):
        assert _classify_length(30) == "long (16+)"


# ---------------------------------------------------------------------------
# Unit tests — _detect_language
# ---------------------------------------------------------------------------

class TestDetectLanguage:
    def test_plain_english(self):
        result = _detect_language(
            "I have been feeling very sad and hopeless lately."
        )
        assert result == "english"

    def test_hinglish_with_common_words(self):
        # "aur", "bohot", "hai", "nahi" push ratio above 5%
        text = "I am feeling bohot sad aur I dont know kya to do nahi samajh"
        result = _detect_language(text)
        assert result == "hinglish"

    def test_devanagari_is_mixed(self):
        # Contains non-ASCII Devanagari chars, no Hinglish words
        result = _detect_language("I feel मेरा something")
        assert result == "mixed"

    def test_empty_text_returns_english(self):
        assert _detect_language("") == "english"

    def test_hinglish_threshold_sensitive(self):
        # One Hinglish word in many English words — below threshold
        text = "I feel very worried and " + "word " * 50 + "aur"
        # hinglish_count = 1, total tokens ~ 55, ratio ≈ 0.018 < 0.05 → english
        result = _detect_language(text)
        assert result == "english"


# ---------------------------------------------------------------------------
# Unit tests — _full_text
# ---------------------------------------------------------------------------

class TestFullText:
    def test_concatenates_content(self):
        rec = make_record([("user", "Hello"), ("assistant", "Hi there")])
        assert "Hello" in _full_text(rec)
        assert "Hi there" in _full_text(rec)

    def test_empty_messages(self):
        assert _full_text({"messages": []}) == ""

    def test_skips_non_string_content(self):
        rec = {"messages": [{"role": "user", "content": 123}, {"role": "assistant", "content": "ok"}]}
        text = _full_text(rec)
        assert "ok" in text


# ---------------------------------------------------------------------------
# Unit tests — DimensionReport
# ---------------------------------------------------------------------------

class TestDimensionReport:
    def test_analyse_flags_below_threshold(self):
        dim = DimensionReport("topic")
        dim.counts = Counter({"depression": 90, "other": 5, "anxiety": 5})
        dim.analyse(threshold=0.10)
        assert "other" in dim.imbalanced
        assert "anxiety" in dim.imbalanced
        assert "depression" not in dim.imbalanced

    def test_analyse_no_imbalance(self):
        dim = DimensionReport("topic")
        dim.counts = Counter({"depression": 50, "anxiety": 50})
        dim.analyse(threshold=0.10)
        assert dim.imbalanced == []

    def test_analyse_empty_counts(self):
        dim = DimensionReport("topic")
        dim.analyse(threshold=0.10)
        assert dim.imbalanced == []

    def test_format_contains_counts(self):
        dim = DimensionReport("topic")
        dim.counts = Counter({"depression": 80, "anxiety": 20})
        dim.analyse(threshold=0.10)
        text = dim.format(threshold=0.10)
        assert "80" in text
        assert "20" in text

    def test_format_flags_imbalanced(self):
        dim = DimensionReport("topic")
        dim.counts = Counter({"depression": 95, "other": 5})
        dim.analyse(threshold=0.10)
        text = dim.format(threshold=0.10)
        assert "IMBALANCED" in text

    def test_format_no_flag_when_balanced(self):
        dim = DimensionReport("topic")
        dim.counts = Counter({"depression": 50, "anxiety": 50})
        dim.analyse(threshold=0.10)
        text = dim.format(threshold=0.10)
        assert "IMBALANCED" not in text


# ---------------------------------------------------------------------------
# Unit tests — BalanceReport
# ---------------------------------------------------------------------------

class TestBalanceReport:
    def test_any_imbalanced_true(self):
        br = BalanceReport(threshold=0.10)
        br.topic.counts = Counter({"depression": 99, "other": 1})
        br.length.counts = Counter({"short (3-8)": 100})
        br.language.counts = Counter({"english": 100})
        br.total = 100
        br.analyse()
        assert br.any_imbalanced is True

    def test_any_imbalanced_false(self):
        br = BalanceReport(threshold=0.10)
        br.topic.counts = Counter({"depression": 50, "anxiety": 50})
        br.length.counts = Counter({"short (3-8)": 50, "medium (9-15)": 50})
        br.language.counts = Counter({"english": 50, "hinglish": 50})
        br.total = 100
        br.analyse()
        assert br.any_imbalanced is False

    def test_summary_contains_total(self):
        br = BalanceReport(threshold=0.10)
        br.total = 42
        br.topic.counts = Counter({"depression": 42})
        br.length.counts = Counter({"short (3-8)": 42})
        br.language.counts = Counter({"english": 42})
        br.analyse()
        summary = br.summary()
        assert "42" in summary

    def test_to_dict_structure(self):
        br = BalanceReport(threshold=0.10)
        br.total = 10
        br.topic.counts = Counter({"other": 10})
        br.length.counts = Counter({"short (3-8)": 10})
        br.language.counts = Counter({"english": 10})
        br.analyse()
        d = br.to_dict()
        assert d["total"] == 10
        assert "topic" in d
        assert "length" in d
        assert "language" in d
        assert "counts" in d["topic"]
        assert "imbalanced" in d["topic"]


# ---------------------------------------------------------------------------
# Integration tests — check_balance (uses tmp_path fixture)
# ---------------------------------------------------------------------------

class TestCheckBalance:
    def _make_depression_record(self) -> dict:
        return make_record([
            ("user", "I have been feeling depressed and hopeless every day"),
            ("assistant", "I hear you. Can you tell me more about when this started?"),
            ("user", "It started a few months ago after I lost my job"),
        ])

    def _make_anxiety_record(self) -> dict:
        return make_record([
            ("user", "I suffer from anxiety and panic attacks frequently"),
            ("assistant", "Anxiety can be very challenging. What triggers your attacks?"),
            ("user", "Crowded places and social situations mostly"),
        ])

    def test_basic_count(self, tmp_path):
        records = [self._make_depression_record(), self._make_anxiety_record()]
        inp = tmp_path / "data.jsonl"
        write_jsonl(inp, records)

        report = check_balance(inp, threshold=0.10)
        assert report.total == 2

    def test_topic_counts_correct(self, tmp_path):
        records = [self._make_depression_record()] * 3 + [self._make_anxiety_record()] * 2
        inp = tmp_path / "data.jsonl"
        write_jsonl(inp, records)

        report = check_balance(inp)
        assert report.topic.counts["depression"] == 3
        assert report.topic.counts["anxiety"] == 2

    def test_length_short(self, tmp_path):
        # 3-message record → short
        records = [self._make_depression_record()]
        inp = tmp_path / "data.jsonl"
        write_jsonl(inp, records)

        report = check_balance(inp)
        assert report.length.counts["short (3-8)"] == 1

    def test_length_long(self, tmp_path):
        # 16-message record → long
        turns = [("user", "I feel depressed")] + [
            ("assistant", "Tell me more"), ("user", "Yes indeed")
        ] * 8  # 1 + 16 = 17 messages
        records = [{"messages": [{"role": r, "content": c} for r, c in turns]}]
        inp = tmp_path / "data.jsonl"
        write_jsonl(inp, records)

        report = check_balance(inp)
        assert report.length.counts["long (16+)"] == 1

    def test_language_english_classified(self, tmp_path):
        records = [self._make_depression_record()]
        inp = tmp_path / "data.jsonl"
        write_jsonl(inp, records)

        report = check_balance(inp)
        assert report.language.counts.get("english", 0) >= 1

    def test_language_hinglish_classified(self, tmp_path):
        hinglish_record = make_record([
            ("user", "Main bahut depressed feel kar raha hoon aur nahi samajh kya karun"),
            ("assistant", "Aap jo feel kar rahe hain woh bahut important hai. Aur baat karein?"),
            ("user", "Haan bilkul, bohot dukh hai mujhe"),
        ])
        inp = tmp_path / "data.jsonl"
        write_jsonl(inp, [hinglish_record])

        report = check_balance(inp)
        assert report.language.counts.get("hinglish", 0) == 1

    def test_imbalance_flagged(self, tmp_path):
        # 95 depression + 5 anxiety → anxiety < 10% → flagged
        records = [self._make_depression_record()] * 95 + [self._make_anxiety_record()] * 5
        inp = tmp_path / "data.jsonl"
        write_jsonl(inp, records)

        report = check_balance(inp, threshold=0.10)
        assert "anxiety" in report.topic.imbalanced

    def test_balanced_not_flagged(self, tmp_path):
        records = [self._make_depression_record()] * 50 + [self._make_anxiety_record()] * 50
        inp = tmp_path / "data.jsonl"
        write_jsonl(inp, records)

        report = check_balance(inp, threshold=0.10)
        assert not report.topic.imbalanced

    def test_skips_blank_lines(self, tmp_path):
        rec = self._make_depression_record()
        inp = tmp_path / "data.jsonl"
        inp.write_text("\n" + json.dumps(rec) + "\n\n", encoding="utf-8")

        report = check_balance(inp)
        assert report.total == 1

    def test_skips_invalid_json(self, tmp_path):
        inp = tmp_path / "data.jsonl"
        inp.write_text(
            json.dumps(self._make_depression_record()) + "\n"
            "NOT VALID JSON\n",
            encoding="utf-8",
        )

        report = check_balance(inp)
        assert report.total == 1  # only the valid record counted

    def test_skips_record_without_messages(self, tmp_path):
        inp = tmp_path / "data.jsonl"
        inp.write_text(
            json.dumps({"bad_key": []}) + "\n"
            + json.dumps(self._make_depression_record()) + "\n",
            encoding="utf-8",
        )

        report = check_balance(inp)
        assert report.total == 1

    def test_to_dict_roundtrip(self, tmp_path):
        records = [self._make_depression_record(), self._make_anxiety_record()]
        inp = tmp_path / "data.jsonl"
        write_jsonl(inp, records)

        report = check_balance(inp)
        d = report.to_dict()
        assert d["total"] == 2
        assert isinstance(d["topic"]["counts"], dict)
        assert isinstance(d["language"]["counts"], dict)


# ---------------------------------------------------------------------------
# CLI tests — main()
# ---------------------------------------------------------------------------

class TestMain:
    def _make_records(self, n: int = 5) -> list[dict]:
        return [
            make_record([
                ("user", "I feel depressed and hopeless"),
                ("assistant", "Tell me more"),
                ("user", "It has been months"),
            ])
            for _ in range(n)
        ]

    def test_missing_input_returns_1(self, tmp_path):
        from check_balance import main

        result = main(["--input", str(tmp_path / "nonexistent.jsonl")])
        assert result == 1

    def test_balanced_run_returns_0(self, tmp_path):
        from check_balance import main

        # 50/50 depression/anxiety — balanced
        records = [
            make_record([
                ("user", "I have depression and feel hopeless"),
                ("assistant", "Tell me more"), ("user", "Every day"),
            ])
        ] * 50 + [
            make_record([
                ("user", "I have anxiety and panic attacks"),
                ("assistant", "I hear you"), ("user", "Frequently"),
            ])
        ] * 50

        inp = tmp_path / "data.jsonl"
        out_report = tmp_path / "report.json"
        with inp.open("w") as f:
            for r in records:
                f.write(json.dumps(r) + "\n")

        result = main(["--input", str(inp), "--report", str(out_report)])
        assert result == 0
        assert out_report.exists()

    def test_imbalanced_run_returns_2(self, tmp_path):
        from check_balance import main

        # All depression → length and language dimensions may be single-category,
        # which at 100% cannot be < 10%, but we force topic imbalance via tiny anxiety count
        records = [
            make_record([
                ("user", "I have depression and feel hopeless"),
                ("assistant", "Tell me more"), ("user", "Every day"),
            ])
        ] * 95 + [
            make_record([
                ("user", "I have anxiety and panic attacks"),
                ("assistant", "I hear you"), ("user", "Frequently"),
            ])
        ] * 5

        inp = tmp_path / "data.jsonl"
        with inp.open("w") as f:
            for r in records:
                f.write(json.dumps(r) + "\n")

        result = main(["--input", str(inp)])
        assert result == 2

    def test_report_json_written(self, tmp_path):
        from check_balance import main

        records = self._make_records(10)
        inp = tmp_path / "data.jsonl"
        report_path = tmp_path / "balance.json"
        with inp.open("w") as f:
            for r in records:
                f.write(json.dumps(r) + "\n")

        main(["--input", str(inp), "--report", str(report_path)])

        assert report_path.exists()
        data = json.loads(report_path.read_text())
        assert "total" in data
        assert "topic" in data
        assert data["total"] == 10

    def test_empty_dataset_returns_1(self, tmp_path):
        from check_balance import main

        inp = tmp_path / "empty.jsonl"
        inp.write_text("", encoding="utf-8")

        result = main(["--input", str(inp)])
        assert result == 1

    def test_invalid_threshold_returns_1(self, tmp_path):
        from check_balance import main

        records = self._make_records(3)
        inp = tmp_path / "data.jsonl"
        with inp.open("w") as f:
            for r in records:
                f.write(json.dumps(r) + "\n")

        result = main(["--input", str(inp), "--threshold", "1.5"])
        assert result == 1
