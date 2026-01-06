import pandas as pd
from datetime import datetime
from app.utils.logging import setup_logger


class DataCleaning:
    """
    Handles data cleaning operations for attendance data.
    Lightweight, justified cleaning for system-generated data.
    """

    def __init__(self):
        self.logger = setup_logger()

    def normalize_timestamps(self, df):
        """
        Normalize timestamps to datetime format.
        
        Args:
            df: DataFrame with timestamp column
            
        Returns:
            DataFrame with normalized timestamps
        """
        if df.empty or 'timestamp' not in df.columns:
            return df
        
        df = df.copy()
        try:
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            self.logger.info("Timestamps normalized successfully")
        except Exception as e:
            self.logger.warning(f"Error normalizing timestamps: {e}")
        
        return df

    def remove_duplicates(self, df, strategy='first', subset=None):
        """
        Remove duplicate attendance entries.
        
        Args:
            df: DataFrame with attendance records
            strategy: 'first' (keep first) or 'last' (keep last)
            subset: Columns to consider for duplicates (default: user_id + date)
            
        Returns:
            DataFrame with duplicates removed
        """
        if df.empty:
            return df
        
        df = df.copy()
        
        # Default: remove duplicates based on user_id and date
        if subset is None:
            if 'timestamp' in df.columns:
                df['date'] = pd.to_datetime(df['timestamp']).dt.date
                subset = ['user_id', 'date']
            else:
                subset = ['user_id']
        
        initial_count = len(df)
        
        if strategy == 'first':
            df = df.drop_duplicates(subset=subset, keep='first')
        elif strategy == 'last':
            df = df.drop_duplicates(subset=subset, keep='last')
        else:
            df = df.drop_duplicates(subset=subset)
        
        removed = initial_count - len(df)
        if removed > 0:
            self.logger.info(f"Removed {removed} duplicate attendance records")
        
        return df

    def handle_missing_values(self, df, columns=None, strategy='drop'):
        """
        Handle missing values in attendance data.
        
        Args:
            df: DataFrame with attendance records
            columns: Specific columns to check (None = all)
            strategy: 'drop' (remove rows) or 'flag' (add flag column)
            
        Returns:
            DataFrame with missing values handled
        """
        if df.empty:
            return df
        
        df = df.copy()
        
        # Critical columns that should not be missing
        critical_columns = ['user_id', 'timestamp']
        if columns is None:
            columns = critical_columns
        
        initial_count = len(df)
        
        if strategy == 'drop':
            # Drop rows with missing critical values
            df = df.dropna(subset=columns)
            removed = initial_count - len(df)
            if removed > 0:
                self.logger.info(f"Removed {removed} rows with missing values in {columns}")
        elif strategy == 'flag':
            # Add flag column for missing values
            df['has_missing_values'] = df[columns].isnull().any(axis=1)
            self.logger.info(f"Flagged {df['has_missing_values'].sum()} rows with missing values")
        
        return df

    def flag_outliers(self, df, score_column='recognition_score', lower_threshold=0.3, upper_threshold=1.0):
        """
        Flag outlier recognition scores.
        
        Args:
            df: DataFrame with attendance records
            score_column: Column name for recognition scores
            lower_threshold: Lower bound for normal scores
            upper_threshold: Upper bound for normal scores
            
        Returns:
            DataFrame with outlier flag column
        """
        if df.empty or score_column not in df.columns:
            return df
        
        df = df.copy()
        df['is_outlier'] = (
            (df[score_column] < lower_threshold) | 
            (df[score_column] > upper_threshold)
        )
        
        outlier_count = df['is_outlier'].sum()
        if outlier_count > 0:
            self.logger.info(f"Flagged {outlier_count} records with outlier scores")
        
        return df

    def filter_test_users(self, df, test_user_ids=None):
        """
        Filter out test/inactive users.
        
        Args:
            df: DataFrame with attendance records
            test_user_ids: List of test user IDs to exclude (default: common test patterns)
            
        Returns:
            DataFrame with test users removed
        """
        if df.empty:
            return df
        
        df = df.copy()
        
        if test_user_ids is None:
            # Default test user patterns
            test_user_ids = ['test', 'demo', 'admin', 'system']
        
        initial_count = len(df)
        
        # Filter out test users (case-insensitive)
        if 'user_id' in df.columns:
            mask = ~df['user_id'].str.lower().isin([uid.lower() for uid in test_user_ids])
            df = df[mask]
        
        removed = initial_count - len(df)
        if removed > 0:
            self.logger.info(f"Removed {removed} records from test users")
        
        return df

    def clean_attendance_data(self, df, 
                             normalize_timestamps=True,
                             remove_duplicates=True,
                             handle_missing=True,
                             flag_outliers=True,
                             filter_test_users=True):
        """
        Main data cleaning pipeline.
        
        Args:
            df: Raw attendance DataFrame
            normalize_timestamps: Whether to normalize timestamps
            remove_duplicates: Whether to remove duplicates
            handle_missing: Whether to handle missing values
            flag_outliers: Whether to flag outliers
            filter_test_users: Whether to filter test users
            
        Returns:
            Cleaned DataFrame
        """
        if df.empty:
            return df
        
        df = df.copy()
        initial_count = len(df)
        
        self.logger.info(f"Starting data cleaning pipeline (initial records: {initial_count})")
        
        if normalize_timestamps:
            df = self.normalize_timestamps(df)
        
        if handle_missing:
            df = self.handle_missing_values(df, strategy='drop')
        
        if filter_test_users:
            df = self.filter_test_users(df)
        
        if remove_duplicates:
            df = self.remove_duplicates(df, strategy='first')
        
        if flag_outliers and 'recognition_score' in df.columns:
            df = self.flag_outliers(df)
        
        final_count = len(df)
        removed = initial_count - final_count
        
        if removed > 0:
            self.logger.info(f"Data cleaning complete: {final_count} records remaining ({removed} removed)")
        else:
            self.logger.info(f"Data cleaning complete: {final_count} records (no changes)")
        
        return df

