#!/usr/bin/env python3
"""
Show summary of attendance data in database.
"""

import sys
from pathlib import Path

parent_dir = str(Path(__file__).parent.parent)
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

from app.database.db_manager import DatabaseManager

def main():
    db = DatabaseManager()
    
    print("=" * 60)
    print("ATTENDANCE DATA SUMMARY")
    print("=" * 60)
    print()
    
    # Total count
    total = db.execute_query("SELECT COUNT(*) as count FROM attendance")
    total_count = dict(total[0])['count'] if total else 0
    print(f"Total records: {total_count}")
    
    # Date range
    date_range = db.execute_query("""
        SELECT 
            MIN(timestamp) as first_date,
            MAX(timestamp) as last_date
        FROM attendance
    """)
    
    if date_range:
        r = dict(date_range[0])
        print(f"Date range: {r['first_date']} to {r['last_date']}")
    
    print()
    print("Breakdown by outcome:")
    print("-" * 60)
    
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
        print(f"  {face:10} + {decision:6} = {count:4d} records")
    
    print()
    print("Records per day (last 7 days):")
    print("-" * 60)
    
    daily = db.execute_query("""
        SELECT 
            DATE(timestamp) as date,
            COUNT(*) as count
        FROM attendance
        WHERE timestamp >= datetime('now', '-7 days')
        GROUP BY DATE(timestamp)
        ORDER BY date DESC
        LIMIT 7
    """)
    
    for row in daily:
        r = dict(row)
        print(f"  {r['date']}: {r['count']:3d} records")

if __name__ == "__main__":
    main()

