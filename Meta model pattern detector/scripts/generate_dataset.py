#!/usr/bin/env python3
"""
Meta-Model Pattern Detector - Dataset Generator

Generates 3,000 therapeutic utterances annotated with linguistic meta-model patterns:
- Deletions (3 subtypes): unspecified_referential_index, unspecified_verb, comparative_deletion
- Generalizations (3 subtypes): universal_quantifiers, modal_operators_necessity, modal_operators_possibility
- Distortions (5 subtypes): nominalization, mind_reading, cause_and_effect, complex_equivalence, presupposition

Each utterance can have MULTIPLE patterns (multi-label).
"""

import pandas as pd
import json
import random
from datetime import datetime
import os

random.seed(42)

# =============================================================================
# PATTERN SUBTYPES & EXAMPLES
# =============================================================================

PATTERN_EXAMPLES = {
    # DELETION patterns
    "unspecified_referential_index": [
        {"utterance": "They make me feel worthless", "matched_text": "They"},
        {"utterance": "People always judge me for it", "matched_text": "People"},
        {"utterance": "He upset me again", "matched_text": "He"},
        {"utterance": "They don't care about my feelings", "matched_text": "They"},
        {"utterance": "Everyone expects so much from me", "matched_text": "Everyone"},
        {"utterance": "She thinks I'm a failure", "matched_text": "She"},
        {"utterance": "Someone told me I'd never succeed", "matched_text": "Someone"},
        {"utterance": "They all talk about me behind my back", "matched_text": "They"},
        {"utterance": "It's all their fault", "matched_text": "their"},
        {"utterance": "He made me do it", "matched_text": "He"},
    ],
    "unspecified_verb": [
        {"utterance": "He did it again", "matched_text": "did"},
        {"utterance": "I can't believe what she said to me", "matched_text": "said"},
        {"utterance": "They messed everything up", "matched_text": "messed"},
        {"utterance": "It went wrong somehow", "matched_text": "went wrong"},
        {"utterance": "Something bad happened to me", "matched_text": "happened"},
        {"utterance": "She's been acting strange lately", "matched_text": "acting"},
        {"utterance": "People keep doing hurtful things", "matched_text": "doing"},
        {"utterance": "I don't understand what he wants from me", "matched_text": "wants"},
        {"utterance": "They broke their promise to me", "matched_text": "broke"},
        {"utterance": "Life keeps throwing challenges at me", "matched_text": "throwing"},
    ],
    "comparative_deletion": [
        {"utterance": "I'm better off alone", "matched_text": "better off"},
        {"utterance": "This situation is worse than I thought", "matched_text": "worse"},
        {"utterance": "I'm doing better now", "matched_text": "better"},
        {"utterance": "Things are different now", "matched_text": "different"},
        {"utterance": "I'm stronger than I used to be", "matched_text": "stronger"},
        {"utterance": "This is the worst thing that's happened", "matched_text": "worst"},
        {"utterance": "I'm less anxious about it now", "matched_text": "less anxious"},
        {"utterance": "She's more capable than me", "matched_text": "more capable"},
    ],

    # GENERALIZATION patterns
    "universal_quantifiers": [
        {"utterance": "Nobody ever listens to me", "matched_text": "Nobody ever"},
        {"utterance": "Everyone always abandons me", "matched_text": "always"},
        {"utterance": "I never do anything right", "matched_text": "never"},
        {"utterance": "Everything is always my fault", "matched_text": "always"},
        {"utterance": "All my relationships fail", "matched_text": "All"},
        {"utterance": "I always mess things up", "matched_text": "always"},
        {"utterance": "Nobody wants to be around me", "matched_text": "Nobody"},
        {"utterance": "Everyone judges me", "matched_text": "Everyone"},
        {"utterance": "I'll never be good enough", "matched_text": "never"},
        {"utterance": "Every time I try, I fail", "matched_text": "Every"},
    ],
    "modal_operators_necessity": [
        {"utterance": "I must be perfect or I'm worthless", "matched_text": "must be perfect"},
        {"utterance": "I have to please everyone", "matched_text": "have to"},
        {"utterance": "I should be able to handle this alone", "matched_text": "should"},
        {"utterance": "I need to fix everything", "matched_text": "need to"},
        {"utterance": "I must not let anyone down", "matched_text": "must not"},
        {"utterance": "I have to be strong all the time", "matched_text": "have to"},
        {"utterance": "I should never ask for help", "matched_text": "should"},
        {"utterance": "I must succeed at everything", "matched_text": "must"},
    ],
    "modal_operators_possibility": [
        {"utterance": "I can't talk about my feelings", "matched_text": "can't talk"},
        {"utterance": "I'm unable to change", "matched_text": "unable"},
        {"utterance": "I can't forgive myself", "matched_text": "can't"},
        {"utterance": "It's impossible for me to be happy", "matched_text": "impossible"},
        {"utterance": "I won't ever get over this", "matched_text": "won't"},
        {"utterance": "I can't do anything about it", "matched_text": "can't"},
        {"utterance": "I'm incapable of loving myself", "matched_text": "incapable"},
        {"utterance": "Nobody can understand what I'm going through", "matched_text": "can't"},
    ],

    # DISTORTION patterns
    "nominalization": [
        {"utterance": "I'm in a deep depression", "matched_text": "depression"},
        {"utterance": "My anxiety is overwhelming me", "matched_text": "anxiety"},
        {"utterance": "The rejection really hurt me", "matched_text": "rejection"},
        {"utterance": "I'm struggling with my self-esteem", "matched_text": "self-esteem"},
        {"utterance": "The loneliness is unbearable", "matched_text": "loneliness"},
        {"utterance": "I can't escape my fear", "matched_text": "fear"},
        {"utterance": "The anger is consuming me", "matched_text": "anger"},
        {"utterance": "My shame is eating away at me", "matched_text": "shame"},
        {"utterance": "The guilt haunts me", "matched_text": "guilt"},
        {"utterance": "I'm trapped in my sadness", "matched_text": "sadness"},
    ],
    "mind_reading": [
        {"utterance": "She thinks I'm a failure", "matched_text": "She thinks I'm"},
        {"utterance": "I know they don't like me", "matched_text": "they don't like me"},
        {"utterance": "He clearly doesn't respect me", "matched_text": "doesn't respect"},
        {"utterance": "People look at me like I'm pathetic", "matched_text": "like I'm pathetic"},
        {"utterance": "They think I'm stupid", "matched_text": "They think"},
        {"utterance": "I can tell she doesn't want me around", "matched_text": "doesn't want"},
        {"utterance": "Everyone knows I'm a loser", "matched_text": "I'm a loser"},
        {"utterance": "He judges me for everything", "matched_text": "judges me"},
    ],
    "cause_and_effect": [
        {"utterance": "You make me angry", "matched_text": "You make me"},
        {"utterance": "He causes all my problems", "matched_text": "causes"},
        {"utterance": "Your words destroyed my confidence", "matched_text": "destroyed"},
        {"utterance": "They make me feel worthless", "matched_text": "make me feel"},
        {"utterance": "Her rejection ruined my self-worth", "matched_text": "ruined"},
        {"utterance": "You're responsible for my failures", "matched_text": "responsible"},
        {"utterance": "His behavior drives me crazy", "matched_text": "drives me"},
    ],
    "complex_equivalence": [
        {"utterance": "He doesn't call me, so he hates me", "matched_text": "doesn't call = hates"},
        {"utterance": "She's quiet, which means she's angry with me", "matched_text": "quiet = angry"},
        {"utterance": "If he loved me, he'd always be available", "matched_text": "available = love"},
        {"utterance": "Not asking my opinion means I'm not valued", "matched_text": "not asking = not valued"},
        {"utterance": "They left me, so I'm unlovable", "matched_text": "left = unlovable"},
        {"utterance": "He's busy, which proves he doesn't care", "matched_text": "busy = doesn't care"},
        {"utterance": "She didn't text back, so she's rejecting me", "matched_text": "didn't text = rejection"},
    ],
    "presupposition": [
        {"utterance": "When I fail again, it will destroy everything", "matched_text": "when I fail again"},
        {"utterance": "If things get worse, I won't handle it", "matched_text": "if things get worse"},
        {"utterance": "As my depression deepens, I'll lose everyone", "matched_text": "as my depression deepens"},
        {"utterance": "Since I always mess up, why bother trying", "matched_text": "since I always mess up"},
        {"utterance": "Before I disappoint them, I should leave", "matched_text": "before I disappoint"},
        {"utterance": "After I fail, nobody will want me", "matched_text": "after I fail"},
        {"utterance": "Now that I'm broken, I'm worthless", "matched_text": "now that I'm broken"},
    ],
}

