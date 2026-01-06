import sqlite3
from pathlib import Path
from contextlib import contextmanager
from app.config.paths import DB_PATH
from app.utils.logging import setup_logger

class DatabaseManager:
    """
    Manages SQLite database connections and operations.
    """
    
    def __init__(self):
        self.db_path = DB_PATH
        self.logger = setup_logger()
    
    @contextmanager
    def get_connection(self):
        """
        Context manager for database connections.
        Ensures proper connection handling and rollback on errors.
        """
        conn = None
        try:
            conn = sqlite3.connect(str(self.db_path))
            conn.row_factory = sqlite3.Row  # Enable column access by name
            conn.execute("PRAGMA foreign_keys = ON")  # Enable foreign keys
            yield conn
            conn.commit()
        except sqlite3.Error as e:
            if conn:
                conn.rollback()
            self.logger.error(f"Database error: {e}")
            raise
        finally:
            if conn:
                conn.close()
    
    def initialize_db(self):
        """
        Initialize database by creating tables from schema.sql
        """
        schema_path = Path(__file__).parent / "schema.sql"
        
        if not schema_path.exists():
            self.logger.error(f"Schema file not found: {schema_path}")
            raise FileNotFoundError(f"Schema file not found: {schema_path}")
        
        try:
            with self.get_connection() as conn:
                with open(schema_path, 'r') as f:
                    schema_sql = f.read()
                    conn.executescript(schema_sql)
                self.logger.info("Database initialized successfully")
            
            # Run migrations for existing databases
            self.migrate_add_qr_code_column()
        except sqlite3.Error as e:
            self.logger.error(f"Failed to initialize database: {e}")
            raise
    
    def execute_query(self, query, params=None):
        """
        Execute a query and return results.
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)
            return cursor.fetchall()
    
    def execute_update(self, query, params=None):
        """
        Execute an update/insert/delete query.
        Returns the last row ID for INSERT operations.
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)
            conn.commit()
            return cursor.lastrowid
    
    def table_exists(self, table_name):
        """
        Check if a table exists in the database.
        """
        query = """
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name=?
        """
        result = self.execute_query(query, (table_name,))
        return len(result) > 0
    
    def is_initialized(self):
        """
        Check if database is initialized (has required tables).
        """
        required_tables = ['users', 'face_templates', 'attendance']
        return all(self.table_exists(table) for table in required_tables)
    
    def column_exists(self, table_name, column_name):
        """
        Check if a column exists in a table.
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(f"PRAGMA table_info({table_name})")
                columns = [row[1] for row in cursor.fetchall()]
                return column_name in columns
        except sqlite3.Error as e:
            self.logger.error(f"Failed to check column existence: {e}")
            return False
    
    def migrate_add_qr_code_column(self):
        """
        Migration: Add qr_code column to users table if it doesn't exist.
        """
        if not self.table_exists('users'):
            self.logger.warning("Users table doesn't exist, skipping migration")
            return
        
        if self.column_exists('users', 'qr_code'):
            self.logger.info("qr_code column already exists, skipping migration")
            return
        
        try:
            with self.get_connection() as conn:
                conn.execute("ALTER TABLE users ADD COLUMN qr_code TEXT")
                self.logger.info("Successfully added qr_code column to users table")
        except sqlite3.Error as e:
            self.logger.error(f"Failed to add qr_code column: {e}")
            raise

