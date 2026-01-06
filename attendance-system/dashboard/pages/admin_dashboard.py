import streamlit as st
import pandas as pd
import sys
import os
from pathlib import Path

# Get the attendance-system directory
attendance_system_dir = str(Path(__file__).parent.parent.parent)
if attendance_system_dir not in sys.path:
    sys.path.insert(0, attendance_system_dir)

# Change working directory to attendance-system for proper module resolution
os.chdir(attendance_system_dir)

from app.analytics.metrics import AttendanceMetrics
from app.analytics.reports import ReportService
from app.analytics.data_cleaning import DataCleaning
from dashboard.filters import DashboardFilters
from dashboard.charts import DashboardCharts
from dashboard.auth import DashboardAuth

# Page configuration
st.set_page_config(
    page_title="Admin Dashboard",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialize services
@st.cache_resource
def get_services():
    """Cache service instances for performance."""
    return {
        'metrics': AttendanceMetrics(),
        'reports': ReportService(),
        'filters': DashboardFilters(),
        'charts': DashboardCharts(),
        'cleaning': DataCleaning(),
        'auth': DashboardAuth()
    }

services = get_services()
metrics = services['metrics']
reports = services['reports']
filters = services['filters']
charts = services['charts']
cleaning = services['cleaning']
auth = services['auth']

# Check authentication
user = auth.get_user_session()
if not user:
    st.error("⚠️ Please log in to access the admin dashboard.")
    st.stop()

user_role = auth.get_user_role()
if user_role not in ['admin', 'staff']:
    st.warning("⚠️ Admin access required. Redirecting to student profile...")
    st.switch_page("pages/student_profile.py")
    st.stop()

# Main title
st.title("📊 Attendance Analytics Dashboard - Admin View")
st.markdown("---")

# Navigation links
col1, col2, col3 = st.columns(3)
with col1:
    if st.button("📊 Go to Evaluation", use_container_width=True):
        st.switch_page("pages/evaluation.py")
with col2:
    st.write("")  # Spacer
with col3:
    st.write("")  # Spacer
st.markdown("---")

# Sidebar filters
filter_values = filters.render_filters()

# Data cleaning option
st.sidebar.header("🧹 Data Options")
apply_cleaning = st.sidebar.checkbox("Apply Data Cleaning", value=False, help="Remove duplicates, handle missing values, filter test users")

# Apply filters
start_date = filter_values.get('start_date')
end_date = filter_values.get('end_date')
user_id = filter_values.get('user_id')

# Display active filters
if start_date or end_date or user_id:
    with st.expander("🔍 Active Filters", expanded=False):
        col1, col2, col3 = st.columns(3)
        with col1:
            st.write(f"**Start Date:** {start_date if start_date else 'N/A'}")
        with col2:
            st.write(f"**End Date:** {end_date if end_date else 'N/A'}")
        with col3:
            st.write(f"**User:** {user_id if user_id else 'All Users'}")

# Load data
attendance_df = metrics.load_attendance(
    start_date=start_date,
    end_date=end_date,
    user_id=user_id
)

# Apply data cleaning if requested
if apply_cleaning and not attendance_df.empty:
    attendance_df = cleaning.clean_attendance_data(attendance_df)
    st.sidebar.success("✅ Data cleaning applied")

# Key Performance Indicators (KPIs)
st.subheader("📈 Key Performance Indicators")
stats = metrics.verification_stats(start_date=start_date, end_date=end_date)

col1, col2, col3, col4 = st.columns(4)
col1.metric("Total Records", stats["total_records"])
col2.metric("Face Verified", f"{stats['face_verified']} ({stats['face_verification_rate']}%)")
col3.metric("Liveness Verified", f"{stats['liveness_verified']} ({stats['liveness_verification_rate']}%)")
col4.metric("Multi-Factor Verified", f"{stats['multi_factor_verified']} ({stats['multi_factor_rate']}%)")

st.markdown("---")

# Charts section
st.subheader("📊 Visualizations")

# Row 1: Daily and Weekly trends
col1, col2 = st.columns(2)

with col1:
    daily_df = metrics.daily_summary(start_date=start_date, end_date=end_date)
    daily_chart = charts.daily_attendance_chart(daily_df)
    if daily_chart:
        st.plotly_chart(daily_chart, use_container_width=True)
    else:
        st.info("No daily attendance data available for the selected period.")

with col2:
    weekly_df = metrics.weekly_summary(start_date=start_date, end_date=end_date)
    weekly_chart = charts.weekly_attendance_chart(weekly_df)
    if weekly_chart:
        st.plotly_chart(weekly_chart, use_container_width=True)
    else:
        st.info("No weekly attendance data available for the selected period.")

# Row 2: User attendance and Hourly distribution
col1, col2 = st.columns(2)

with col1:
    user_df = metrics.user_summary(start_date=start_date, end_date=end_date)
    user_chart = charts.user_attendance_chart(user_df)
    if user_chart:
        st.plotly_chart(user_chart, use_container_width=True)
    else:
        st.info("No user attendance data available.")

with col2:
    hourly_df = metrics.hourly_distribution(start_date=start_date, end_date=end_date)
    hourly_chart = charts.hourly_distribution_chart(hourly_df)
    if hourly_chart:
        st.plotly_chart(hourly_chart, use_container_width=True)
    else:
        st.info("No hourly distribution data available.")

# Row 3: Advanced Charts - Heatmap and Funnel
col1, col2 = st.columns(2)

with col1:
    if not attendance_df.empty:
        heatmap_chart = charts.weekly_heatmap_chart(attendance_df)
        if heatmap_chart:
            st.plotly_chart(heatmap_chart, use_container_width=True)
        else:
            st.info("No data available for heatmap.")
    else:
        st.info("No data available for heatmap.")

with col2:
    if not attendance_df.empty:
        funnel_chart = charts.multi_factor_funnel_chart(attendance_df)
        if funnel_chart:
            st.plotly_chart(funnel_chart, use_container_width=True)
        else:
            st.info("No data available for funnel chart.")
    else:
        st.info("No data available for funnel chart.")

# Row 4: Verification stats and Liveness failure rate
col1, col2 = st.columns(2)

with col1:
    verification_chart = charts.verification_stats_chart(stats)
    if verification_chart:
        st.plotly_chart(verification_chart, use_container_width=True)
    else:
        st.info("No verification statistics available.")

with col2:
    if not attendance_df.empty:
        liveness_chart = charts.liveness_failure_rate_chart(attendance_df, group_by='date')
        if liveness_chart:
            st.plotly_chart(liveness_chart, use_container_width=True)
        else:
            st.info("No liveness failure data available.")
    else:
        st.info("No data available for liveness failure rate.")

# Row 5: Recognition Score Distribution
if not attendance_df.empty:
    score_chart = charts.recognition_score_distribution(attendance_df)
    if score_chart:
        st.plotly_chart(score_chart, use_container_width=True)

st.markdown("---")

# Recognition Score Statistics
st.subheader("🎯 Recognition Score Statistics")
score_stats = metrics.recognition_score_stats(start_date=start_date, end_date=end_date)

col1, col2, col3, col4, col5 = st.columns(5)
col1.metric("Mean", f"{score_stats['mean']:.3f}")
col2.metric("Median", f"{score_stats['median']:.3f}")
col3.metric("Min", f"{score_stats['min']:.3f}")
col4.metric("Max", f"{score_stats['max']:.3f}")
col5.metric("Std Dev", f"{score_stats['std']:.3f}")

st.markdown("---")

# Raw data view
st.subheader("📋 Raw Attendance Data")

if not attendance_df.empty:
    # Display summary info
    st.info(f"Showing {len(attendance_df)} attendance record(s)")
    
    # Display dataframe
    st.dataframe(
        attendance_df,
        use_container_width=True,
        hide_index=True
    )
    
    # Export buttons
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("📥 Export Full Data (CSV)", use_container_width=True):
            try:
                filepath = reports.export_csv(
                    start_date=start_date,
                    end_date=end_date,
                    user_id=user_id
                )
                if filepath:
                    st.success(f"✅ Report exported successfully to: `{filepath}`")
            except Exception as e:
                st.error(f"❌ Error exporting report: {e}")
    
    with col2:
        if st.button("📊 Export Summary Report (CSV)", use_container_width=True):
            try:
                filepath = reports.export_summary_report(
                    start_date=start_date,
                    end_date=end_date
                )
                if filepath:
                    st.success(f"✅ Summary report exported successfully to: `{filepath}`")
            except Exception as e:
                st.error(f"❌ Error exporting summary report: {e}")
else:
    st.warning("⚠️ No attendance data available for the selected filters.")

# Footer
st.markdown("---")
st.markdown(
    """
    <div style='text-align: center; color: gray;'>
        <small>Admin Attendance Analytics Dashboard | GDPR Compliant | No Biometric Data Stored</small>
    </div>
    """,
    unsafe_allow_html=True
)

