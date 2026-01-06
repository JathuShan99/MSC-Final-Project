#!/usr/bin/env python3
"""
Generate 100 dummy attendance records spread over a 1-month period.
Useful for testing analytics and evaluation metrics.
"""

import sys
from pathlib import Path
from datetime import datetime, timedelta
import random

parent_dir = str(Path(__file__).parent.parent)
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

from app.database.db_manager import DatabaseManager
from app.utils.logging import setup_logger

def main():
    logger = setup_logger()
    db = DatabaseManager()
    
    print("=" * 60)
    print("GENERATING DUMMY ATTENDANCE DATA")
    print("=" * 60)
    print()
    
    # Get existing users
    users = db.execute_query("SELECT user_id FROM users")
    if not users:
        print("[ERROR] No users found in database. Please enroll at least one user first.")
        return 1
    
    user_ids = [dict(u)['user_id'] for u in users]
    print(f"Found {len(user_ids)} users: {', '.join(user_ids)}")
    print()
    
    # Date range: Last 30 days
    end_date = datetime.now()
    start_date = end_date - timedelta(days=30)
    
    print(f"Date range: {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}")
    print(f"Generating 100 records...")
    print()
    
    # Distribution of outcome types (realistic mix)
    # True Accept: 60% (genuine users, accepted)
    # False Reject: 10% (genuine users, rejected)
    # False Accept: 5% (impostors, accepted)
    # True Reject: 25% (impostors, rejected)
    
    outcome_configs = [
        # (name, face_verified, system_decision, count, score_range)
        ("True Accept", 1, "accept", 60, (0.55, 0.95)),  # Genuine + Accept
        ("False Reject", 1, "reject", 10, (0.35, 0.49)),  # Genuine + Reject
        ("False Accept", 0, "accept", 5, (0.51, 0.75)),   # Impostor + Accept
        ("True Reject", 0, "reject", 25, (0.20, 0.50)),   # Impostor + Reject
    ]
    
    threshold = 0.5
    records_created = 0
    
    # Generate timestamps spread over 30 days
    # Mix of weekdays and weekends, different times of day
    timestamps = []
    for i in range(100):
        # Random day within the month
        days_offset = random.randint(0, 29)
        date = start_date + timedelta(days=days_offset)
        
        # Random time (8 AM to 6 PM, weighted towards morning)
        hour = random.choices(
            range(8, 19),
            weights=[3, 3, 4, 4, 3, 2, 2, 2, 1, 1, 1]  # More weight to 8-11 AM
        )[0]
        minute = random.randint(0, 59)
        second = random.randint(0, 59)
        
        timestamp = date.replace(hour=hour, minute=minute, second=second)
        timestamps.append(timestamp)
    
    # Sort timestamps chronologically
    timestamps.sort()
    
    # Generate records
    record_idx = 0
    
    for outcome_name, face_verified, system_decision, count, score_range in outcome_configs:
        print(f"Creating {count} {outcome_name} records...")
        
        for i in range(count):
            user_id = random.choice(user_ids)
            recognition_score = round(random.uniform(*score_range), 3)
            liveness_verified = 1 if face_verified == 1 and system_decision == "accept" else random.choice([0, 1])
            timestamp = timestamps[record_idx]
            
            try:
                with db.get_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute("""
                        INSERT INTO attendance 
                        (user_id, recognition_score, face_verified, liveness_verified, 
                         threshold_used, system_decision, timestamp)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                    """, (
                        user_id,
                        recognition_score,
                        face_verified,
                        liveness_verified,
                        threshold,
                        system_decision,
                        timestamp
                    ))
                    conn.commit()
                
                records_created += 1
                record_idx += 1
                
            except Exception as e:
                logger.error(f"Failed to create record {i+1} of {outcome_name}: {e}")
                print(f"  [ERROR] Failed: {e}")
    
    print()
    print("=" * 60)
    print(f"[SUCCESS] Created {records_created} dummy attendance records")
    print("=" * 60)
    print()
    
    # Show summary
    summary = db.execute_query("""
        SELECT 
            face_verified,
            system_decision,
            COUNT(*) as count
        FROM attendance
        WHERE timestamp >= ?
        GROUP BY face_verified, system_decision
        ORDER BY face_verified DESC, system_decision
    """, (start_date.strftime('%Y-%m-%d'),))
    
    print("Summary of generated records:")
    print("-" * 60)
    for row in summary:
        r = dict(row)
        face = "Genuine" if r['face_verified'] == 1 else "Impostor"
        decision = r['system_decision']
        count = r['count']
        print(f"  {face:10} + {decision:6} = {count:3d} records")
    
    print()
    print("Date range coverage:")
    date_range = db.execute_query("""
        SELECT 
            DATE(timestamp) as date,
            COUNT(*) as count
        FROM attendance
        WHERE timestamp >= ?
        GROUP BY DATE(timestamp)
        ORDER BY date
    """, (start_date.strftime('%Y-%m-%d'),))
    
    if date_range:
        first_date = dict(date_range[0])['date']
        last_date = dict(date_range[-1])['date']
        total_days = len(date_range)
        print(f"  Dates: {first_date} to {last_date} ({total_days} days with records)")
    
    print()
    print("You can now run evaluation:")
    print("  python scripts/run_evaluation.py")
    print("  python scripts/verify_evaluation_outcomes.py")
    
    return 0

if __name__ == "__main__":
    exit(main())

