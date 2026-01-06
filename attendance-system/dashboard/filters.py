import streamlit as st
import sys
import os
from pathlib import Path
from datetime import datetime, timedelta

# Get the attendance-system directory (parent of dashboard)
attendance_system_dir = str(Path(__file__).parent.parent)
if attendance_system_dir not in sys.path:
    sys.path.insert(0, attendance_system_dir)

# Change working directory to attendance-system for proper module resolution
os.chdir(attendance_system_dir)

# Lazy import to avoid circular dependency
def _get_models():
    """Lazy import to avoid circular dependency."""
    from app.database.models import User
    from app.database.db_manager import DatabaseManager
    return User, DatabaseManager


class DashboardFilters:
    """
    Handles date and user filters for the dashboard.
    """

    def __init__(self):
        # Lazy imports to avoid circular dependency
        User, DatabaseManager = _get_models()
        self.db_manager = DatabaseManager()
        self.user_model = User(self.db_manager)

    def render_date_filters(self):
        """
        Render date range filter widgets.
        
        Returns:
            Tuple of (start_date, end_date) or (None, None)
        """
        st.sidebar.header("📅 Date Range Filter")
        
        # Date range options
        date_range_option = st.sidebar.radio(
            "Select date range:",
            ["All Time", "Last 7 Days", "Last 30 Days", "Last 90 Days", "Custom Range"],
            key="date_range_option"
        )
        
        start_date = None
        end_date = None
        
        if date_range_option == "Last 7 Days":
            end_date = datetime.now().date()
            start_date = end_date - timedelta(days=7)
        elif date_range_option == "Last 30 Days":
            end_date = datetime.now().date()
            start_date = end_date - timedelta(days=30)
        elif date_range_option == "Last 90 Days":
            end_date = datetime.now().date()
            start_date = end_date - timedelta(days=90)
        elif date_range_option == "Custom Range":
            col1, col2 = st.sidebar.columns(2)
            with col1:
                start_date = st.date_input("Start Date", value=datetime.now().date() - timedelta(days=30))
            with col2:
                end_date = st.date_input("End Date", value=datetime.now().date())
            
            if start_date > end_date:
                st.sidebar.error("Start date must be before end date")
                return None, None
        
        return start_date, end_date

    def render_user_filter(self):
        """
        Render user filter widget.
        
        Returns:
            Selected user_id or None for all users
        """
        st.sidebar.header("👤 User Filter")
        
        # Get all users
        try:
            users = self.user_model.get_all()
            user_options = ["All Users"] + [f"{u['user_id']} - {u.get('name', 'N/A')}" for u in users]
            
            selected = st.sidebar.selectbox("Select user:", user_options)
            
            if selected == "All Users":
                return None
            
            # Extract user_id from selection
            user_id = selected.split(" - ")[0]
            return user_id
        except Exception as e:
            st.sidebar.error(f"Error loading users: {e}")
            return None

    def render_filters(self):
        """
        Render all filters and return filter values.
        
        Returns:
            Dictionary with start_date, end_date, and user_id
        """
        start_date, end_date = self.render_date_filters()
        user_id = self.render_user_filter()
        
        return {
            "start_date": start_date,
            "end_date": end_date,
            "user_id": user_id
        }

