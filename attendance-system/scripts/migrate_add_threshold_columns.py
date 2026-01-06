#!/usr/bin/env python3
"""
Migration script to add threshold_used and system_decision columns to attendance table.
Run this once to update existing database.
"""

import sys
from pathlib import Path

parent_dir = str(Path(__file__).parent.parent)
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

from app.database.db_manager import DatabaseManager
from app.utils.logging import setup_logger

def migrate():
    logger = setup_logger()
    db = DatabaseManager()
    
    try:
        with db.get_connection() as conn:
            cursor = conn.cursor()
            
            # Check if columns exist
            cursor.execute("PRAGMA table_info(attendance)")
            columns = [row[1] for row in cursor.fetchall()]
            
            # Add threshold_used if not exists
            if 'threshold_used' not in columns:
                try:
                    cursor.execute("ALTER TABLE attendance ADD COLUMN threshold_used REAL DEFAULT 0.5")
                    logger.info("Added threshold_used column")
                    print("[OK] Added threshold_used column")
                except Exception as e:
                    logger.error(f"Failed to add threshold_used column: {e}")
                    print(f"[WARNING] threshold_used column may already exist: {e}")
            else:
                logger.info("threshold_used column already exists")
                print("[INFO] threshold_used column already exists")
            
            # Add system_decision if not exists
            if 'system_decision' not in columns:
                try:
                    cursor.execute("ALTER TABLE attendance ADD COLUMN system_decision TEXT")
                    logger.info("Added system_decision column")
                    print("[OK] Added system_decision column")
                except Exception as e:
                    logger.error(f"Failed to add system_decision column: {e}")
                    print(f"[WARNING] system_decision column may already exist: {e}")
            else:
                logger.info("system_decision column already exists")
                print("[INFO] system_decision column already exists")
            
            # Update existing records with default threshold and computed decision
            from app.config.settings import SIMILARITY_THRESHOLD
            
            cursor.execute("""
                UPDATE attendance 
                SET threshold_used = ?,
                    system_decision = CASE 
                        WHEN recognition_score IS NULL THEN NULL
                        WHEN recognition_score >= ? THEN 'accept'
                        ELSE 'reject'
                    END
                WHERE threshold_used IS NULL OR system_decision IS NULL
            """, (SIMILARITY_THRESHOLD, SIMILARITY_THRESHOLD))
            
            updated = cursor.rowcount
            logger.info(f"Updated {updated} existing records with threshold and system_decision")
            print(f"[OK] Updated {updated} existing records with threshold and system_decision")
            
            conn.commit()
            print("\n[SUCCESS] Migration completed successfully!")
            
    except Exception as e:
        logger.error(f"Migration failed: {e}")
        print(f"[ERROR] Migration failed: {e}")
        import traceback
        logger.error(traceback.format_exc())
        raise

if __name__ == "__main__":
    migrate()

