#!/usr/bin/env python3
"""
Script to validate outcomes (True Accept, False Reject, False Accept, True Reject)
using stored threshold and system_decision.

Usage:
    python scripts/validate_outcomes.py
"""

import sys
from pathlib import Path
import pandas as pd

# Add parent directory to path
parent_dir = str(Path(__file__).parent.parent)
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

from app.analytics.metrics import AttendanceMetrics
from app.analytics.evaluation import AttendanceEvaluation


def main():
    print("=" * 60)
    print("OUTCOME VALIDATION")
    print("=" * 60)
    print()
    
    # Load data
    print("Loading attendance data...")
    metrics = AttendanceMetrics()
    df = metrics.load_attendance()
    
    if df.empty:
        print("No attendance data found.")
        return
    
    print(f"Total records: {len(df)}")
    print()
    
    # Check if required columns exist
    required_cols = ['threshold_used', 'system_decision', 'face_verified', 'recognition_score']
    missing_cols = [col for col in required_cols if col not in df.columns]
    
    if missing_cols:
        print(f"[WARNING] Missing columns: {missing_cols}")
        print("Some records may not have threshold_used and system_decision.")
        print("Run migration script: python scripts/migrate_add_threshold_columns.py")
        print()
    
    # Validate outcomes
    print("Validating outcomes...")
    evaluator = AttendanceEvaluation()
    df_validated = evaluator.validate_outcomes(df)
    
    if 'outcome' not in df_validated.columns:
        print("[ERROR] Could not validate outcomes. Check data structure.")
        return
    
    # Get outcome counts
    outcome_counts = evaluator.get_outcome_counts(df_validated)
    
    print("=" * 60)
    print("OUTCOME SUMMARY")
    print("=" * 60)
    print(f"True Accepts:  {outcome_counts['true_accept']:4d}  (Genuine + System Accept)")
    print(f"False Rejects: {outcome_counts['false_reject']:4d}  (Genuine + System Reject)")
    print(f"False Accepts: {outcome_counts['false_accept']:4d}  (Impostor + System Accept)")
    print(f"True Rejects:  {outcome_counts['true_reject']:4d}  (Impostor + System Reject)")
    print(f"Unknown:       {outcome_counts['unknown']:4d}  (Could not determine)")
    print()
    
    total_validated = sum([
        outcome_counts['true_accept'],
        outcome_counts['false_reject'],
        outcome_counts['false_accept'],
        outcome_counts['true_reject']
    ])
    
    print(f"Total Validated: {total_validated} / {len(df)}")
    print()
    
    # Show breakdown by outcome
    if total_validated > 0:
        print("=" * 60)
        print("OUTCOME BREAKDOWN")
        print("=" * 60)
        
        for outcome_type in ['true_accept', 'false_reject', 'false_accept', 'true_reject']:
            count = outcome_counts[outcome_type]
            if count > 0:
                outcome_df = df_validated[df_validated['outcome'] == outcome_type]
                print(f"\n{outcome_type.upper().replace('_', ' ')} ({count} records):")
                print("-" * 60)
                
                display_cols = ['user_id', 'recognition_score', 'threshold_used', 'system_decision', 'face_verified']
                available_cols = [col for col in display_cols if col in outcome_df.columns]
                
                if available_cols:
                    pd.set_option('display.max_rows', 10)
                    print(outcome_df[available_cols].head(10).to_string(index=False))
                    if len(outcome_df) > 10:
                        print(f"... and {len(outcome_df) - 10} more")
    
    print()
    print("=" * 60)
    print("VALIDATION COMPLETE")
    print("=" * 60)


if __name__ == "__main__":
    main()

