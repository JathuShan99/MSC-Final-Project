import streamlit as st
import sys
import os
from pathlib import Path

# Get the attendance-system directory (parent of dashboard)
attendance_system_dir = str(Path(__file__).parent.parent)
if attendance_system_dir not in sys.path:
    sys.path.insert(0, attendance_system_dir)

# Change working directory to attendance-system for proper module resolution
os.chdir(attendance_system_dir)

# Now import dashboard module
from dashboard.auth import DashboardAuth

# Page configuration
st.set_page_config(
    page_title="Attendance System - Login",
    page_icon="🔐",
    layout="centered",
    initial_sidebar_state="collapsed"
)

# Initialize authentication
@st.cache_resource
def get_auth():
    """Cache auth instance."""
    return DashboardAuth()

auth = get_auth()

# Main login page
st.title("🔐 Attendance System Login")
st.markdown("---")

# Check if already authenticated
if auth.is_authenticated():
    user = auth.get_user_session()
    user_role = auth.get_user_role()
    
    st.success(f"✅ Logged in as: {user.get('name', user.get('user_id'))} ({user_role})")
    
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("🚪 Go to Dashboard", use_container_width=True):
            if user_role == 'student':
                st.switch_page("pages/student_profile.py")
            else:
                st.switch_page("pages/admin_dashboard.py")
    
    with col2:
        if st.button("🔓 Logout", use_container_width=True):
            auth.clear_session()
            st.rerun()
    
    st.stop()

# Login form
with st.form("login_form"):
    st.subheader("Enter Your User ID")
    user_id_input = st.text_input(
        "User ID",
        placeholder="Enter your user ID",
        help="Enter the user ID you were assigned during enrollment"
    )
    
    submitted = st.form_submit_button("Login", use_container_width=True)
    
    if submitted:
        if not user_id_input or not user_id_input.strip():
            st.error("⚠️ Please enter a user ID")
        else:
            # Authenticate user
            user = auth.authenticate_user(user_id_input.strip())
            
            if user:
                # Set session
                auth.set_user_session(user)
                user_role = user.get('role', '').lower()
                
                st.success(f"✅ Login successful! Welcome, {user.get('name', user_id_input)}")
                
                # Redirect based on role
                if user_role == 'student':
                    st.info("Redirecting to your student profile...")
                    st.switch_page("pages/student_profile.py")
                else:
                    st.info("Redirecting to admin dashboard...")
                    st.switch_page("pages/admin_dashboard.py")
            else:
                st.error("❌ Invalid user ID or user is inactive. Please check your credentials.")

# Help section
with st.expander("ℹ️ Need Help?"):
    st.markdown("""
    **How to login:**
    1. Enter your User ID (the ID assigned during enrollment)
    2. Click "Login"
    3. You will be redirected to your appropriate dashboard:
       - **Students**: Personal attendance profile
       - **Admins/Staff**: Full analytics dashboard
    
    **Don't have a User ID?**
    - Contact your administrator to get enrolled in the system
    - Or use the enrollment feature in the main application
    """)

# Footer
st.markdown("---")
st.markdown(
    """
    <div style='text-align: center; color: gray;'>
        <small>Attendance System Dashboard | Secure Access</small>
    </div>
    """,
    unsafe_allow_html=True
)
