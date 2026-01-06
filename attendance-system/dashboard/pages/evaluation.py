import streamlit as st
import pandas as pd
import sys
from pathlib import Path
from datetime import datetime

# Add parent directory to path for imports
parent_dir = str(Path(__file__).parent.parent.parent)
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

from app.analytics.metrics import AttendanceMetrics
from app.analytics.data_cleaning import DataCleaning
from app.analytics.evaluation import AttendanceEvaluation
from app.analytics.plots import EvaluationPlots
from dashboard.filters import DashboardFilters
from dashboard.auth import DashboardAuth

# Page configuration
st.set_page_config(
    page_title="Biometric Evaluation",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialize services
@st.cache_resource
def get_services():
    return {
        'metrics': AttendanceMetrics(),
        'cleaning': DataCleaning(),
        'evaluator': AttendanceEvaluation(),
        'plots': EvaluationPlots(),
        'filters': DashboardFilters(),
        'auth': DashboardAuth()
    }

services = get_services()
metrics = services['metrics']
cleaning = services['cleaning']
evaluator = services['evaluator']
plots = services['plots']
filters = services['filters']
auth = services['auth']

# Authentication check
if not auth.is_authenticated():
    st.warning("🔒 Please log in to access evaluation.")
    st.stop()

user_session = auth.get_user_session()
user_role = auth.get_user_role()

# Only allow admin/staff
if user_role not in ['admin', 'staff']:
    st.error("Access Denied: Only administrators can access evaluation.")
    st.stop()

st.title("📊 Biometric Evaluation & Performance Analysis")
st.markdown("---")

# Sidebar filters
st.sidebar.header("📅 Data Filters")
filter_values = filters.render_filters()

start_date = filter_values.get('start_date')
end_date = filter_values.get('end_date')
user_id = filter_values.get('user_id')

# Data cleaning option
st.sidebar.header("🧹 Data Options")
apply_cleaning = st.sidebar.checkbox("Apply Data Cleaning", value=True, 
                                     help="Remove duplicates, handle missing values, filter test users")

# Load data
with st.spinner("Loading attendance data..."):
    df = metrics.load_attendance(start_date=start_date, end_date=end_date, user_id=user_id)

if df.empty:
    st.warning("⚠️ No attendance data available for the selected filters.")
    st.stop()

# Apply cleaning
if apply_cleaning:
    with st.spinner("Applying data cleaning (keeping all attempts for evaluation)..."):
        # Skip duplicate removal for evaluation - we need ALL attempts for accurate FAR/FRR
        df = cleaning.clean_attendance_data(
            df,
            normalize_timestamps=True,
            remove_duplicates=False,  # Keep all attempts - important for evaluation
            handle_missing=True,
            flag_outliers=True,
            filter_test_users=True
        )

if df.empty:
    st.warning("⚠️ No data remaining after cleaning.")
    st.stop()

st.success(f"✅ Loaded {len(df)} attendance records")

# Threshold selection
st.sidebar.header("⚙️ Evaluation Settings")
threshold = st.sidebar.slider(
    "Similarity Score Threshold",
    min_value=0.0,
    max_value=1.0,
    value=0.5,
    step=0.01,
    help="Threshold for determining acceptance/rejection"
)

# Compute metrics
# Use stored system_decision for accurate evaluation (recommended)
use_stored = st.sidebar.checkbox(
    "Use Stored System Decision",
    value=True,
    help="Use stored system_decision and threshold_used for accurate evaluation. Recommended for correct FAR/FRR calculation."
)
with st.spinner("Computing evaluation metrics..."):
    metrics_result = evaluator.compute_metrics(df, threshold, use_stored_decision=use_stored)
    eer_result = evaluator.find_eer_threshold(df)
    stats = evaluator.get_score_statistics(df)

# Display metrics
st.subheader("📈 Key Performance Metrics")

col1, col2, col3, col4 = st.columns(4)
col1.metric("FAR", f"{metrics_result['FAR']:.4f}", f"{metrics_result['FAR']*100:.2f}%")
col2.metric("FRR", f"{metrics_result['FRR']:.4f}", f"{metrics_result['FRR']*100:.2f}%")
col3.metric("Accuracy", f"{metrics_result['accuracy']:.4f}", f"{metrics_result['accuracy']*100:.2f}%")
col4.metric("EER", f"{eer_result['eer_value']:.4f}", f"@ {eer_result['eer_threshold']:.3f}")

st.markdown("---")

# Detailed metrics
with st.expander("📋 Detailed Metrics", expanded=False):
    col1, col2 = st.columns(2)
    
    with col1:
        st.write("**Attempt Counts:**")
        st.write(f"- Total Attempts: {metrics_result['total_attempts']}")
        st.write(f"- Genuine Attempts: {metrics_result['genuine_attempts']}")
        st.write(f"- Impostor Attempts: {metrics_result['impostor_attempts']}")
    
    with col2:
        st.write("**Classification Results:**")
        st.write(f"- True Accepts: {metrics_result['true_accepts']}")
        st.write(f"- True Rejects: {metrics_result['true_rejects']}")
        st.write(f"- False Accepts: {metrics_result['false_accepts']}")
        st.write(f"- False Rejects: {metrics_result['false_rejects']}")

# Score statistics
if stats['genuine'] or stats['impostor']:
    with st.expander("📊 Score Statistics", expanded=False):
        col1, col2 = st.columns(2)
        
        if stats['genuine']:
            with col1:
                st.write("**Genuine Attempts:**")
                st.json(stats['genuine'])
        
        if stats['impostor']:
            with col2:
                st.write("**Impostor Attempts:**")
                st.json(stats['impostor'])

st.markdown("---")

# Visualizations
st.subheader("📊 Evaluation Visualizations")

# Row 1: Score Distribution and Genuine vs Impostor
col1, col2 = st.columns(2)

with col1:
    st.write("**Recognition Score Distribution**")
    fig = plots.score_distribution_histogram(df, backend='plotly')
    if fig:
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No data available for score distribution.")

with col2:
    st.write("**Genuine vs Impostor Distribution**")
    fig = plots.genuine_vs_impostor_distribution(df, backend='plotly')
    if fig:
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No data available for genuine/impostor distribution.")

# Row 2: FAR/FRR Curve and Accuracy Curve
col1, col2 = st.columns(2)

with col1:
    st.write("**FAR / FRR vs Threshold**")
    fig = plots.far_frr_curve(df, backend='plotly')
    if fig:
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No data available for FAR/FRR curve.")

with col2:
    st.write("**Accuracy vs Threshold**")
    fig = plots.accuracy_curve(df, backend='plotly')
    if fig:
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No data available for accuracy curve.")

st.markdown("---")

# Export section
st.subheader("💾 Export Results")

col1, col2 = st.columns(2)

with col1:
    if st.button("📥 Export Metrics (CSV)", use_container_width=True):
        try:
            from app.config.paths import EXPORTS_DIR
            from app.analytics.reports import ReportService
            
            reports = ReportService()
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            
            # Create metrics summary
            summary_df = pd.DataFrame([{
                'threshold': metrics_result['threshold'],
                'FAR': metrics_result['FAR'],
                'FRR': metrics_result['FRR'],
                'accuracy': metrics_result['accuracy'],
                'total_attempts': metrics_result['total_attempts'],
                'genuine_attempts': metrics_result['genuine_attempts'],
                'impostor_attempts': metrics_result['impostor_attempts'],
                'true_accepts': metrics_result['true_accepts'],
                'true_rejects': metrics_result['true_rejects'],
                'false_accepts': metrics_result['false_accepts'],
                'false_rejects': metrics_result['false_rejects'],
                'eer_threshold': eer_result['eer_threshold'],
                'eer_value': eer_result['eer_value']
            }])
            
            filepath = EXPORTS_DIR / f"evaluation_metrics_{timestamp}.csv"
            filepath.parent.mkdir(parents=True, exist_ok=True)
            summary_df.to_csv(filepath, index=False)
            st.success(f"✅ Metrics exported to: `{filepath}`")
        except Exception as e:
            st.error(f"❌ Error exporting metrics: {e}")

with col2:
    if st.button("📊 Export Plots (PNG)", use_container_width=True):
        try:
            from app.config.paths import EXPORTS_DIR
            import matplotlib.pyplot as plt
            
            output_dir = EXPORTS_DIR / "evaluation"
            output_dir.mkdir(parents=True, exist_ok=True)
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            
            # Generate and save all plots
            fig1 = plots.score_distribution_histogram(df, backend='matplotlib')
            if fig1:
                plots.save_matplotlib_figure(fig1, output_dir / f"score_distribution_{timestamp}.png")
                plt.close(fig1)
            
            fig2 = plots.genuine_vs_impostor_distribution(df, backend='matplotlib')
            if fig2:
                plots.save_matplotlib_figure(fig2, output_dir / f"genuine_impostor_{timestamp}.png")
                plt.close(fig2)
            
            fig3 = plots.far_frr_curve(df, backend='matplotlib')
            if fig3:
                plots.save_matplotlib_figure(fig3, output_dir / f"far_frr_curve_{timestamp}.png")
                plt.close(fig3)
            
            fig4 = plots.accuracy_curve(df, backend='matplotlib')
            if fig4:
                plots.save_matplotlib_figure(fig4, output_dir / f"accuracy_curve_{timestamp}.png")
                plt.close(fig4)
            
            st.success(f"✅ Plots exported to: `{output_dir}`")
        except Exception as e:
            st.error(f"❌ Error exporting plots: {e}")

# Footer
st.markdown("---")
st.markdown(
    """
    <div style='text-align: center; color: gray;'>
        <small>Biometric Evaluation Dashboard | FAR/FRR Analysis | Research-Grade Metrics</small>
    </div>
    """,
    unsafe_allow_html=True
)

