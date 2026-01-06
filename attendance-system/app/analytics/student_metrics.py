import pandas as pd
from datetime import datetime, timedelta
from app.database.db_manager import DatabaseManager
from app.utils.logging import setup_logger


class StudentMetrics:
    """
    Computes student-specific attendance analytics.
    Focused on individual student profile metrics.
    """

    def __init__(self):
        self.db = DatabaseManager()
        self.logger = setup_logger()

    def get_student_attendance_history(self, user_id: str, start_date=None, end_date=None):
        """
        Get student's attendance history timeline.
        
        Args:
            user_id: Student user ID
            start_date: Optional start date filter
            end_date: Optional end date filter
            
        Returns:
            DataFrame with attendance records sorted by date
        """
        query = """
            SELECT 
                a.id,
                a.user_id,
                a.recognition_score,
                a.face_verified,
                a.liveness_verified,
                a.timestamp
            FROM attendance a
            WHERE a.user_id = ?
        """
        params = [user_id]
        
        if start_date:
            query += " AND DATE(a.timestamp) >= DATE(?)"
            params.append(start_date if isinstance(start_date, str) else start_date.strftime('%Y-%m-%d'))
        
        if end_date:
            query += " AND DATE(a.timestamp) <= DATE(?)"
            params.append(end_date if isinstance(end_date, str) else end_date.strftime('%Y-%m-%d'))
        
        query += " ORDER BY a.timestamp DESC"
        
        try:
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(query, tuple(params))
                rows = cursor.fetchall()
                
                if not rows:
                    return pd.DataFrame()
                
                data = []
                for row in rows:
                    if hasattr(row, 'keys'):
                        data.append(dict(row))
                    else:
                        data.append({
                            'id': row[0] if len(row) > 0 else None,
                            'user_id': row[1] if len(row) > 1 else None,
                            'recognition_score': row[2] if len(row) > 2 else None,
                            'face_verified': row[3] if len(row) > 3 else None,
                            'liveness_verified': row[4] if len(row) > 4 else None,
                            'timestamp': row[5] if len(row) > 5 else None,
                        })
                
                df = pd.DataFrame(data)
                
                if 'timestamp' in df.columns:
                    df['timestamp'] = pd.to_datetime(df['timestamp'])
                    df['date'] = df['timestamp'].dt.date
                
                return df
        except Exception as e:
            self.logger.error(f"Error loading student attendance: {e}")
            return pd.DataFrame()

    def get_student_statistics(self, user_id: str, start_date=None, end_date=None):
        """
        Calculate comprehensive statistics for a student.
        
        Args:
            user_id: Student user ID
            start_date: Optional start date filter
            end_date: Optional end date filter
            
        Returns:
            Dictionary with student statistics
        """
        df = self.get_student_attendance_history(user_id, start_date, end_date)
        
        if df.empty:
            return {
                "total_attendance": 0,
                "attendance_rate": 0.0,
                "average_score": 0.0,
                "face_verification_rate": 0.0,
                "liveness_verification_rate": 0.0,
                "multi_factor_rate": 0.0,
                "first_attendance": None,
                "last_attendance": None,
                "days_active": 0
            }
        
        total = len(df)
        
        # Calculate attendance rate (assuming daily attendance expected)
        if start_date and end_date:
            expected_days = (end_date - start_date).days + 1
        else:
            # Use date range from data
            if 'date' in df.columns:
                date_range = (df['date'].max() - df['date'].min()).days + 1
                expected_days = max(date_range, total)  # At least as many days as records
            else:
                expected_days = total
        
        attendance_rate = (total / expected_days * 100) if expected_days > 0 else 0.0
        
        # Average recognition score
        scores = df['recognition_score'].dropna()
        avg_score = scores.mean() if not scores.empty else 0.0
        
        # Verification rates
        face_verified = int(df['face_verified'].sum()) if 'face_verified' in df.columns else 0
        liveness_verified = int(df['liveness_verified'].sum()) if 'liveness_verified' in df.columns else 0
        multi_factor = int(((df['face_verified'] == 1) & (df['liveness_verified'] == 1)).sum()) if 'face_verified' in df.columns and 'liveness_verified' in df.columns else 0
        
        # Date range
        first_attendance = df['timestamp'].min() if 'timestamp' in df.columns and not df['timestamp'].empty else None
        last_attendance = df['timestamp'].max() if 'timestamp' in df.columns and not df['timestamp'].empty else None
        
        # Unique days with attendance
        days_active = df['date'].nunique() if 'date' in df.columns else 0
        
        return {
            "total_attendance": total,
            "attendance_rate": round(attendance_rate, 2),
            "average_score": round(avg_score, 3),
            "face_verification_rate": round((face_verified / total * 100) if total > 0 else 0, 2),
            "liveness_verification_rate": round((liveness_verified / total * 100) if total > 0 else 0, 2),
            "multi_factor_rate": round((multi_factor / total * 100) if total > 0 else 0, 2),
            "first_attendance": first_attendance,
            "last_attendance": last_attendance,
            "days_active": days_active
        }

    def get_student_score_trends(self, user_id: str, start_date=None, end_date=None):
        """
        Get recognition score trends over time for a student.
        
        Args:
            user_id: Student user ID
            start_date: Optional start date filter
            end_date: Optional end date filter
            
        Returns:
            DataFrame with date and average score per day
        """
        df = self.get_student_attendance_history(user_id, start_date, end_date)
        
        if df.empty or 'recognition_score' not in df.columns:
            return pd.DataFrame(columns=['date', 'avg_score', 'count'])
        
        if 'date' not in df.columns:
            df['date'] = pd.to_datetime(df['timestamp']).dt.date
        
        # Group by date and calculate average score
        daily_scores = df.groupby('date').agg({
            'recognition_score': ['mean', 'count']
        }).reset_index()
        
        daily_scores.columns = ['date', 'avg_score', 'count']
        daily_scores = daily_scores.sort_values('date')
        daily_scores['avg_score'] = daily_scores['avg_score'].round(3)
        
        return daily_scores

    def get_student_recent_records(self, user_id: str, limit=10):
        """
        Get student's most recent attendance records.
        
        Args:
            user_id: Student user ID
            limit: Number of recent records to return
            
        Returns:
            DataFrame with recent attendance records
        """
        df = self.get_student_attendance_history(user_id)
        
        if df.empty:
            return pd.DataFrame()
        
        # Return most recent records
        recent = df.head(limit).copy()
        
        # Format for display
        if 'timestamp' in recent.columns:
            recent['formatted_time'] = pd.to_datetime(recent['timestamp']).dt.strftime('%Y-%m-%d %H:%M:%S')
        
        return recent

    def get_student_daily_summary(self, user_id: str, start_date=None, end_date=None):
        """
        Get daily attendance summary for student.
        
        Args:
            user_id: Student user ID
            start_date: Optional start date filter
            end_date: Optional end date filter
            
        Returns:
            DataFrame with date and count columns
        """
        df = self.get_student_attendance_history(user_id, start_date, end_date)
        
        if df.empty:
            return pd.DataFrame(columns=['date', 'count'])
        
        if 'date' not in df.columns:
            df['date'] = pd.to_datetime(df['timestamp']).dt.date
        
        daily = df.groupby('date').size().reset_index(name='count')
        daily = daily.sort_values('date')
        
        return daily

