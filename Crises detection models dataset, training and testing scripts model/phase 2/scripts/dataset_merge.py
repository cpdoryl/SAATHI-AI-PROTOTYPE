"""
CPDO APPROVED: Combined Dataset Creation Script
================================================
Merges Phase 1 and Phase 2 datasets into a single training dataset

Author: CPDO Team
Date: December 29, 2025
"""

import pandas as pd
import numpy as np
from datetime import datetime
import json

# ═══════════════════════════════════════════════════════════════
# CONFIGURATION
# ═══════════════════════════════════════════════════════════════

PHASE1_PATH = 'phase_1_suicidal_ideation_1500_FIXED.csv'
PHASE2_PATH = 'phase_2_high_risk_2000_FIXED.csv'
OUTPUT_PATH = 'combined_crisis_dataset_3500.csv'
MANIFEST_PATH = 'combined_dataset_manifest.json'

# ═══════════════════════════════════════════════════════════════
# MERGE FUNCTION
# ═══════════════════════════════════════════════════════════════

def merge_datasets():
    """
    Merge Phase 1 and Phase 2 datasets with validation.
    """
    print("="*70)
    print(" COMBINING PHASE 1 + PHASE 2 DATASETS")
    print("="*70)
    
    # Load datasets
    print("\n Loading datasets...")
    phase1 = pd.read_csv(PHASE1_PATH, encoding='utf-8')
    phase2 = pd.read_csv(PHASE2_PATH, encoding='utf-8')
    
    print(f"   Phase 1: {len(phase1)} records")
    print(f"   Phase 2: {len(phase2)} records")
    
    # Validate schemas match
    if list(phase1.columns) != list(phase2.columns):
        # Reorder Phase 2 columns to match Phase 1
        phase2 = phase2[phase1.columns]
        print("    Reordered Phase 2 columns to match Phase 1")
    
    # Concatenate
    print("\n Merging datasets...")
    combined = pd.concat([phase1, phase2], ignore_index=False)
    
    # Verify no duplicate IDs
    if combined['id'].duplicated().any():
        print("    ERROR: Duplicate IDs found!")
        duplicates = combined[combined['id'].duplicated()]['id'].tolist()
        print(f"   Duplicates: {duplicates[:10]}...")
        return None
    
    print(f"  combined: {len(combined)} records")
    
    # Sort by ID for consistency
    combined = combined.sort_values('id').reset_index(drop=True)
    
    # Validate combined dataset
    print("\n Combined Dataset Statistics:")
    print(f"   Total Records: {len(combined)}")
    print(f"   ID Range: {combined['id'].min()} → {combined['id'].max()}")
    
    print("\n   Crisis Type Distribution:")
    crisis_dist = combined['crisis_label'].value_counts()
    for crisis, count in crisis_dist.items():
        pct = count / len(combined) * 100
        print(f"      {crisis}: {count} ({pct:.1f}%)")
    
    print("\n   Severity Distribution:")
    severity_dist = combined['severity_score'].value_counts().sort_index()
    for sev, count in severity_dist.items():
        pct = count / len(combined) * 100
        print(f"      {sev}: {count} ({pct:.1f}%)")
    
    print("\n   High-Risk Distribution:")
    high_risk = combined['high_risk_flag'].value_counts()
    for flag, count in high_risk.items():
        pct = count / len(combined) * 100
        label = "HIGH-RISK" if flag else "Normal"
        print(f"      {label}: {count} ({pct:.1f}%)")
    
    # Save combined dataset
    print(f"\n Saving to {OUTPUT_PATH}...")
    combined.to_csv(OUTPUT_PATH, index=False, encoding='utf-8')
    print("    Dataset saved successfully")
    
    # Create manifest
    manifest = {
        "created_at": datetime.now().isoformat(),
        "created_by": "CPDO",
        "version": "1.0",
        "sources": {
            "phase1": {
                "file": PHASE1_PATH,
                "records": len(phase1),
                "crisis_types": phase1['crisis_label'].unique().tolist()
            },
            "phase2": {
                "file": PHASE2_PATH,
                "records": len(phase2),
                "crisis_types": phase2['crisis_label'].unique().tolist()
            }
        },
        "combined": {
            "file": OUTPUT_PATH,
            "total_records": len(combined),
            "crisis_types": combined['crisis_label'].unique().tolist(),
            "severity_levels": sorted(combined['severity_score'].unique().tolist()),
            "high_risk_count": int(combined['high_risk_flag'].sum()),
            "high_risk_percentage": round(combined['high_risk_flag'].mean() * 100, 2)
        },
        "schema": {
            "columns": list(combined.columns),
            "column_count": len(combined.columns)
        }
    }
    
    with open(MANIFEST_PATH, 'w') as f:
        json.dump(manifest, f, indent=2)
    print(f"    Manifest saved to {MANIFEST_PATH}")
    
    print("\n" + "="*70)
    print(" DATASET MERGE COMPLETE")
    print("="*70)
    
    return combined

# ═══════════════════════════════════════════════════════════════
# MAIN EXECUTION
# ═══════════════════════════════════════════════════════════════

if __name__ == "__main__":
    combined_df = merge_datasets()