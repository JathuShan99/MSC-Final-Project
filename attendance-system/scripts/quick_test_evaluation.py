#!/usr/bin/env python3
"""
Quick test of evaluation metrics with test data.
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
    print("QUICK EVALUATION TEST")
    print("=" * 60)
    print()
    
    # Load data
    metrics = AttendanceMetrics()
    df = metrics.load_attendance()
    
    if df.empty:
        print("[ERROR] No data found. Run:")
        print("  python scripts/create_test_evaluation_data.py")
        return
    
    print(f"Loaded {len(df)} records")
    print()
    
    # Compute metrics using stored decisions
    evaluator = AttendanceEvaluation()
    result = evaluator.compute_metrics(df, threshold=0.5, use_stored_decision=True)
    
    print("=" * 60)
    print("EVALUATION METRICS")
    print("=" * 60)
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
    print(f"  - True Accepts:  {result['true_accepts']}  (Genuine + Accept)")
    print(f"  - False Rejects: {result['false_rejects']}  (Genuine + Reject)")
    print(f"  - False Accepts: {result['false_accepts']}  (Impostor + Accept)")
    print(f"  - True Rejects:  {result['true_rejects']}  (Impostor + Reject)")
    print("=" * 60)

if __name__ == "__main__":
    main()

