"""
Pre-Merge Validation Script
Run this BEFORE combining datasets
"""

import pandas as pd
import numpy as np

# Load datasets
phase1 = pd.read_csv('phase_1_suicidal_ideation_1500_FIXED.csv', encoding='utf-8')
phase2 = pd.read_csv('phase_2_high_risk_2000_FIXED.csv', encoding='utf-8')

print("="*70)
print("PRE-MERGE VALIDATION")
print("="*70)

# Check 1: Record counts
print(f"\n Phase 1 records: {len(phase1)} (expected: 1,500)")
print(f" Phase 2 records: {len(phase2)} (expected: 2,000)")

# Check 2: Schema match
phase1_cols = set(phase1.columns)
phase2_cols = set(phase2.columns)

if phase1_cols == phase2_cols:
    print(f" Schema match: {len(phase1_cols)} columns")
else:
    print(f" Schema mismatch!")
    print(f"   Only in Phase 1: {phase1_cols - phase2_cols}")
    print(f"   Only in Phase 2: {phase2_cols - phase1_cols}")

# Check 3: ID ranges
print(f"\n Phase 1 ID range: {phase1['id'].min()} → {phase1['id'].max()}")
print(f" Phase 2 ID range: {phase2['id'].min()} → {phase2['id'].max()}")

# Check 4: No overlapping IDs
overlap = set(phase1['id']).intersection(set(phase2['id']))
if len(overlap) == 0:
    print(" No overlapping IDs")
else:
    print(f" Overlapping IDs found: {len(overlap)}")

# Check 5: Severity distributions
print("\n Phase 1 Severity Distribution:")
print(phase1['severity_score'].value_counts().sort_index())

print("\n Phase 2 Severity Distribution:")
print(phase2['severity_score'].value_counts().sort_index())

# Check 6: Crisis type distributions
print("\n Phase 1 Crisis Types:")
print(phase1['crisis_label'].value_counts())

print("\n Phase 2 Crisis Types:")
print(phase2['crisis_label'].value_counts())

print("\n" + "="*70)
print("VALIDATION COMPLETE - Ready for merge if all checks passed")
print("="*70)