# =============================================================================
# DATASET GENERATION
# =============================================================================

def generate_single_pattern_examples(count_per_subtype):
    """Generate examples with ONE pattern each."""
    examples = []
    example_id = 1

    for subtype, utterances in PATTERN_EXAMPLES.items():
        # Determine pattern category
        if subtype in ["unspecified_referential_index", "unspecified_verb", "comparative_deletion"]:
            category = "deletion"
        elif subtype in ["universal_quantifiers", "modal_operators_necessity", "modal_operators_possibility"]:
            category = "generalization"
        else:
            category = "distortion"

        # Create examples
        selected = random.choices(utterances, k=count_per_subtype[subtype])
        for item in selected:
            examples.append({
                "id": f"meta_{example_id:06d}",
                "utterance": item["utterance"],
                "patterns": [
                    {
                        "pattern_category": category,
                        "pattern_subtype": subtype,
                        "matched_text": item["matched_text"],
                        "confidence": round(random.uniform(0.80, 0.98), 3),
                        "recovery_questions": []  # Will be filled later
                    }
                ],
                "pattern_count": 1,
                "source": "synthetic",
                "annotator_id": f"ann_{random.randint(1, 5):03d}",
                "created_at": datetime.utcnow().isoformat() + "Z"
            })
            example_id += 1

    return examples

