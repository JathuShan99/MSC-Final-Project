#!/usr/bin/env python3
"""
Script to query and display impostor attempts from the database.

Usage:
    python scripts/get_impostor_data.py
    python scripts/get_impostor_data.py --export-csv
"""

import sys
from pathlib import Path
import pandas as pd

# Add parent directory to path
parent_dir = str(Path(__file__).parent.parent)
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

from app.database.db_manager import DatabaseManager
from app.database.models import Attendance
from app.analytics.evaluation import AttendanceEvaluation
from app.analytics.metrics import AttendanceMetrics


def main():
    print("=" * 60)
    print("IMPOSTOR DATA QUERY")
    print("=" * 60)
    print()
    
    # Load attendance data
    print("Loading attendance data...")
    metrics = AttendanceMetrics()
    df = metrics.load_attendance()
    
    if df.empty:
        print("No attendance data found in database.")
        return
    
    print(f"Total attendance records: {len(df)}")
    print()
    
    # Split into genuine and impostor
    evaluator = AttendanceEvaluation()
    genuine, impostor = evaluator.get_genuine_impostor_split(df)
    
    print("=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"Genuine Attempts: {len(genuine)}")
    print(f"Impostor Attempts: {len(impostor)}")
    print()
    
    if len(impostor) == 0:
        print("⚠️  No impostor attempts found!")
        print()
        print("To create impostor attempts:")
        print("1. Enroll at least 2 users (e.g., 0002 and 0003)")
        print("2. Run recognition (main.py → Option 2)")
        print("3. Scan QR code for one user (e.g., 0002)")
        print("4. Show face of a different user (e.g., 0003)")
        print("5. System will record this as an impostor attempt")
        return
    
    # Display impostor records
    print("=" * 60)
    print("IMPOSTOR ATTEMPTS DETAILS")
    print("=" * 60)
    print()
    
    # Show summary statistics
    if 'recognition_score' in impostor.columns:
        scores = impostor['recognition_score'].dropna()
        if len(scores) > 0:
            print("Recognition Score Statistics:")
            print(f"  Mean: {scores.mean():.3f}")
            print(f"  Median: {scores.median():.3f}")
            print(f"  Min: {scores.min():.3f}")
            print(f"  Max: {scores.max():.3f}")
            print()
    
    # Show detailed records
    print("Detailed Records:")
    print("-" * 60)
    
    display_cols = ['user_id', 'name', 'recognition_score', 'face_verified', 'liveness_verified', 'timestamp']
    available_cols = [col for col in display_cols if col in impostor.columns]
    
    pd.set_option('display.max_rows', None)
    pd.set_option('display.width', None)
    pd.set_option('display.max_columns', None)
    
    print(impostor[available_cols].to_string(index=False))
    print()
    
    # Export option
    if '--export-csv' in sys.argv:
        from app.config.paths import EXPORTS_DIR
        from datetime import datetime
        
        output_file = EXPORTS_DIR / f"impostor_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        output_file.parent.mkdir(parents=True, exist_ok=True)
        impostor.to_csv(output_file, index=False)
        print(f"✅ Exported to: {output_file}")
    
    print()
    print("=" * 60)
    print("How Impostor Attempts Are Created:")
    print("=" * 60)
    print("Impostor attempts are automatically recorded when:")
    print("  - QR code is scanned for one user (e.g., 0002)")
    print("  - But face recognition identifies a different user (e.g., 0003)")
    print("  - System records: face_verified=0, liveness_verified=0")
    print()
    print("These are used in evaluation to compute:")
    print("  - FAR (False Acceptance Rate)")
    print("  - Accuracy metrics")
    print("  - Security performance analysis")


if __name__ == "__main__":
    main()

