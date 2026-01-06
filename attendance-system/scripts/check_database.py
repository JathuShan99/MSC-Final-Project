#!/usr/bin/env python3
"""
Check database state and verify test data exists.
"""

import sys
from pathlib import Path

parent_dir = str(Path(__file__).parent.parent)
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

from app.database.db_manager import DatabaseManager
from app.config.paths import DB_PATH

def main():
    print("=" * 60)
    print("DATABASE CHECK")
    print("=" * 60)
    print(f"Database path: {DB_PATH}")
    print(f"Database exists: {DB_PATH.exists()}")
    print()
    
    if not DB_PATH.exists():
        print("[ERROR] Database file does not exist!")
        return
    
    db = DatabaseManager()
    
    # Check users
    users = db.execute_query("SELECT COUNT(*) as count FROM users")
    user_count = dict(users[0])['count'] if users else 0
    print(f"Users in database: {user_count}")
    
    # Check attendance
    attendance = db.execute_query("SELECT COUNT(*) as count FROM attendance")
    attendance_count = dict(attendance[0])['count'] if attendance else 0
    print(f"Attendance records: {attendance_count}")
    print()
    
    if attendance_count == 0:
        print("[WARNING] No attendance records found!")
        print("Run: python scripts/create_test_evaluation_data.py")
        return
    
    # Show breakdown
    print("=" * 60)
    print("ATTENDANCE BREAKDOWN")
    print("=" * 60)
    
    breakdown = db.execute_query("""
        SELECT 
            face_verified,
            system_decision,
            COUNT(*) as count
        FROM attendance
        GROUP BY face_verified, system_decision
        ORDER BY face_verified DESC, system_decision
    """)
    
    for row in breakdown:
        r = dict(row)
        face = "Genuine" if r['face_verified'] == 1 else "Impostor"
        decision = r['system_decision'] or "NULL"
        count = r['count']
        print(f"  {face:10} + {decision:6} = {count:3d} records")
    
    print()
    print("=" * 60)
    print("RECENT RECORDS (Last 5)")
    print("=" * 60)
    
    recent = db.execute_query("""
        SELECT 
            user_id,
            recognition_score,
            face_verified,
            system_decision,
            timestamp
        FROM attendance
        ORDER BY timestamp DESC
        LIMIT 5
    """)
    
    for row in recent:
        r = dict(row)
        print(f"  User: {r['user_id']}, Score: {r['recognition_score']:.3f}, "
              f"Face: {r['face_verified']}, Decision: {r['system_decision']}, "
              f"Time: {r['timestamp']}")

if __name__ == "__main__":
    main()

