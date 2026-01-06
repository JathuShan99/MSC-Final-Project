#!/usr/bin/env python3
"""
Test load_attendance method to see why it's not returning records.
"""

import sys
from pathlib import Path

parent_dir = str(Path(__file__).parent.parent)
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

from app.analytics.metrics import AttendanceMetrics
from app.database.db_manager import DatabaseManager

def main():
    print("=" * 60)
    print("TESTING load_attendance")
    print("=" * 60)
    print()
    
    # Direct database query
    db = DatabaseManager()
    direct_query = db.execute_query("SELECT COUNT(*) as count FROM attendance")
    direct_count = dict(direct_query[0])['count'] if direct_query else 0
    print(f"Direct DB query count: {direct_count}")
    
    # Using metrics
    metrics = AttendanceMetrics()
    df = metrics.load_attendance()
    print(f"load_attendance() count: {len(df)}")
    
    if df.empty:
        print("\n[ERROR] DataFrame is empty!")
        print("Checking query directly...")
        
        # Try the exact query from load_attendance
        query = """
            SELECT 
                a.id,
                a.user_id,
                u.name,
                u.role,
                a.recognition_score,
                a.face_verified,
                a.liveness_verified,
                a.threshold_used,
                a.system_decision,
                a.timestamp
            FROM attendance a
            LEFT JOIN users u ON a.user_id = u.user_id
            WHERE 1=1
            ORDER BY a.timestamp DESC
        """
        
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query)
            rows = cursor.fetchall()
            print(f"Direct query returned: {len(rows)} rows")
            
            if rows:
                print("\nFirst row sample:")
                first_row = dict(rows[0])
                for key, value in first_row.items():
                    print(f"  {key}: {value}")
    else:
        print("\n[OK] DataFrame loaded successfully!")
        print(f"Columns: {list(df.columns)}")
        print(f"\nFirst 3 rows:")
        print(df.head(3).to_string())

if __name__ == "__main__":
    main()

