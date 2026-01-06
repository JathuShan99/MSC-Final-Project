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

# Lazy import functions to avoid circular dependency
def _get_models():
    """Lazy import to avoid circular dependency."""
    from app.database.models import User
    from app.database.db_manager import DatabaseManager
    return User, DatabaseManager

def _get_logger():
    """Lazy import to avoid circular dependency."""
    from app.utils.logging import setup_logger
    return setup_logger()


class DashboardAuth:
    """
    Handles authentication and role-based access control for the dashboard.
    """

    def __init__(self):
        # Lazy imports to avoid circular dependency
        User, DatabaseManager = _get_models()
        self.db_manager = DatabaseManager()
        self.user_model = User(self.db_manager)
        self.logger = _get_logger()

    def authenticate_user(self, user_id: str):
        """
        Authenticate user by user_id and return user info.
        
        Args:
            user_id: User ID to authenticate
            
        Returns:
            Dictionary with user info if authenticated, None otherwise
        """
        if not user_id or not user_id.strip():
            return None
        
        user_id = user_id.strip()
        try:
            user = self.user_model.get_by_id(user_id)
            if user and user.get('status') == 'active':
                return user
            return None
        except Exception as e:
            self.logger.error(f"Authentication error for {user_id}: {e}")
            return None

    def check_access(self, user_role: str, required_role: str = None):
        """
        Check if user has required role for access.
        
        Args:
            user_role: User's role (student, staff, admin)
            required_role: Required role (None = any authenticated user)
            
        Returns:
            True if access granted, False otherwise
        """
        if not user_role:
            return False
        
        user_role_lower = user_role.lower()
        
        # Admin/staff have full access
        if user_role_lower in ['admin', 'staff']:
            return True
        
        # Students can only access student view
        if user_role_lower == 'student':
            return required_role == 'student' or required_role is None
        
        return False

    def get_user_session(self):
        """
        Get current logged-in user from session state.
        
        Returns:
            User dictionary if logged in, None otherwise
        """
        if 'user' in st.session_state and st.session_state['user']:
            return st.session_state['user']
        return None

    def set_user_session(self, user: dict):
        """
        Set user in session state.
        
        Args:
            user: User dictionary
        """
        st.session_state['user'] = user
        st.session_state['authenticated'] = True

    def clear_session(self):
        """
        Clear user session.
        """
        if 'user' in st.session_state:
            del st.session_state['user']
        if 'authenticated' in st.session_state:
            del st.session_state['authenticated']

    def is_authenticated(self):
        """
        Check if user is authenticated.
        
        Returns:
            True if authenticated, False otherwise
        """
        return st.session_state.get('authenticated', False)

    def get_user_role(self):
        """
        Get current user's role.
        
        Returns:
            User role string or None
        """
        user = self.get_user_session()
        if user:
            return user.get('role', '').lower()
        return None

