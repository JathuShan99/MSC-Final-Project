#!/usr/bin/env python3
"""
Fix system_decision for existing face mismatch records.
Face mismatches (face_verified=0) should always have system_decision='reject'.
"""

import sys
from pathlib import Path

parent_dir = str(Path(__file__).parent.parent)
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

from app.database.db_manager import DatabaseManager
from app.utils.logging import setup_logger

def main():
    logger = setup_logger()
    db = DatabaseManager()
    
    print("=" * 60)
    print("FIXING SYSTEM_DECISION FOR FACE MISMATCHES")
    print("=" * 60)
    print()
    
    try:
        with db.get_connection() as conn:
            cursor = conn.cursor()
            
            # Find face mismatch records with incorrect system_decision
            cursor.execute("""
                SELECT id, user_id, recognition_score, system_decision
                FROM attendance
                WHERE face_verified = 0 
                AND (system_decision IS NULL OR system_decision != 'reject')
            """)
            
            incorrect_records = cursor.fetchall()
            
            if not incorrect_records:
                print("[OK] No records need fixing. All face mismatches already have system_decision='reject'")
                return
            
            print(f"Found {len(incorrect_records)} records to fix:")
            print("-" * 60)
            
            for record in incorrect_records:
                record_id = record[0]
                user_id = record[1]
                score = record[2]
                old_decision = record[3]
                print(f"  ID: {record_id}, User: {user_id}, Score: {score:.3f}, Old Decision: {old_decision}")
            
            print()
            print("Updating records...")
            
            # Update all face mismatch records to have system_decision='reject'
            cursor.execute("""
                UPDATE attendance
                SET system_decision = 'reject'
                WHERE face_verified = 0 
                AND (system_decision IS NULL OR system_decision != 'reject')
            """)
            
            updated = cursor.rowcount
            conn.commit()
            
            print(f"[OK] Updated {updated} records")
            print()
            print("=" * 60)
            print("[SUCCESS] All face mismatch records now have system_decision='reject'")
            print("=" * 60)
            
            logger.info(f"Fixed {updated} face mismatch records with incorrect system_decision")
            
    except Exception as e:
        logger.error(f"Failed to fix records: {e}")
        print(f"[ERROR] Failed to fix records: {e}")
        import traceback
        logger.error(traceback.format_exc())
        raise

if __name__ == "__main__":
    main()

