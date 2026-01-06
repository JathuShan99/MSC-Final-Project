#!/usr/bin/env python3
"""
Verify evaluation outcomes - show breakdown of all 4 outcome types.
"""

import sys
from pathlib import Path

parent_dir = str(Path(__file__).parent.parent)
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

from app.analytics.metrics import AttendanceMetrics
from app.analytics.evaluation import AttendanceEvaluation

def main():
    print("=" * 60)
    print("EVALUATION OUTCOMES VERIFICATION")
    print("=" * 60)
    print()
    
    # Load data
    metrics = AttendanceMetrics()
    df = metrics.load_attendance()
    
    print(f"Total records: {len(df)}")
    print()
    
    if df.empty:
        print("[WARNING] No attendance records found in database.")
        print("Run 'python scripts/create_test_evaluation_data.py' first to create test data.")
        return
    
    # Validate outcomes
    evaluator = AttendanceEvaluation()
    df_validated = evaluator.validate_outcomes(df)
    
    # Get outcome counts
    counts = evaluator.get_outcome_counts(df_validated)
    
    print("=" * 60)
    print("OUTCOME BREAKDOWN")
    print("=" * 60)
    print(f"True Accepts:  {counts['true_accept']:3d}  (Genuine + System Accept)")
    print(f"False Rejects: {counts['false_reject']:3d}  (Genuine + System Reject)")
    print(f"False Accepts: {counts['false_accept']:3d}  (Impostor + System Accept)")
    print(f"True Rejects:  {counts['true_reject']:3d}  (Impostor + System Reject)")
    print(f"Unknown:       {counts['unknown']:3d}  (Could not determine)")
    print()
    
    # Show details for each outcome type
    print("=" * 60)
    print("DETAILED BREAKDOWN")
    print("=" * 60)
    
    for outcome_type in ['true_accept', 'false_reject', 'false_accept', 'true_reject']:
        if 'outcome' not in df_validated.columns:
            print("[WARNING] Outcome column not found. Cannot show detailed breakdown.")
            break
        outcome_df = df_validated[df_validated['outcome'] == outcome_type]
        if len(outcome_df) > 0:
            print()
            print(f"{outcome_type.upper().replace('_', ' ')} ({len(outcome_df)} records):")
            print("-" * 60)
            for idx, row in outcome_df.head(10).iterrows():
                print(f"  User: {row['user_id']:6} | "
                      f"Score: {row['recognition_score']:.3f} | "
                      f"Face: {row['face_verified']} | "
                      f"Decision: {row.get('system_decision', 'N/A'):6} | "
                      f"Threshold: {row.get('threshold_used', 'N/A')}")
            if len(outcome_df) > 10:
                print(f"  ... and {len(outcome_df) - 10} more records")
    
    # Compute metrics
    print()
    print("=" * 60)
    print("EVALUATION METRICS (Using Stored Decisions)")
    print("=" * 60)
    result = evaluator.compute_metrics(df, threshold=0.5, use_stored_decision=True)
    print(f"Threshold: {result['threshold']}")
    print(f"Total Attempts: {result['total_attempts']}")
    print(f"  - Genuine Attempts: {result['genuine_attempts']}")
    print(f"  - Impostor Attempts: {result['impostor_attempts']}")
    print()
    print(f"False Acceptance Rate (FAR): {result['FAR']:.4f} ({result['FAR']*100:.2f}%)")
    print(f"False Rejection Rate (FRR):  {result['FRR']:.4f} ({result['FRR']*100:.2f}%)")
    print(f"Accuracy: {result['accuracy']:.4f} ({result['accuracy']*100:.2f}%)")
    print()
    print("Detailed Counts:")
    print(f"  - True Accepts:  {result['true_accepts']}")
    print(f"  - True Rejects:  {result['true_rejects']}")
    print(f"  - False Accepts: {result['false_accepts']}")
    print(f"  - False Rejects: {result['false_rejects']}")
    print("=" * 60)

if __name__ == "__main__":
    main()

