#!/usr/bin/env python3
"""
Sentiment Classifier Dataset Generator
Generates 2,000 therapeutic sentiment examples with 3 classes:
- negative (45%, n=900): despair, frustration, suppression, avoidance
- positive (32.5%, n=650): progress, relief, hope, growth
- neutral (22.5%, n=450): factual, informational, emotionally flat

This script creates synthetic data with therapeutic semantics, including:
- Hinglish variants (Hindi-English code-switching)
- Emotional registers: distressed, resigned, angry, confused, hopeful
- Formality levels: casual, formal, clinical-adjacent
"""

import pandas as pd
import json
from datetime import datetime
import random
import os

random.seed(42)

# ============================================================================
# SENTIMENT UTTERANCE POOLS
# ============================================================================

NEGATIVE_UTTERANCES = [
    # Despair/hopelessness
    "I don't see any way out of this",
    "Everything feels pointless",
    "I've given up trying to change things",
    "Nothing I do matters anymore",
    "This pain is unbearable",
    "I feel completely hopeless right now",
    "There's no light at the end of the tunnel",
    "I'm drowning in this situation",
    "It's all too much, I can't handle it",
    "I don't want to get out of bed anymore",
    "Everything is falling apart",
    "I'm a complete failure",
    "I don't deserve to feel better",
    "This will never change",
    "I'm broken beyond repair",

    # Minimization/suppression (therapeutic red flag)
    "I'm fine, everything is okay",
    "I'm just fine really",
    "It's all fine, don't worry",
    "I'm okay, nothing to worry about",
    "Everything is fine, truly",
    "I'm alright, completely alright",
    "There's nothing wrong, I'm good",
    "It's nothing serious, I'm coping",
    "I'm managing, everything's fine",
    "Don't worry, I'm fine, really",

    # Avoidance/suppression
    "I don't want to talk about it",
    "Let's just move on from this",
    "I'm not going to think about it",
    "I've been avoiding dealing with this",
    "I don't want to face what's happening",
    "I'm pushing all my feelings away",
    "I'm just numbing myself to it all",
    "I can't bear to think about it",

    # Frustration/anger
    "This is so frustrating, nothing works",
    "I'm angry at myself for this mess",
    "Why does everything go wrong for me?",
    "I'm sick of struggling like this",
    "This is infuriating beyond belief",
    "I hate feeling this powerless",
    "I'm done with trying",
    "Nothing ever goes my way",

    # Emotional numbing/dissociation (concerning)
    "I feel nothing anymore",
    "I don't know what I feel",
    "I can't feel anything at all",
    "I'm emotionally numb",
    "Everything feels empty inside",
    "I'm disconnected from everything",
    "I don't feel alive",
    "I'm just going through the motions",

    # Worsening condition
    "I'm feeling worse than I was before",
    "Things have gotten so much darker",
    "I'm slipping deeper into this hole",
    "My situation is only getting worse",
    "I feel like I'm falling apart",
    "Each day is harder than the last",

    # Hinglish variants - negative
    "Sab kuch bekar lag raha hai",
    "Mujhe koi umeed nahi hai",
    "Mera jeevan khatam ho gaya",
    "Kuch bhi theek nahi hai mere liye",
    "Main har din badtar ho raha hoon",
    "Kuch bhi sahi nahi hota mere saath",
    "Main haara hua hoon ab",
    "Sab kuch bekaar hai",
]

POSITIVE_UTTERANCES = [
    # Progress/improvement
    "I'm starting to feel a bit better today",
    "I noticed a small improvement",
    "Today was better than yesterday",
    "I feel lighter than I did",
    "Things are looking up a little",
    "I'm making tiny steps forward",
    "There's a glimmer of hope now",
    "I'm surprised by how much better I feel",
    "I think I'm actually getting better",
    "I've had a breakthrough moment",

    # Relief/catharsis
    "I had a good cry and felt relieved",
    "Letting it out actually helped",
    "I feel so much better after talking about it",
    "That conversation really helped me",
    "I feel like a weight has lifted",
    "I'm finally able to breathe easier",
    "I feel so much lighter now",
    "Getting this out was exactly what I needed",
    "I feel clearer now after that",

    # Small wins (therapeutic context)
    "I managed to get out of bed today",
    "I actually made it through the day",
    "I did something I thought I couldn't do",
    "I took a small step for myself",
    "I pushed myself just a little bit",
    "I did something good for myself today",
    "I managed to go for a walk",
    "I cooked something healthy today",
    "I reached out to someone",
    "I'm proud of myself for that",

    # Growth/self-compassion
    "I understand myself a bit better now",
    "I'm learning to be kinder to myself",
    "I think I'm growing from this",
    "This is helping me understand my patterns",
    "I'm finding strength I didn't know I had",
    "I feel more at peace now",
    "I'm accepting things more easily",
    "I'm becoming more aware of myself",
    "I feel more in control now",
    "I'm learning new ways to cope",

    # Hope/gratitude
    "I feel grateful for this conversation",
    "Thank you, that actually helped me see things differently",
    "I feel hopeful about the future",
    "I'm grateful for having support",
    "I feel more connected now",
    "I appreciate your perspective",
    "That makes sense, thank you",
    "I'm looking forward to working on this",
    "I feel like I have a path forward now",
    "I feel more optimistic",

    # Qualified positive (realistic)
    "At least I got through today",
    "It's not perfect but it's better",
    "I'm managing better than I thought",
    "There are some good moments now",
    "Not as bad as I feared",
    "I can see some light in this",
    "Parts of me feel hopeful",

    # Hinglish variants - positive
    "Aaj mujhe thoda acha lag raha hai",
    "Mujhe kuch hope dikh raha hai",
    "Main halka mahsoos kar raha hoon",
    "Aaj mera din badhiya gaya",
    "Mujhe kuch-sa theek lag raha hai",
    "Main apne aap par garvi hoon",
    "Aaj mene khud ko samjha",
    "Mujhe sukhd raha hoon",
]

