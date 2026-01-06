#!/usr/bin/env python3
"""
Debug load_attendance to see what's happening.
"""

import sys
from pathlib import Path
import pandas as pd

parent_dir = str(Path(__file__).parent.parent)
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

from app.database.db_manager import DatabaseManager

def main():
    print("=" * 60)
    print("DEBUGGING load_attendance")
    print("=" * 60)
    print()
    
    db = DatabaseManager()
    
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
    
    try:
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, ())
            rows = cursor.fetchall()
            
            print(f"Rows fetched: {len(rows)}")
            print(f"Row type: {type(rows[0]) if rows else 'No rows'}")
            print()
            
            if rows:
                first_row = rows[0]
                print(f"First row: {first_row}")
                print(f"First row type: {type(first_row)}")
                print(f"Has keys(): {hasattr(first_row, 'keys')}")
                
                if hasattr(first_row, 'keys'):
                    print(f"Keys: {first_row.keys()}")
                    print(f"dict(row): {dict(first_row)}")
                print()
                
                # Try converting
                print("Converting rows to dicts...")
                data = []
                for i, row in enumerate(rows[:3]):  # Just first 3
                    try:
                        if hasattr(row, 'keys'):
                            d = dict(row)
                            print(f"  Row {i}: {d}")
                            data.append(d)
                        else:
                            print(f"  Row {i}: Not a Row object, type={type(row)}")
                    except Exception as e:
                        print(f"  Row {i}: Error converting - {e}")
                
                print()
                print("Creating DataFrame...")
                df = pd.DataFrame(data)
                print(f"DataFrame shape: {df.shape}")
                print(f"DataFrame columns: {list(df.columns)}")
                print()
                print("DataFrame head:")
                print(df.head())
                
    except Exception as e:
        print(f"[ERROR] {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()

