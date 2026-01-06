#!/usr/bin/env python3
"""
Create test data for evaluation metrics (False Accepts, False Rejects, etc.)

This script creates test attendance records to verify evaluation metrics work correctly.
"""

import sys
from pathlib import Path
from datetime import datetime, timedelta

parent_dir = str(Path(__file__).parent.parent)
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

from app.database.db_manager import DatabaseManager
from app.database.models import Attendance
from app.utils.logging import setup_logger

def create_test_records():
    """
    Create test records for all 4 outcome types:
    1. True Accept: Genuine (face_verified=1) + System Accept
    2. False Reject: Genuine (face_verified=1) + System Reject
    3. False Accept: Impostor (face_verified=0) + System Accept
    4. True Reject: Impostor (face_verified=0) + System Reject
    """
    logger = setup_logger()
    db = DatabaseManager()
    attendance_model = Attendance(db)
    
    print("=" * 60)
    print("CREATING TEST EVALUATION DATA")
    print("=" * 60)
    print()
    
    # Get a valid user_id from database
    user_query = "SELECT user_id FROM users LIMIT 1"
    user_result = db.execute_query(user_query)
    if not user_result:
        print("[ERROR] No users found in database. Please enroll at least one user first.")
        return
    
    test_user_id = dict(user_result[0])['user_id']
    print(f"Using test user_id: {test_user_id}")
    print()
    
    base_time = datetime.now()
    threshold = 0.5
    
    test_cases = [
        # True Accept: Genuine + Accept
        {
            "name": "True Accept",
            "user_id": test_user_id,
            "recognition_score": 0.85,  # High score, above threshold
            "face_verified": 1,  # Genuine
            "liveness_verified": 1,
            "threshold_used": threshold,
            "system_decision": "accept",  # System accepts
            "timestamp": base_time - timedelta(hours=4)
        },
        {
            "name": "True Accept",
            "user_id": test_user_id,
            "recognition_score": 0.75,
            "face_verified": 1,
            "liveness_verified": 1,
            "threshold_used": threshold,
            "system_decision": "accept",
            "timestamp": base_time - timedelta(hours=3)
        },
        {
            "name": "True Accept",
            "user_id": test_user_id,
            "recognition_score": 0.65,
            "face_verified": 1,
            "liveness_verified": 1,
            "threshold_used": threshold,
            "system_decision": "accept",
            "timestamp": base_time - timedelta(hours=2)
        },
        
        # False Reject: Genuine + Reject (legitimate user rejected)
        {
            "name": "False Reject",
            "user_id": test_user_id,
            "recognition_score": 0.45,  # Below threshold, but genuine user
            "face_verified": 1,  # Genuine
            "liveness_verified": 0,  # Liveness might have failed
            "threshold_used": threshold,
            "system_decision": "reject",  # System rejects (WRONG - should accept)
            "timestamp": base_time - timedelta(hours=1)
        },
        {
            "name": "False Reject",
            "user_id": test_user_id,
            "recognition_score": 0.40,  # Below threshold
            "face_verified": 1,  # Genuine
            "liveness_verified": 0,
            "threshold_used": threshold,
            "system_decision": "reject",
            "timestamp": base_time - timedelta(minutes=30)
        },
        
        # False Accept: Impostor + Accept (impostor gets through)
        {
            "name": "False Accept",
            "user_id": test_user_id,
            "recognition_score": 0.75,  # High score, above threshold
            "face_verified": 0,  # Impostor (face mismatch)
            "liveness_verified": 0,
            "threshold_used": threshold,
            "system_decision": "accept",  # System accepts (WRONG - should reject)
            "timestamp": base_time - timedelta(minutes=20)
        },
        {
            "name": "False Accept",
            "user_id": test_user_id,
            "recognition_score": 0.68,  # Above threshold
            "face_verified": 0,  # Impostor
            "liveness_verified": 0,
            "threshold_used": threshold,
            "system_decision": "accept",  # System accepts (WRONG)
            "timestamp": base_time - timedelta(minutes=10)
        },
        
        # True Reject: Impostor + Reject (correctly rejected)
        {
            "name": "True Reject",
            "user_id": test_user_id,
            "recognition_score": 0.35,  # Low score, below threshold
            "face_verified": 0,  # Impostor
            "liveness_verified": 0,
            "threshold_used": threshold,
            "system_decision": "reject",  # System rejects (CORRECT)
            "timestamp": base_time - timedelta(minutes=5)
        },
        {
            "name": "True Reject",
            "user_id": test_user_id,
            "recognition_score": 0.42,  # Below threshold
            "face_verified": 0,  # Impostor
            "liveness_verified": 0,
            "threshold_used": threshold,
            "system_decision": "reject",  # System rejects (CORRECT)
            "timestamp": base_time - timedelta(minutes=2)
        },
    ]
    
    print("Creating test records:")
    print("-" * 60)
    
    created_count = 0
    for i, test_case in enumerate(test_cases, 1):
        try:
            # Insert directly into database with custom timestamp
            with db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO attendance 
                    (user_id, recognition_score, face_verified, liveness_verified, 
                     threshold_used, system_decision, timestamp)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    test_case["user_id"],
                    test_case["recognition_score"],
                    test_case["face_verified"],
                    test_case["liveness_verified"],
                    test_case["threshold_used"],
                    test_case["system_decision"],
                    test_case["timestamp"]
                ))
                conn.commit()
            
            print(f"{i}. {test_case['name']:15} | "
                  f"Score: {test_case['recognition_score']:.2f} | "
                  f"Face: {test_case['face_verified']} | "
                  f"Decision: {test_case['system_decision']}")
            created_count += 1
            
        except Exception as e:
            logger.error(f"Failed to create test record {i}: {e}")
            print(f"  [ERROR] Failed to create: {e}")
    
    print()
    print("=" * 60)
    print(f"[SUCCESS] Created {created_count} test records")
    print("=" * 60)
    print()
    print("Test data breakdown:")
    print("  - True Accepts:  3 (genuine + accept)")
    print("  - False Rejects: 2 (genuine + reject)")
    print("  - False Accepts: 2 (impostor + accept)")
    print("  - True Rejects:  2 (impostor + reject)")
    print()
    print("Now run evaluation to see the metrics:")
    print("  python scripts/run_evaluation.py")
    print()

def main():
    try:
        create_test_records()
    except Exception as e:
        print(f"[ERROR] Failed to create test data: {e}")
        import traceback
        traceback.print_exc()
        return 1
    return 0

if __name__ == "__main__":
    exit(main())

