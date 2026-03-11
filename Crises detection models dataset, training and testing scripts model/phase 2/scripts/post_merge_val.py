"""
Post-Merge Validation Script
Ensures combined dataset is ready for training
"""

import pandas as pd
import numpy as np

# Load combined dataset
df = pd.read_csv('combined_crisis_dataset_3500.csv', encoding='utf-8')

print("="*70)
print("POST-MERGE VALIDATION")
print("="*70)

# Validation 1: Record count
expected = 3500
actual = len(df)
status = "okay" if actual == expected else "not okay"
print(f"\n{status} Record Count: {actual} (expected: {expected})")

# Validation 2: ID continuity
ids = df['id'].tolist()
expected_ids = [f"crisis_{str(i).zfill(6)}" for i in range(1, 3501)]
missing = set(expected_ids) - set(ids)
extra = set(ids) - set(expected_ids)

if len(missing) == 0 and len(extra) == 0:
    print(" ID Continuity: All IDs present (crisis_000001 → crisis_003500)")
else:
    print(f" ID Issues: {len(missing)} missing, {len(extra)} extra")

# Validation 3: No null values in critical columns
critical_cols = ['id', 'utterance', 'crisis_label', 'severity_score', 'high_risk_flag']
null_counts = df[critical_cols].isnull().sum()
if null_counts.sum() == 0:
    print(" No Null Values: All critical columns complete")
else:
    print(f" Null Values Found:")
    for col, count in null_counts.items():
        if count > 0:
            print(f"   {col}: {count} nulls")

# Validation 4: Crisis type distribution
print("\n Crisis Type Distribution:")
crisis_expected = {
    'suicidal_ideation': 1500,
    'suicide_plan': 800,
    'suicide_attempt': 500,
    'self_harm': 700
}
crisis_actual = df['crisis_label'].value_counts().to_dict()

all_match = True
for crisis, expected_count in crisis_expected.items():
    actual_count = crisis_actual.get(crisis, 0)
    status = "okay" if actual_count == expected_count else "not okay"
    if actual_count != expected_count:
        all_match = False
    print(f"   {status} {crisis}: {actual_count} (expected: {expected_count})")

# Validation 5: High-risk count
high_risk_count = df['high_risk_flag'].sum()
expected_high_risk = 150 + 800 + 500  # Phase 1 (0.9) + suicide_plan + suicide_attempt
status = "ok" if high_risk_count == expected_high_risk else "⚠️"
print(f"\n{status} High-Risk Records: {high_risk_count} (expected: ~{expected_high_risk})")

# Validation 6: Schema completeness
expected_cols = 25
actual_cols = len(df.columns)
status = "ok" if actual_cols == expected_cols else "not okay"
print(f"{status} Schema: {actual_cols} columns (expected: {expected_cols})")

# Final verdict
print("\n" + "="*70)
if all_match and len(missing) == 0 and null_counts.sum() == 0:
    print(" VALIDATION PASSED - Dataset ready for training")
else:
    print(" VALIDATION WARNINGS - Review issues above")
print("="*70)