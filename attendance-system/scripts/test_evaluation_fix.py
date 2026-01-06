#!/usr/bin/env python3
"""
Test the evaluation fix - verify that face mismatches are correctly counted as True Rejects.
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
    print("TESTING EVALUATION FIX")
    print("=" * 60)
    print()
    
    # Load data
    metrics = AttendanceMetrics()
    df = metrics.load_attendance()
    
    print(f"Loaded {len(df)} records")
    print()
    
    # Check face mismatch records
    impostor_records = df[df['face_verified'] == 0]
    print(f"Impostor attempts (face_verified=0): {len(impostor_records)}")
    if len(impostor_records) > 0:
        print("\nImpostor records details:")
        for idx, row in impostor_records.iterrows():
            print(f"  User: {row['user_id']}, Score: {row['recognition_score']:.3f}, "
                  f"Decision: {row.get('system_decision', 'N/A')}, "
                  f"Threshold: {row.get('threshold_used', 'N/A')}")
    print()
    
    # Test with stored decisions (NEW - correct way)
    evaluator = AttendanceEvaluation()
    print("=" * 60)
    print("USING STORED SYSTEM_DECISION (CORRECT)")
    print("=" * 60)
    result_stored = evaluator.compute_metrics(df, threshold=0.5, use_stored_decision=True)
    print(f"Threshold: {result_stored['threshold']}")
    print(f"Impostor Attempts: {result_stored['impostor_attempts']}")
    print(f"False Accepts: {result_stored['false_accepts']}")
    print(f"True Rejects: {result_stored['true_rejects']}")
    print(f"FAR: {result_stored['FAR']:.4f} ({result_stored['FAR']*100:.2f}%)")
    print()
    
    # Test with score-based (OLD - for comparison)
    print("=" * 60)
    print("USING SCORE-BASED (OLD METHOD - FOR COMPARISON)")
    print("=" * 60)
    result_score = evaluator.compute_metrics(df, threshold=0.5, use_stored_decision=False)
    print(f"Threshold: {result_score['threshold']}")
    print(f"Impostor Attempts: {result_score['impostor_attempts']}")
    print(f"False Accepts: {result_score['false_accepts']}")
    print(f"True Rejects: {result_score['true_rejects']}")
    print(f"FAR: {result_score['FAR']:.4f} ({result_score['FAR']*100:.2f}%)")
    print()
    
    # Summary
    print("=" * 60)
    print("SUMMARY")
    print("=" * 60)
    if result_stored['true_rejects'] == result_stored['impostor_attempts']:
        print("[OK] All impostor attempts correctly counted as True Rejects")
    else:
        print(f"[WARNING] Expected {result_stored['impostor_attempts']} True Rejects, got {result_stored['true_rejects']}")
    
    if result_stored['false_accepts'] == 0:
        print("[OK] No False Accepts (correct)")
    else:
        print(f"[WARNING] Found {result_stored['false_accepts']} False Accepts (should be 0 for face mismatches)")
    
    print("=" * 60)

if __name__ == "__main__":
    main()

