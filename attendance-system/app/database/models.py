from datetime import datetime
from app.database.db_manager import DatabaseManager

class User:
    """
    User model for database operations.
    """
    
    def __init__(self, db_manager: DatabaseManager):
        self.db = db_manager
    
    def create(self, user_id: str, name: str = None, role: str = None, qr_code: str = None, status: str = 'active'):
        """
        Create a new user.
        """
        query = """
            INSERT INTO users (user_id, name, role, qr_code, status)
            VALUES (?, ?, ?, ?, ?)
        """
        try:
            self.db.execute_update(query, (user_id, name, role, qr_code, status))
            return True
        except Exception as e:
            error_msg = str(e)
            error_type = type(e).__name__
            self.db.logger.error(f"Failed to create user {user_id}: {error_type}: {error_msg}")
            self.db.logger.error(f"Full error details: {repr(e)}")
            # Re-raise with more context
            raise Exception(f"Database create failed: {error_type} - {error_msg}") from e
    
    def get_by_id(self, user_id: str):
        """
        Get user by user_id.
        """
        query = "SELECT * FROM users WHERE user_id = ?"
        result = self.db.execute_query(query, (user_id,))
        if result:
            return dict(result[0])
        return None
    
    def update(self, user_id: str, name: str = None, role: str = None, qr_code: str = None, status: str = None):
        """
        Update user information.
        """
        updates = []
        params = []
        
        if name is not None:
            updates.append("name = ?")
            params.append(name)
        if role is not None:
            updates.append("role = ?")
            params.append(role)
        if qr_code is not None:
            updates.append("qr_code = ?")
            params.append(qr_code)
        if status is not None:
            updates.append("status = ?")
            params.append(status)
        
        if not updates:
            return False
        
        params.append(user_id)
        query = f"UPDATE users SET {', '.join(updates)} WHERE user_id = ?"
        
        try:
            self.db.execute_update(query, tuple(params))
            return True
        except Exception as e:
            self.db.logger.error(f"Failed to update user {user_id}: {e}")
            return False
    
    def get_all(self, status: str = None):
        """
        Get all users, optionally filtered by status.
        """
        if status:
            query = "SELECT * FROM users WHERE status = ? ORDER BY created_at DESC"
            result = self.db.execute_query(query, (status,))
        else:
            query = "SELECT * FROM users ORDER BY created_at DESC"
            result = self.db.execute_query(query)
        
        return [dict(row) for row in result]
    
    def delete(self, user_id: str):
        """
        Delete a user and all associated records (cascade delete).
        """
        query = "DELETE FROM users WHERE user_id = ?"
        try:
            self.db.execute_update(query, (user_id,))
            return True
        except Exception as e:
            self.db.logger.error(f"Failed to delete user {user_id}: {e}")
            return False


class FaceTemplate:
    """
    Face template model for database operations.
    """
    
    def __init__(self, db_manager: DatabaseManager):
        self.db = db_manager
    
    def create(self, user_id: str, embedding_path: str):
        """
        Create a face template record.
        """
        query = """
            INSERT INTO face_templates (user_id, embedding_path)
            VALUES (?, ?)
        """
        try:
            self.db.execute_update(query, (user_id, embedding_path))
            return True
        except Exception as e:
            self.db.logger.error(f"Failed to create face template for {user_id}: {e}")
            return False
    
    def get_by_user_id(self, user_id: str):
        """
        Get all face templates for a user.
        """
        query = """
            SELECT * FROM face_templates 
            WHERE user_id = ? 
            ORDER BY created_at DESC
        """
        result = self.db.execute_query(query, (user_id,))
        return [dict(row) for row in result]
    
    def delete(self, template_id: int):
        """
        Delete a face template by ID.
        """
        query = "DELETE FROM face_templates WHERE id = ?"
        try:
            self.db.execute_update(query, (template_id,))
            return True
        except Exception as e:
            self.db.logger.error(f"Failed to delete face template {template_id}: {e}")
            return False
    
    def get_all(self):
        """
        Get all face templates.
        """
        query = """
            SELECT ft.*, u.name, u.role, u.status
            FROM face_templates ft
            JOIN users u ON ft.user_id = u.user_id
            ORDER BY ft.created_at DESC
        """
        result = self.db.execute_query(query)
        return [dict(row) for row in result]


class Attendance:
    """
    Attendance model for database operations.
    """
    
    def __init__(self, db_manager: DatabaseManager):
        self.db = db_manager
    
    def create(self, user_id: str, recognition_score: float = None, 
               face_verified: bool = True, liveness_verified: bool = False,
               threshold_used: float = None, system_decision: str = None):
        """
        Create an attendance record.
        
        Args:
            user_id: User ID
            recognition_score: Similarity score
            face_verified: Whether face matched QR (ground truth)
            liveness_verified: Whether liveness check passed
            threshold_used: Threshold used for system decision (default: SIMILARITY_THRESHOLD)
            system_decision: 'accept' or 'reject' based on threshold
        """
        # Default threshold if not provided
        if threshold_used is None:
            from app.config.settings import SIMILARITY_THRESHOLD
            threshold_used = SIMILARITY_THRESHOLD
        
        # Determine system decision if not provided
        if system_decision is None and recognition_score is not None:
            system_decision = 'accept' if recognition_score >= threshold_used else 'reject'
        
        query = """
            INSERT INTO attendance (user_id, recognition_score, face_verified, liveness_verified, threshold_used, system_decision)
            VALUES (?, ?, ?, ?, ?, ?)
        """
        try:
            self.db.execute_update(query, (
                user_id, 
                recognition_score, 
                1 if face_verified else 0,
                1 if liveness_verified else 0,
                threshold_used,
                system_decision
            ))
            return True
        except Exception as e:
            self.db.logger.error(f"Failed to create attendance record for {user_id}: {e}")
            return False
    
    def get_by_user_id(self, user_id: str, limit: int = None):
        """
        Get attendance records for a user.
        """
        query = "SELECT * FROM attendance WHERE user_id = ? ORDER BY timestamp DESC"
        if limit:
            query += f" LIMIT {limit}"
        
        result = self.db.execute_query(query, (user_id,))
        return [dict(row) for row in result]
    
    def get_all(self, limit: int = None):
        """
        Get all attendance records.
        """
        query = """
            SELECT a.*, u.name, u.role
            FROM attendance a
            JOIN users u ON a.user_id = u.user_id
            ORDER BY a.timestamp DESC
        """
        if limit:
            query += f" LIMIT {limit}"
        
        result = self.db.execute_query(query)
        return [dict(row) for row in result]
    
    def get_by_date_range(self, start_date: str, end_date: str):
        """
        Get attendance records within a date range.
        """
        query = """
            SELECT a.*, u.name, u.role
            FROM attendance a
            JOIN users u ON a.user_id = u.user_id
            WHERE a.timestamp BETWEEN ? AND ?
            ORDER BY a.timestamp DESC
        """
        result = self.db.execute_query(query, (start_date, end_date))
        return [dict(row) for row in result]

