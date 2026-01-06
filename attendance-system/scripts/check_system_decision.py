#!/usr/bin/env python3
"""
Check system_decision for face mismatch records.
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
    print("CHECKING SYSTEM_DECISION FOR FACE MISMATCHES")
    print("=" * 60)
    print()
    
    # Check face mismatch records
    query = """
        SELECT 
            user_id,
            recognition_score,
            face_verified,
            system_decision,
            threshold_used
        FROM attendance 
        WHERE face_verified = 0
        ORDER BY timestamp DESC
    """
    
    rows = db.execute_query(query)
    
    if not rows:
        print("No face mismatch records found.")
        return
    
    print(f"Found {len(rows)} face mismatch records:")
    print("-" * 60)
    
    incorrect = 0
    for row in rows:
        r = dict(row)
        user_id = r['user_id']
        score = r['recognition_score']
        decision = r['system_decision']
        threshold = r['threshold_used']
        
        # Check if decision is correct
        # Face mismatch should always be 'reject'
        if decision and decision.lower() != 'reject':
            status = "[INCORRECT]"
            incorrect += 1
        else:
            status = "[OK]"
        
        print(f"{status} User: {user_id}, Score: {score:.3f}, Decision: {decision}, Threshold: {threshold}")
    
    print()
    print("=" * 60)
    if incorrect > 0:
        print(f"[WARNING] Found {incorrect} records with incorrect system_decision")
        print("Face mismatches should always have system_decision='reject'")
    else:
        print("[OK] All face mismatch records have system_decision='reject'")
    print("=" * 60)

if __name__ == "__main__":
    main()

