import pandas as pd
from datetime import datetime, timedelta
from app.database.db_manager import DatabaseManager
from app.utils.logging import setup_logger


class AttendanceMetrics:
    """
    Computes attendance analytics from the database.
    Enterprise-grade metrics for MSc-level analysis.
    """

    def __init__(self):
        self.db = DatabaseManager()
        self.logger = setup_logger()

    def load_attendance(self, start_date=None, end_date=None, user_id=None):
        """
        Load attendance records from database with optional filters.
        
        Args:
            start_date: Optional start date filter (datetime or date)
            end_date: Optional end date filter (datetime or date)
            user_id: Optional user ID filter
            
        Returns:
            DataFrame with attendance records
        """
        query = """
            SELECT 
                a.id,
                a.user_id,
                u.name,
                u.role,
                a.recognition_score,
                a.face_verified,
                a.liveness_verified,
                a.threshold_used,
                a.system_decision,
                a.timestamp
            FROM attendance a
            LEFT JOIN users u ON a.user_id = u.user_id
            WHERE 1=1
        """
        params = []
        
        if start_date:
            query += " AND DATE(a.timestamp) >= DATE(?)"
            params.append(start_date if isinstance(start_date, str) else start_date.strftime('%Y-%m-%d'))
        
        if end_date:
            query += " AND DATE(a.timestamp) <= DATE(?)"
            params.append(end_date if isinstance(end_date, str) else end_date.strftime('%Y-%m-%d'))
        
        if user_id:
            query += " AND a.user_id = ?"
            params.append(user_id)
        
        query += " ORDER BY a.timestamp DESC"
        
        try:
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                # Execute query with params (empty tuple if no params)
                if params:
                    cursor.execute(query, tuple(params))
                else:
                    cursor.execute(query)
                
                rows = cursor.fetchall()
                
                if not rows:
                    self.logger.info("No attendance records found in database")
                    return pd.DataFrame()
                
                # Convert sqlite3.Row objects to dicts
                # sqlite3.Row objects support dict() conversion
                data = []
                for row in rows:
                    try:
                        if hasattr(row, 'keys'):
                            # sqlite3.Row object - convert to dict
                            data.append(dict(row))
                        else:
                            # Fallback for tuple rows
                            columns = [desc[0] for desc in cursor.description]
                            data.append(dict(zip(columns, row)))
                    except Exception as row_error:
                        self.logger.error(f"Error converting row to dict: {row_error}")
                        self.logger.error(f"Row type: {type(row)}, Row value: {row}")
                        continue
                
                if not data:
                    self.logger.warning("No rows could be converted to dicts")
                    return pd.DataFrame()
                
                df = pd.DataFrame(data)
                
                # Convert timestamp to datetime
                # Handle mixed formats (with/without microseconds)
                if 'timestamp' in df.columns:
                    df['timestamp'] = pd.to_datetime(df['timestamp'], format='mixed', errors='coerce')
                
                self.logger.info(f"Loaded {len(df)} attendance records")
                return df
        except Exception as e:
            self.logger.error(f"Error loading attendance: {e}")
            import traceback
            self.logger.error(traceback.format_exc())
            return pd.DataFrame()

    def daily_summary(self, start_date=None, end_date=None):
        """
        Get daily attendance summary.
        
        Args:
            start_date: Optional start date filter
            end_date: Optional end date filter
            
        Returns:
            DataFrame with date and count columns
        """
        df = self.load_attendance(start_date=start_date, end_date=end_date)
        
        if df.empty:
            return pd.DataFrame(columns=['date', 'count'])
        
        df['date'] = pd.to_datetime(df['timestamp']).dt.date
        daily = df.groupby('date').size().reset_index(name='count')
        daily = daily.sort_values('date')
        
        return daily

    def weekly_summary(self, start_date=None, end_date=None):
        """
        Get weekly attendance summary.
        
        Args:
            start_date: Optional start date filter
            end_date: Optional end date filter
            
        Returns:
            DataFrame with week and count columns
        """
        df = self.load_attendance(start_date=start_date, end_date=end_date)
        
        if df.empty:
            return pd.DataFrame(columns=['week', 'count'])
        
        df['date'] = pd.to_datetime(df['timestamp']).dt.date
        df['week'] = pd.to_datetime(df['timestamp']).dt.to_period('W').astype(str)
        weekly = df.groupby('week').size().reset_index(name='count')
        weekly = weekly.sort_values('week')
        
        return weekly

    def user_summary(self, start_date=None, end_date=None):
        """
        Get attendance summary per user.
        
        Args:
            start_date: Optional start date filter
            end_date: Optional end date filter
            
        Returns:
            DataFrame with user_id, name, role, and attendance_count
        """
        df = self.load_attendance(start_date=start_date, end_date=end_date)
        
        if df.empty:
            return pd.DataFrame(columns=['user_id', 'name', 'role', 'attendance_count'])
        
        user_summary = df.groupby(['user_id', 'name', 'role']).size().reset_index(name='attendance_count')
        user_summary = user_summary.sort_values('attendance_count', ascending=False)
        
        return user_summary

    def verification_stats(self, start_date=None, end_date=None):
        """
        Get verification statistics.
        
        Args:
            start_date: Optional start date filter
            end_date: Optional end date filter
            
        Returns:
            Dictionary with verification statistics
        """
        df = self.load_attendance(start_date=start_date, end_date=end_date)
        
        if df.empty:
            return {
                "total_records": 0,
                "face_verified": 0,
                "liveness_verified": 0,
                "face_verification_rate": 0.0,
                "liveness_verification_rate": 0.0,
                "multi_factor_verified": 0,
                "multi_factor_rate": 0.0
            }
        
        total = len(df)
        face_verified = int(df['face_verified'].sum()) if 'face_verified' in df.columns else 0
        liveness_verified = int(df['liveness_verified'].sum()) if 'liveness_verified' in df.columns else 0
        multi_factor = int(((df['face_verified'] == 1) & (df['liveness_verified'] == 1)).sum()) if 'face_verified' in df.columns and 'liveness_verified' in df.columns else 0
        
        return {
            "total_records": total,
            "face_verified": face_verified,
            "liveness_verified": liveness_verified,
            "face_verification_rate": round((face_verified / total * 100) if total > 0 else 0, 2),
            "liveness_verification_rate": round((liveness_verified / total * 100) if total > 0 else 0, 2),
            "multi_factor_verified": multi_factor,
            "multi_factor_rate": round((multi_factor / total * 100) if total > 0 else 0, 2)
        }

    def hourly_distribution(self, start_date=None, end_date=None):
        """
        Get attendance distribution by hour of day.
        
        Args:
            start_date: Optional start date filter
            end_date: Optional end date filter
            
        Returns:
            DataFrame with hour and count columns
        """
        df = self.load_attendance(start_date=start_date, end_date=end_date)
        
        if df.empty:
            return pd.DataFrame(columns=['hour', 'count'])
        
        df['hour'] = pd.to_datetime(df['timestamp']).dt.hour
        hourly = df.groupby('hour').size().reset_index(name='count')
        hourly = hourly.sort_values('hour')
        
        return hourly

    def recognition_score_stats(self, start_date=None, end_date=None):
        """
        Get recognition score statistics.
        
        Args:
            start_date: Optional start date filter
            end_date: Optional end date filter
            
        Returns:
            Dictionary with score statistics
        """
        df = self.load_attendance(start_date=start_date, end_date=end_date)
        
        if df.empty or 'recognition_score' not in df.columns:
            return {
                "mean": 0.0,
                "median": 0.0,
                "min": 0.0,
                "max": 0.0,
                "std": 0.0
            }
        
        scores = df['recognition_score'].dropna()
        
        if scores.empty:
            return {
                "mean": 0.0,
                "median": 0.0,
                "min": 0.0,
                "max": 0.0,
                "std": 0.0
            }
        
        return {
            "mean": round(scores.mean(), 3),
            "median": round(scores.median(), 3),
            "min": round(scores.min(), 3),
            "max": round(scores.max(), 3),
            "std": round(scores.std(), 3)
        }

