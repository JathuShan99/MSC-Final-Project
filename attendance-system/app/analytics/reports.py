import pandas as pd
from pathlib import Path
from app.analytics.metrics import AttendanceMetrics
from app.config.paths import BASE_DIR
from app.utils.logging import setup_logger


class ReportService:
    """
    Handles data exports and report generation.
    GDPR-compliant: exports only metadata, no biometrics.
    """

    def __init__(self):
        self.metrics = AttendanceMetrics()
        self.logger = setup_logger()
        # Create exports directory
        self.exports_dir = BASE_DIR / "data" / "exports"
        self.exports_dir.mkdir(parents=True, exist_ok=True)

    def export_csv(self, start_date=None, end_date=None, user_id=None, filename=None):
        """
        Export attendance data to CSV.
        
        Args:
            start_date: Optional start date filter
            end_date: Optional end date filter
            user_id: Optional user ID filter
            filename: Optional custom filename (default: attendance_report_YYYYMMDD.csv)
            
        Returns:
            Path to exported CSV file
        """
        df = self.metrics.load_attendance(
            start_date=start_date,
            end_date=end_date,
            user_id=user_id
        )
        
        if df.empty:
            self.logger.warning("No attendance data to export")
            return None
        
        # Generate filename if not provided
        if filename is None:
            from datetime import datetime
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"attendance_report_{timestamp}.csv"
        
        # Ensure .csv extension
        if not filename.endswith('.csv'):
            filename += '.csv'
        
        filepath = self.exports_dir / filename
        
        try:
            df.to_csv(filepath, index=False)
            self.logger.info(f"Attendance report exported to: {filepath}")
            return filepath
        except Exception as e:
            self.logger.error(f"Error exporting CSV: {e}")
            raise

    def export_summary_report(self, start_date=None, end_date=None, filename=None):
        """
        Export summary report with aggregated statistics.
        
        Args:
            start_date: Optional start date filter
            end_date: Optional end date filter
            filename: Optional custom filename
            
        Returns:
            Path to exported CSV file
        """
        # Get summaries
        daily = self.metrics.daily_summary(start_date=start_date, end_date=end_date)
        user = self.metrics.user_summary(start_date=start_date, end_date=end_date)
        stats = self.metrics.verification_stats(start_date=start_date, end_date=end_date)
        
        # Create summary DataFrame
        summary_data = {
            'Metric': [
                'Total Records',
                'Face Verified',
                'Liveness Verified',
                'Multi-Factor Verified',
                'Face Verification Rate (%)',
                'Liveness Verification Rate (%)',
                'Multi-Factor Rate (%)'
            ],
            'Value': [
                stats['total_records'],
                stats['face_verified'],
                stats['liveness_verified'],
                stats['multi_factor_verified'],
                stats['face_verification_rate'],
                stats['liveness_verification_rate'],
                stats['multi_factor_rate']
            ]
        }
        
        summary_df = pd.DataFrame(summary_data)
        
        # Generate filename if not provided
        if filename is None:
            from datetime import datetime
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"attendance_summary_{timestamp}.csv"
        
        if not filename.endswith('.csv'):
            filename += '.csv'
        
        filepath = self.exports_dir / filename
        
        try:
            summary_df.to_csv(filepath, index=False)
            self.logger.info(f"Summary report exported to: {filepath}")
            return filepath
        except Exception as e:
            self.logger.error(f"Error exporting summary report: {e}")
            raise