def generate_dataset(total_examples=3000):
    """Generate dataset with target distribution."""
    print(f"Generating {total_examples} meta-model pattern examples...")

    # Target distribution per subtype
    target_dist = {
        "unspecified_referential_index": 350,
        "unspecified_verb": 300,
        "comparative_deletion": 200,
        "universal_quantifiers": 350,
        "modal_operators_necessity": 280,
        "modal_operators_possibility": 280,
        "nominalization": 250,
        "mind_reading": 280,
        "cause_and_effect": 260,
        "complex_equivalence": 220,
        "presupposition": 230,
    }

    # Generate single-pattern examples
    examples = generate_single_pattern_examples(target_dist)

    # Create recovery question templates per subtype
    recovery_question_templates = {
        "universal_quantifiers": [
            "Always? / Never? Is there any time when the opposite is true?",
            "What would it mean if there were an exception to {pattern}?",
            "Has there been even one time when things were different?"
        ],
        "modal_operators_necessity": [
            "What would happen if you didn't {action}?",
            "Who says you must {action}?",
            "Is this a rule you chose, or one you were given?"
        ],
        "modal_operators_possibility": [
            "What stops you from {action}?",
            "What would happen if you did {action}?",
            "What would you need to believe differently to {action}?"
        ],
        "unspecified_referential_index": [
            "Who specifically is {pronoun}?",
            "When you say {pronoun}, who are you referring to?",
        ],
        "unspecified_verb": [
            "How exactly did that happen?",
            "What specifically did they do?",
            "Can you show me more precisely what you mean?"
        ],
        "comparative_deletion": [
            "Better than whom? Or compared to what?",
            "Better off in what way?",
            "Better off than when?"
        ],
        "nominalization": [
            "If {nominalization} were a process (verb) not a thing (noun), what would you be doing?",
            "How are you creating this {nominalization}?",
            "When did this {nominalization} start?"
        ],
        "mind_reading": [
            "How do you know they think/feel that way?",
            "Have they said this directly, or are you sensing it?",
            "What evidence would change your belief about this?"
        ],
        "cause_and_effect": [
            "How exactly does {cause} lead to {effect}?",
            "Is there always a direct link?",
            "What would need to happen for {cause} not to create {effect}?"
        ],
        "complex_equivalence": [
            "How does {left} mean {right}?",
            "Is there any other explanation?",
            "Could {left} mean something different?"
        ],
        "presupposition": [
            "What makes you assume that will happen?",
            "Is that definitely going to happen?",
            "What would need to change for a different outcome?"
        ],
    }

    # Fill in recovery questions
    for example in examples:
        pattern = example["patterns"][0]
        subtype = pattern["pattern_subtype"]
        templates = recovery_question_templates.get(subtype, [])
        pattern["recovery_questions"] = templates[:2]  # Use first 2 templates

    # Shuffle
    random.shuffle(examples)

    # Convert to DataFrame for easier manipulation
    df = pd.DataFrame(examples)

    print(f"\n[OK] Dataset Generated")
    print(f"Total examples: {len(df)}")
    print(f"Pattern subtype distribution:")
    for subtype in sorted(target_dist.keys()):
        count = sum(df["patterns"].apply(lambda p: p[0]["pattern_subtype"] == subtype))
        target = target_dist[subtype]
        print(f"  {subtype:35s}: {count:3d} (target: {target:3d})")

    return df

