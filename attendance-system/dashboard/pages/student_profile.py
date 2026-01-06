import streamlit as st
import pandas as pd
import sys
import os
from pathlib import Path
from datetime import datetime, timedelta

# Get the attendance-system directory
attendance_system_dir = str(Path(__file__).parent.parent.parent)
if attendance_system_dir not in sys.path:
    sys.path.insert(0, attendance_system_dir)

# Change working directory to attendance-system for proper module resolution
os.chdir(attendance_system_dir)

from app.analytics.student_metrics import StudentMetrics
from dashboard.student_charts import StudentCharts
from dashboard.auth import DashboardAuth

# Page configuration
st.set_page_config(
    page_title="My Attendance Profile",
    page_icon="👤",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialize services
@st.cache_resource
def get_services():
    """Cache service instances for performance."""
    return {
        'metrics': StudentMetrics(),
        'charts': StudentCharts(),
        'auth': DashboardAuth()
    }

services = get_services()
metrics = services['metrics']
charts = services['charts']
auth = services['auth']

# Check authentication
user = auth.get_user_session()
if not user:
    st.error("⚠️ Please log in to view your profile.")
    st.stop()

user_id = user.get('user_id')
user_name = user.get('name', user_id)
user_role = user.get('role', '').lower()

# Verify student access
if user_role != 'student':
    st.warning("⚠️ This page is for students only. Redirecting to admin dashboard...")
    st.switch_page("pages/admin_dashboard.py")
    st.stop()

# Main title
st.title(f"👤 My Attendance Profile")
st.markdown(f"**Student:** {user_name} ({user_id})")
st.markdown("---")

# Date range filter in sidebar
st.sidebar.header("📅 Date Range Filter")
date_range_option = st.sidebar.radio(
    "Select date range:",
    ["All Time", "Last 7 Days", "Last 30 Days", "Last 90 Days", "Custom Range"],
    key="student_date_range"
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
    start_date = st.sidebar.date_input("Start Date", value=datetime.now().date() - timedelta(days=30))
    end_date = st.sidebar.date_input("End Date", value=datetime.now().date())
    
    if start_date > end_date:
        st.sidebar.error("Start date must be before end date")
        start_date = None
        end_date = None

# Load student statistics
stats = metrics.get_student_statistics(user_id, start_date=start_date, end_date=end_date)

# Key Performance Indicators
st.subheader("📊 My Statistics")
col1, col2, col3, col4 = st.columns(4)
col1.metric("Total Attendance", stats["total_attendance"])
col2.metric("Attendance Rate", f"{stats['attendance_rate']}%")
col3.metric("Average Score", f"{stats['average_score']:.3f}")
col4.metric("Days Active", stats["days_active"])

st.markdown("---")

# Charts section
st.subheader("📈 My Attendance Analytics")

# Row 1: Attendance Timeline and Rate Gauge
col1, col2 = st.columns([2, 1])

with col1:
    daily_df = metrics.get_student_daily_summary(user_id, start_date=start_date, end_date=end_date)
    timeline_chart = charts.personal_attendance_timeline(daily_df)
    if timeline_chart:
        st.plotly_chart(timeline_chart, use_container_width=True)
    else:
        st.info("No attendance data available for the selected period.")

with col2:
    gauge_chart = charts.attendance_rate_gauge(stats['attendance_rate'])
    if gauge_chart:
        st.plotly_chart(gauge_chart, use_container_width=True)

# Row 2: Score Trends and Verification Success
col1, col2 = st.columns(2)

with col1:
    score_df = metrics.get_student_score_trends(user_id, start_date=start_date, end_date=end_date)
    score_chart = charts.score_trend_chart(score_df)
    if score_chart:
        st.plotly_chart(score_chart, use_container_width=True)
    else:
        st.info("No score trend data available.")

with col2:
    verification_chart = charts.verification_success_chart(stats)
    if verification_chart:
        st.plotly_chart(verification_chart, use_container_width=True)
    else:
        st.info("No verification data available.")

# Row 3: Weekly Pattern
attendance_df = metrics.get_student_attendance_history(user_id, start_date=start_date, end_date=end_date)
weekly_pattern = charts.weekly_attendance_pattern(attendance_df)
if weekly_pattern:
    st.plotly_chart(weekly_pattern, use_container_width=True)

st.markdown("---")

# Recent Records
st.subheader("📋 Recent Attendance Records")

recent_df = metrics.get_student_recent_records(user_id, limit=20)

if not recent_df.empty:
    # Format for display
    display_df = recent_df[['timestamp', 'recognition_score', 'face_verified', 'liveness_verified']].copy()
    display_df['timestamp'] = pd.to_datetime(display_df['timestamp']).dt.strftime('%Y-%m-%d %H:%M:%S')
    display_df['face_verified'] = display_df['face_verified'].map({1: 'Yes', 0: 'No'})
    display_df['liveness_verified'] = display_df['liveness_verified'].map({1: 'Yes', 0: 'No'})
    display_df.columns = ['Date & Time', 'Recognition Score', 'Face Verified', 'Liveness Verified']
    
    st.dataframe(display_df, use_container_width=True, hide_index=True)
else:
    st.info("No recent attendance records available.")

# Footer
st.markdown("---")
st.markdown(
    """
    <div style='text-align: center; color: gray;'>
        <small>Student Attendance Profile | Your Personal Data</small>
    </div>
    """,
    unsafe_allow_html=True
)

