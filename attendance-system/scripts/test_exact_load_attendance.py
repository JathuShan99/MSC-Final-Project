#!/usr/bin/env python3
"""
Test the exact code from load_attendance.
"""

import sys
from pathlib import Path
import pandas as pd

parent_dir = str(Path(__file__).parent.parent)
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

from app.database.db_manager import DatabaseManager

def test_load_attendance():
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
    """
    params = []
    query += " ORDER BY a.timestamp DESC"
    
    print("Testing exact load_attendance code...")
    print(f"Query: {query[:100]}...")
    print(f"Params: {params}")
    print()
    
    try:
        with db.get_connection() as conn:
            cursor = conn.cursor()
            if params:
                cursor.execute(query, tuple(params))
            else:
                cursor.execute(query)
            
            rows = cursor.fetchall()
            print(f"Rows fetched: {len(rows)}")
            
            if not rows:
                print("No rows, returning empty DataFrame")
                return pd.DataFrame()
            
            # Convert sqlite3.Row objects to dicts
            data = []
            for row in rows:
                try:
                    if hasattr(row, 'keys'):
                        data.append(dict(row))
                    else:
                        columns = [desc[0] for desc in cursor.description]
                        data.append(dict(zip(columns, row)))
                except Exception as row_error:
                    print(f"Error converting row: {row_error}")
                    print(f"Row type: {type(row)}")
                    continue
            
            print(f"Data converted: {len(data)} dicts")
            
            if not data:
                print("No data, returning empty DataFrame")
                return pd.DataFrame()
            
            df = pd.DataFrame(data)
            print(f"DataFrame created: {df.shape}")
            
            # Convert timestamp to datetime
            if 'timestamp' in df.columns:
                df['timestamp'] = pd.to_datetime(df['timestamp'])
            
            print(f"Final DataFrame: {len(df)} rows")
            return df
            
    except Exception as e:
        print(f"[ERROR] {e}")
        import traceback
        traceback.print_exc()
        return pd.DataFrame()

if __name__ == "__main__":
    df = test_load_attendance()
    print()
    print("=" * 60)
    print(f"Result: {len(df)} records")
    if not df.empty:
        print(f"Columns: {list(df.columns)}")
        print(df.head(3))