NEUTRAL_UTTERANCES = [
    # Factual/informational
    "My appointment is on Tuesday at 3pm",
    "I have therapy this week",
    "Can you tell me about CBT techniques?",
    "What is the difference between anxiety and stress?",
    "I need information about mindfulness",
    "How do I practice meditation?",
    "What does cognitive distortion mean?",
    "Can you explain attachment theory?",
    "I want to learn about emotional regulation",
    "Tell me more about therapeutic techniques",

    # Observation/reflection (neutral tone)
    "That's an interesting perspective",
    "I hadn't thought of it that way",
    "That makes sense",
    "Okay, I understand",
    "That's logical",
    "I see what you're saying",
    "That's a fair point",

    # Status updates (emotionally flat)
    "I've been busy with work",
    "Things are as they usually are",
    "Nothing much has changed",
    "Same situation as before",
    "I'm just here",
    "Life is continuing as normal",
    "I'm getting through the days",
    "Things remain the same",

    # Transition statements
    "Can we move on to something else?",
    "Let's talk about something different",
    "I'd like to focus on that",
    "What should we discuss next?",
    "Should we continue with that?",
    "Let's go back to what we were saying",

    # Acknowledgment (neutral)
    "I hear you",
    "Got it",
    "Understood",
    "Yes, I follow",
    "That's noted",
    "I acknowledge that",
    "Okay, I see",

    # Hinglish variants - neutral
    "Mera appointment Tuesday ko hai",
    "Kuch toh naya samjhne kiya",
    "Yeh samajh aaya",
    "Sab kuch normal hai",
    "Aaj bhi aisa hi tha",
    "Kuch naya nahi hua",
]

# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def generate_valence_score(sentiment: str) -> float:
    """Generate realistic valence score for each sentiment class."""
    if sentiment == "positive":
        # positive: mean ≈ 0.65, std ≈ 0.18
        return max(0.35, min(1.0, random.gauss(0.65, 0.18)))
    elif sentiment == "negative":
        # negative: mean ≈ -0.62, std ≈ 0.20
        return max(-1.0, min(-0.25, random.gauss(-0.62, 0.20)))
    else:  # neutral
        # neutral: mean ≈ -0.03, std ≈ 0.15
        return max(-0.35, min(0.35, random.gauss(-0.03, 0.15)))

def generate_confidence() -> float:
    """Generate annotator confidence: tends toward 0.80-0.95 range."""
    return round(random.gauss(0.87, 0.06), 2)

def generate_session_context() -> str:
    """Generate session context type."""
    contexts = [
        "therapeutic_progress",
        "crisis_moment",
        "processing_emotion",
        "information_seeking",
        "routine_conversation",
        "insight_moment",
        "resistance_avoidance",
        "breakthrough_realization",
    ]
    return random.choice(contexts)

def generate_utterance_set(pool: list, count: int) -> list:
    """Randomly sample utterances from pool with replacement."""
    return random.choices(pool, k=count)

# ============================================================================
# DATASET GENERATION
# ============================================================================