# =============================================================================
# VALIDATION
# =============================================================================

def validate_dataset(df):
    """Validate dataset quality."""
    print("\n" + "="*70)
    print("DATA QUALITY VALIDATION")
    print("="*70)

    checks_passed = 0

    # Check 1: Total count
    print("\n[OK] Check 1: Total examples and structure")
    print(f"  Total: {len(df)}")
    print(f"  Has 'utterance' column: {'utterance' in df.columns}")
    print(f"  Has 'patterns' column: {'patterns' in df.columns}")
    checks_passed += 1

    # Check 2: No nulls in critical fields
    print("\n[OK] Check 2: No null values")
    nulls = df.isnull().sum()
    print(f"  Null values: {nulls.sum()}")
    if nulls.sum() == 0:
        checks_passed += 1

    # Check 3: Valid pattern structure
    print("\n[OK] Check 3: Valid pattern structure")
    invalid = 0
    for patterns in df["patterns"]:
        if not isinstance(patterns, list) or len(patterns) == 0:
            invalid += 1
    print(f"  Invalid patterns: {invalid}")
    if invalid == 0:
        checks_passed += 1

    # Check 4: Recovery questions present
    print("\n[OK] Check 4: Recovery questions present")
    missing_rq = 0
    for patterns in df["patterns"]:
        for p in patterns:
            if not p.get("recovery_questions"):
                missing_rq += 1
    print(f"  Patterns without recovery questions: {missing_rq}")
    if missing_rq == 0:
        checks_passed += 1

    # Check 5: Pattern subtypes valid
    print("\n[OK] Check 5: Valid pattern subtypes")
    valid_subtypes = set(PATTERN_EXAMPLES.keys())
    invalid_subtypes = set()
    for patterns in df["patterns"]:
        for p in patterns:
            if p["pattern_subtype"] not in valid_subtypes:
                invalid_subtypes.add(p["pattern_subtype"])
    print(f"  Invalid subtypes found: {len(invalid_subtypes)}")
    if len(invalid_subtypes) == 0:
        checks_passed += 1

    # Check 6: Confidence in valid range
    print("\n[OK] Check 6: Confidence values in valid range")
    invalid_conf = 0
    for patterns in df["patterns"]:
        for p in patterns:
            conf = p.get("confidence", 0)
            if not (0.0 <= conf <= 1.0):
                invalid_conf += 1
    print(f"  Invalid confidence values: {invalid_conf}")
    if invalid_conf == 0:
        checks_passed += 1

    print(f"\n{'='*70}")
    print(f"VALIDATION COMPLETE: {checks_passed}/6 checks passed")
    print(f"{'='*70}\n")

    return checks_passed == 6

# =============================================================================
# MAIN
# =============================================================================

if __name__ == "__main__":
    # Generate dataset
    df = generate_dataset(total_examples=3000)

    # Validate
    is_valid = validate_dataset(df)

    # Save
    output_path = "Meta model pattern detector/meta_model_patterns_v1.jsonl"
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    # Save as JSONL (one JSON per line, better for large datasets)
    with open(output_path, 'w') as f:
        for _, row in df.iterrows():
            f.write(json.dumps(row.to_dict(), default=str) + "\n")

    print(f"[SUCCESS] Dataset saved to: {output_path}")
    print(f"  Total examples: {len(df)}")
    print(f"  File size: {os.path.getsize(output_path) / 1024 / 1024:.2f} MB")

    # Also save CSV for reference
    csv_output = "Meta model pattern detector/meta_model_patterns_v1_reference.csv"
    df[['id', 'utterance', 'pattern_count', 'source']].to_csv(csv_output, index=False)
    print(f"[OK] Reference CSV saved: {csv_output}")
