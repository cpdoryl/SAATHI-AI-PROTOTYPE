"""
Crisis Detection Dataset - Exploration & Validation
===================================================
Loads Phase 1 dataset and performs initial analysis
"""
import os
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from collections import Counter

# Configuration
DATA_PATH = "../data/raw/phase1_suicidal_ideation.csv"
OUTPUT_DIR = "../results/plots"

def load_dataset():
    """Load and validate Phase 1 dataset"""
    print("Loading Phase 1 dataset...")
    df = pd.read_csv(DATA_PATH, encoding='utf-8')
    
    print(f"✅ Loaded {len(df)} records")
    print(f"✅ Columns: {len(df.columns)}")
    print(f"✅ Memory usage: {df.memory_usage(deep=True).sum() / 1024**2:.2f} MB")
    
    return df

def explore_severity_distribution(df):
    """Analyze severity score distribution"""
    print("\n" + "="*60)
    print("SEVERITY DISTRIBUTION ANALYSIS")
    print("="*60)
    
    severity_counts = df['severity_score'].value_counts().sort_index()
    
    for score, count in severity_counts.items():
        pct = (count / len(df)) * 100
        risk_label = get_risk_label(score)
        print(f"Severity {score} ({risk_label}): {count} records ({pct:.1f}%)")
    
    # Plot distribution
    plt.figure(figsize=(10, 6))
    severity_counts.plot(kind='bar', color=['green', 'yellow', 'orange', 'red'])
    plt.title('Phase 1: Severity Score Distribution')
    plt.xlabel('Severity Score')
    plt.ylabel('Number of Records')
    plt.xticks(rotation=0)
    plt.tight_layout()
    plt.savefig(f'{OUTPUT_DIR}/severity_distribution.png')
    print(f"\n✅ Saved plot: {OUTPUT_DIR}/severity_distribution.png")

def get_risk_label(score):
    """Map severity score to risk label"""
    if score <= 0.2:
        return "Passive Ideation"
    elif score <= 0.6:
        return "Active Ideation"
    elif score <= 0.7:
        return "Active with Method"
    else:
        return "Intent to Act (HIGH RISK)"

def analyze_language_distribution(df):
    """Analyze language code distribution"""
    print("\n" + "="*60)
    print("LANGUAGE DISTRIBUTION ANALYSIS")
    print("="*60)
    
    lang_counts = df['language_code'].value_counts()
    
    for lang, count in lang_counts.items():
        pct = (count / len(df)) * 100
        print(f"{lang}: {count} records ({pct:.1f}%)")
    
    # Plot distribution
    plt.figure(figsize=(10, 6))
    lang_counts.plot(kind='bar', color='skyblue')
    plt.title('Phase 1: Language Distribution')
    plt.xlabel('Language Code')
    plt.ylabel('Number of Records')
    plt.xticks(rotation=45)
    plt.tight_layout()
    plt.savefig(f'{OUTPUT_DIR}/language_distribution.png')
    print(f"\n✅ Saved plot: {OUTPUT_DIR}/language_distribution.png")

def analyze_demographics(df):
    """Analyze demographic balance"""
    print("\n" + "="*60)
    print("DEMOGRAPHIC DISTRIBUTION ANALYSIS")
    print("="*60)
    
    # Age groups
    print("\nAge Groups:")
    age_counts = df['age_group'].value_counts()
    for age, count in age_counts.items():
        pct = (count / len(df)) * 100
        print(f"  {age}: {count} ({pct:.1f}%)")
    
    # Gender
    print("\nGender:")
    gender_counts = df['gender'].value_counts()
    for gender, count in gender_counts.items():
        pct = (count / len(df)) * 100
        print(f"  {gender}: {count} ({pct:.1f}%)")
    
    # Socioeconomic
    print("\nSocioeconomic Context:")
    socio_counts = df['socioeconomic_context'].value_counts()
    for socio, count in socio_counts.items():
        pct = (count / len(df)) * 100
        print(f"  {socio}: {count} ({pct:.1f}%)")

def analyze_utterance_quality(df):
    """Analyze utterance text characteristics"""
    print("\n" + "="*60)
    print("UTTERANCE QUALITY ANALYSIS")
    print("="*60)
    
    df['utterance_length'] = df['utterance'].str.len()
    
    print(f"\nUtterance Statistics:")
    print(f"  Average length: {df['utterance_length'].mean():.1f} characters")
    print(f"  Min length: {df['utterance_length'].min()}")
    print(f"  Max length: {df['utterance_length'].max()}")
    print(f"  Median length: {df['utterance_length'].median():.1f}")
    
    # Sample utterances from each severity level
    print("\nSample Utterances by Severity:")
    for severity in sorted(df['severity_score'].unique()):
        sample = df[df['severity_score'] == severity].sample(1)
        print(f"\n  Severity {severity}:")
        print(f"    Utterance: {sample['utterance'].values[0]}")
        print(f"    Language: {sample['language_code'].values[0]}")
        print(f"    Risk Level: {sample.iloc[0]['clinical_scale']}")

def check_data_quality(df):
    """Check for data quality issues"""
    print("\n" + "="*60)
    print("DATA QUALITY CHECK")
    print("="*60)
    
    # Check for nulls
    null_counts = df.isnull().sum()
    if null_counts.sum() == 0:
        print("✅ No null values found")
    else:
        print("❌ Null values detected:")
        print(null_counts[null_counts > 0])
    
    # Check for duplicates
    duplicates = df.duplicated(subset=['id']).sum()
    if duplicates == 0:
        print("✅ No duplicate IDs found")
    else:
        print(f"❌ {duplicates} duplicate IDs found")
    
    # Check ID format
    id_format_ok = df['id'].str.match(r'^crisis_\d{6}$').all()
    if id_format_ok:
        print("✅ All IDs follow crisis_NNNNNN format")
    else:
        print("❌ Some IDs have incorrect format")
    
    # Check severity values
    expected_severities = [0.2, 0.6, 0.7, 0.9]
    actual_severities = df['severity_score'].unique()
    if set(actual_severities).issubset(set(expected_severities)):
        print("✅ All severity scores are valid")
    else:
        print(f"❌ Unexpected severity values: {set(actual_severities) - set(expected_severities)}")

def main():
    """Main execution"""
    print("="*60)
    print("CRISIS DETECTION DATASET - PHASE 1 EXPLORATION")
    print("="*60)
    
    # Load dataset
    df = load_dataset()
    
    # Run analyses
    explore_severity_distribution(df)
    analyze_language_distribution(df)
    analyze_demographics(df)
    analyze_utterance_quality(df)
    check_data_quality(df)
    
    print("\n" + "="*60)
    print("✅ EXPLORATION COMPLETE")
    print("="*60)
    print(f"\nDataset Summary:")
    print(f"  Total Records: {len(df)}")
    print(f"  Severity Levels: {len(df['severity_score'].unique())}")
    print(f"  Languages: {len(df['language_code'].unique())}")
    print(f"  High Risk Records: {(df['high_risk_flag'] == True).sum()}")
    print(f"\n  Ready for training: ✅")

if __name__ == "__main__":
    main()