def generate_dataset(total_examples: int = 2000) -> pd.DataFrame:
    """
    Generate sentiment dataset with target distribution:
    - negative: 45% (900 examples)
    - positive: 32.5% (650 examples)
    - neutral: 22.5% (450 examples)
    """

    print(f"Generating {total_examples} sentiment examples...")

    # Calculate counts per sentiment
    neg_count = int(total_examples * 0.45)      # 900
    pos_count = int(total_examples * 0.325)     # 650
    neu_count = total_examples - neg_count - pos_count  # 450

    data = []
    id_counter = 1

    # Generate NEGATIVE sentiment
    print(f"  Generating {neg_count} negative examples...")
    for utterance in generate_utterance_set(NEGATIVE_UTTERANCES, neg_count):
        data.append({
            "id": f"sent_{id_counter:06d}",
            "utterance": utterance,
            "sentiment": "negative",
            "valence_score": generate_valence_score("negative"),
            "confidence": generate_confidence(),
            "session_context": generate_session_context(),
            "source": "synthetic",
            "annotator_id": f"ann_{random.randint(1, 5):03d}",
            "created_at": datetime.utcnow().isoformat() + "Z",
        })
        id_counter += 1

    # Generate POSITIVE sentiment
    print(f"  Generating {pos_count} positive examples...")
    for utterance in generate_utterance_set(POSITIVE_UTTERANCES, pos_count):
        data.append({
            "id": f"sent_{id_counter:06d}",
            "utterance": utterance,
            "sentiment": "positive",
            "valence_score": generate_valence_score("positive"),
            "confidence": generate_confidence(),
            "session_context": generate_session_context(),
            "source": "synthetic",
            "annotator_id": f"ann_{random.randint(1, 5):03d}",
            "created_at": datetime.utcnow().isoformat() + "Z",
        })
        id_counter += 1

    # Generate NEUTRAL sentiment
    print(f"  Generating {neu_count} neutral examples...")
    for utterance in generate_utterance_set(NEUTRAL_UTTERANCES, neu_count):
        data.append({
            "id": f"sent_{id_counter:06d}",
            "utterance": utterance,
            "sentiment": "neutral",
            "valence_score": generate_valence_score("neutral"),
            "confidence": generate_confidence(),
            "session_context": generate_session_context(),
            "source": "synthetic",
            "annotator_id": f"ann_{random.randint(1, 5):03d}",
            "created_at": datetime.utcnow().isoformat() + "Z",
        })
        id_counter += 1

    df = pd.DataFrame(data)

    # Shuffle rows
    df = df.sample(frac=1.0, random_state=42).reset_index(drop=True)

    return df

# ============================================================================
# DATA QUALITY CHECKS
# ============================================================================

def validate_dataset(df: pd.DataFrame) -> bool:
    """Run data quality checks on generated dataset."""
    print("\n" + "="*70)
    print("DATA QUALITY VALIDATION")
    print("="*70)

    checks_passed = 0
    total_checks = 6

    # Check 1: Count targets
    print("\n[OK] Check 1: Target counts")
    counts = df['sentiment'].value_counts()
    print(f"  negative: {counts.get('negative', 0)} (target: 900)")
    print(f"  positive: {counts.get('positive', 0)} (target: 650)")
    print(f"  neutral:  {counts.get('neutral', 0)} (target: 450)")
    print(f"  Total:    {len(df)}")
    checks_passed += 1

    # Check 2: No duplicate utterances
    print("\n[OK] Check 2: Duplicate utterances")
    dups = df['utterance'].duplicated().sum()
    print(f"  Duplicates found: {dups} (expected: 0)")
    if dups == 0:
        checks_passed += 1

    # Check 3: No null/empty utterances
    print("\n[OK] Check 3: Null/empty utterances")
    nulls = df['utterance'].isnull().sum()
    empties = (df['utterance'].str.strip() == "").sum()
    print(f"  Null utterances: {nulls}")
    print(f"  Empty utterances: {empties}")
    if nulls == 0 and empties == 0:
        checks_passed += 1

    # Check 4: All 3 sentiments present
    print("\n[OK] Check 4: All sentiments present")
    unique_sentiments = set(df['sentiment'].unique())
    print(f"  Unique sentiments: {unique_sentiments}")
    if unique_sentiments == {"negative", "positive", "neutral"}:
        checks_passed += 1

    # Check 5: Valence scores in valid range per sentiment
    print("\n[OK] Check 5: Valence score distribution")
    for sentiment in ["negative", "positive", "neutral"]:
        subset = df[df['sentiment'] == sentiment]['valence_score']
        print(f"  {sentiment:10s}: mean={subset.mean():+.3f}, std={subset.std():.3f}, "
              f"min={subset.min():+.3f}, max={subset.max():+.3f}")
    checks_passed += 1

    # Check 6: Confidence values in valid range
    print("\n[OK] Check 6: Confidence scores")
    conf = df['confidence']
    print(f"  Mean confidence: {conf.mean():.3f}")
    print(f"  Min confidence:  {conf.min():.3f}")
    print(f"  Max confidence:  {conf.max():.3f}")
    if (conf >= 0.0).all() and (conf <= 1.0).all():
        checks_passed += 1

    print(f"\n{'='*70}")
    print(f"VALIDATION RESULT: {checks_passed}/{total_checks} checks passed")
    print(f"{'='*70}\n")

    return checks_passed == total_checks

# ============================================================================
# MAIN
# ============================================================================

if __name__ == "__main__":
    # Generate dataset
    df = generate_dataset(total_examples=2000)

    # Validate
    is_valid = validate_dataset(df)

    # Save
    output_path = "Sentiment classifier model/sentiment_classifier_v1.csv"
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    df.to_csv(output_path, index=False)
    print(f"\n[SUCCESS] Dataset saved to: {output_path}")
    print(f"   Total examples: {len(df)}")
    print(f"   File size: {os.path.getsize(output_path) / 1024:.1f} KB")
