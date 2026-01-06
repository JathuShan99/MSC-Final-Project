#!/usr/bin/env python3
"""
Standalone script for running biometric evaluation.
Generates FAR/FRR metrics and evaluation plots.

Usage:
    python scripts/run_evaluation.py
    python scripts/run_evaluation.py --threshold 0.5
    python scripts/run_evaluation.py --start-date 2024-01-01 --end-date 2024-12-31
"""

import sys
import argparse
from pathlib import Path
from datetime import datetime

# Add parent directory to path
parent_dir = str(Path(__file__).parent.parent)
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

from app.analytics.metrics import AttendanceMetrics
from app.analytics.data_cleaning import DataCleaning
from app.analytics.evaluation import AttendanceEvaluation
from app.analytics.plots import EvaluationPlots
from app.config.paths import EXPORTS_DIR


def main():
    parser = argparse.ArgumentParser(description='Run biometric evaluation analysis')
    parser.add_argument('--threshold', type=float, default=0.5, 
                       help='Similarity score threshold (default: 0.5)')
    parser.add_argument('--start-date', type=str, default=None,
                       help='Start date filter (YYYY-MM-DD)')
    parser.add_argument('--end-date', type=str, default=None,
                       help='End date filter (YYYY-MM-DD)')
    parser.add_argument('--no-cleaning', action='store_true',
                       help='Skip data cleaning')
    parser.add_argument('--output-dir', type=str, default=None,
                       help='Output directory for plots (default: data/exports/evaluation)')
    
    args = parser.parse_args()
    
    # Validate threshold
    if not 0.0 <= args.threshold <= 1.0:
        print("Error: Threshold must be between 0.0 and 1.0")
        return 1
    
    # Set output directory
    if args.output_dir:
        output_dir = Path(args.output_dir)
    else:
        output_dir = EXPORTS_DIR / "evaluation"
    output_dir.mkdir(parents=True, exist_ok=True)
    
    print("=" * 60)
    print("BIOMETRIC EVALUATION ANALYSIS")
    print("=" * 60)
    print(f"Threshold: {args.threshold}")
    if args.start_date:
        print(f"Start Date: {args.start_date}")
    if args.end_date:
        print(f"End Date: {args.end_date}")
    print(f"Output Directory: {output_dir}")
    print("=" * 60)
    print()
    
    # Load data
    print("Loading attendance data...")
    metrics = AttendanceMetrics()
    
    start_date = None
    end_date = None
    if args.start_date:
        try:
            start_date = datetime.strptime(args.start_date, '%Y-%m-%d').date()
        except ValueError:
            print(f"Error: Invalid start date format: {args.start_date}. Use YYYY-MM-DD")
            return 1
    
    if args.end_date:
        try:
            end_date = datetime.strptime(args.end_date, '%Y-%m-%d').date()
        except ValueError:
            print(f"Error: Invalid end date format: {args.end_date}. Use YYYY-MM-DD")
            return 1
    
    df = metrics.load_attendance(start_date=start_date, end_date=end_date)
    
    if df.empty:
        print("Error: No attendance data found for the specified filters.")
        return 1
    
    print(f"Loaded {len(df)} attendance records")
    print()
    
    # Apply data cleaning
    if not args.no_cleaning:
        print("Applying data cleaning (keeping all attempts for evaluation)...")
        cleaning = DataCleaning()
        # Skip duplicate removal for evaluation - we need ALL attempts for accurate FAR/FRR
        df = cleaning.clean_attendance_data(
            df,
            normalize_timestamps=True,
            remove_duplicates=False,  # Keep all attempts - important for evaluation
            handle_missing=True,
            flag_outliers=True,
            filter_test_users=True
        )
        print(f"After cleaning: {len(df)} records (all attempts kept)")
        print()
    
    # Compute evaluation metrics
    print("Computing evaluation metrics...")
    evaluator = AttendanceEvaluation()
    
    # Metrics at specified threshold
    # Use stored system_decision for accurate evaluation (recommended)
    metrics_result = evaluator.compute_metrics(df, args.threshold, use_stored_decision=True)
    
    print("\n" + "=" * 60)
    print("EVALUATION METRICS")
    print("=" * 60)
    print(f"Threshold: {metrics_result['threshold']}")
    print(f"Total Attempts: {metrics_result['total_attempts']}")
    print(f"  - Genuine Attempts: {metrics_result['genuine_attempts']}")
    print(f"  - Impostor Attempts: {metrics_result['impostor_attempts']}")
    print()
    print(f"False Acceptance Rate (FAR): {metrics_result['FAR']:.4f} ({metrics_result['FAR']*100:.2f}%)")
    print(f"False Rejection Rate (FRR): {metrics_result['FRR']:.4f} ({metrics_result['FRR']*100:.2f}%)")
    print(f"Accuracy: {metrics_result['accuracy']:.4f} ({metrics_result['accuracy']*100:.2f}%)")
    print()
    print("Detailed Counts:")
    print(f"  - True Accepts: {metrics_result['true_accepts']}")
    print(f"  - True Rejects: {metrics_result['true_rejects']}")
    print(f"  - False Accepts: {metrics_result['false_accepts']}")
    print(f"  - False Rejects: {metrics_result['false_rejects']}")
    print("=" * 60)
    print()
    
    # Find EER
    print("Computing Equal Error Rate (EER)...")
    eer_result = evaluator.find_eer_threshold(df)
    print(f"EER Threshold: {eer_result['eer_threshold']}")
    print(f"EER Value: {eer_result['eer_value']:.4f} ({eer_result['eer_value']*100:.2f}%)")
    print(f"FAR at EER: {eer_result['FAR_at_eer']:.4f}")
    print(f"FRR at EER: {eer_result['FRR_at_eer']:.4f}")
    print()
    
    # Score statistics
    print("Score Statistics:")
    stats = evaluator.get_score_statistics(df)
    if stats['genuine']:
        print("\nGenuine Attempts:")
        for key, value in stats['genuine'].items():
            print(f"  {key}: {value}")
    if stats['impostor']:
        print("\nImpostor Attempts:")
        for key, value in stats['impostor'].items():
            print(f"  {key}: {value}")
    print()
    
    # Generate plots
    print("Generating evaluation plots...")
    plots = EvaluationPlots()
    
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    
    # Score distribution
    print("  - Score distribution histogram...")
    fig = plots.score_distribution_histogram(df, backend='matplotlib')
    if fig:
        plots.save_matplotlib_figure(fig, output_dir / f"score_distribution_{timestamp}.png")
        plt.close(fig)
    
    # Genuine vs Impostor
    print("  - Genuine vs Impostor distribution...")
    fig = plots.genuine_vs_impostor_distribution(df, backend='matplotlib')
    if fig:
        plots.save_matplotlib_figure(fig, output_dir / f"genuine_impostor_{timestamp}.png")
        plt.close(fig)
    
    # FAR/FRR curve
    print("  - FAR/FRR curve...")
    fig = plots.far_frr_curve(df, backend='matplotlib')
    if fig:
        plots.save_matplotlib_figure(fig, output_dir / f"far_frr_curve_{timestamp}.png")
        plt.close(fig)
    
    # Accuracy curve
    print("  - Accuracy curve...")
    fig = plots.accuracy_curve(df, backend='matplotlib')
    if fig:
        plots.save_matplotlib_figure(fig, output_dir / f"accuracy_curve_{timestamp}.png")
        plt.close(fig)
    
    print()
    print("=" * 60)
    print("EVALUATION COMPLETE")
    print("=" * 60)
    print(f"Plots saved to: {output_dir}")
    print()
    
    return 0


if __name__ == "__main__":
    import matplotlib
    matplotlib.use('Agg')  # Non-interactive backend for CLI
    import matplotlib.pyplot as plt
    sys.exit(main())

