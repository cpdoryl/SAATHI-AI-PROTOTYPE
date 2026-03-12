#!/usr/bin/env python3
"""
Meta-Model Pattern Detector - Seq2Seq Format Conversion

Converts JSONL data (raw meta-model patterns) to Seq2Seq format for Flan-T5 training.
Input: data/splits/{train,val,test}.jsonl
Output: data/seq2seq/{train,val,test}.json
"""

import json
import os
from pathlib import Path

FLAN_T5_INSTRUCTION = """Identify all linguistic meta-model patterns in the utterance.
Output format: CATEGORY|SUBTYPE|MATCHED_TEXT (one pattern per line)

Categories: deletion, generalization, distortion

Subtypes:
  deletion: unspecified_referential_index, unspecified_verb, comparative_deletion
  generalization: universal_quantifiers, modal_operators_necessity, modal_operators_possibility
  distortion: nominalization, mind_reading, cause_and_effect, complex_equivalence, presupposition

Utterance: {utterance}

Patterns:"""


def load_jsonl(path):
    """Load JSONL file into list of dicts."""
    data = []
    with open(path, 'r') as f:
        for line in f:
            if line.strip():
                data.append(json.loads(line.strip()))
    return data


def convert_example(raw_example):
    """Convert raw example to Seq2Seq format."""
    patterns_output = "\n".join([
        f"{p['pattern_category'].upper()}|{p['pattern_subtype']}|{p['matched_text']}"
        for p in raw_example.get('patterns', [])
    ])

    if not patterns_output.strip():
        patterns_output = "NONE"

    return {
        "input": FLAN_T5_INSTRUCTION.format(utterance=raw_example['utterance']),
        "output": patterns_output,
        "example_id": raw_example['id']
    }


def convert_split(input_path, output_path):
    """Convert a single split (train/val/test)."""
    print(f"Loading: {input_path}")
    data = load_jsonl(input_path)
    print(f"  Loaded {len(data)} examples")

    converted = [convert_example(ex) for ex in data]

    print(f"Saving: {output_path}")
    with open(output_path, 'w') as f:
        json.dump(converted, f, indent=2)

    print(f"  Saved {len(converted)} examples")
    return len(converted)


def convert_to_seq2seq_format(
    data_dir: str = "Meta model pattern detector/data/splits",
    output_dir: str = "Meta model pattern detector/data/seq2seq"
):
    """Convert all splits to Seq2Seq format."""

    print("=" * 70)
    print("CONVERTING DATA TO SEQ2SEQ FORMAT")
    print("=" * 70)

    # Create output directory
    os.makedirs(output_dir, exist_ok=True)

    # Convert each split
    splits = ["train", "val", "test"]
    total_examples = 0

    for split_name in splits:
        input_path = os.path.join(data_dir, f"{split_name}.jsonl")
        output_path = os.path.join(output_dir, f"{split_name}.json")

        if not os.path.exists(input_path):
            print(f"\n[ERROR] File not found: {input_path}")
            continue

        print(f"\n{split_name.upper()} SPLIT:")
        count = convert_split(input_path, output_path)
        total_examples += count

    print(f"\n{'=' * 70}")
    print(f"CONVERSION COMPLETE: {total_examples} total examples converted")
    print(f"Output directory: {output_dir}")
    print(f"{'=' * 70}\n")

    return True


if __name__ == "__main__":
    convert_to_seq2seq_format()
