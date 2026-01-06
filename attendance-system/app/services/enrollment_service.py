import cv2
import numpy as np
import time
from pathlib import Path
from app.core.face_detector import FaceDetector
from app.core.face_recognizer import FaceRecognizer
from app.core.id_validator import IDValidator
from app.config.settings import ENROLLMENT_SAMPLE_COUNT
from app.config.paths import EMBEDDINGS_DIR
from app.utils.logging import setup_logger
from app.utils.qr_generator import QRGenerator
from app.database.db_manager import DatabaseManager
from app.database.models import User, FaceTemplate

class EnrollmentService:
    """
    Handles biometric enrollment.
    """
    def __init__(self):
        self.detector = FaceDetector()
        self.id_validator = IDValidator()
        self.qr_generator = QRGenerator()
        self.logger = setup_logger()
        self.db_manager = DatabaseManager()
        self.user_model = User(self.db_manager)
        self.template_model = FaceTemplate(self.db_manager)
    
    def generate_user_id(self):
        """
        Generate the next sequential user ID (e.g., 0001, 0002, ...).
        Checks both database and file system for existing IDs.
        """
        max_id = 0
        
        # Check database for existing user IDs
        try:
            if self.db_manager.is_initialized():
                users = self.user_model.get_all()
                for user in users:
                    user_id = user['user_id']
                    # Try to parse as integer
                    try:
                        user_num = int(user_id)
                        max_id = max(max_id, user_num)
                    except ValueError:
                        # Skip non-numeric IDs
                        continue
        except Exception as e:
            self.logger.warning(f"Could not query database for user IDs: {e}")
        
        # Check file system for existing .npy files
        for file in EMBEDDINGS_DIR.glob("*.npy"):
            try:
                user_num = int(file.stem)
                max_id = max(max_id, user_num)
            except ValueError:
                # Skip non-numeric filenames
                continue
        
        # Generate next ID (4 digits with leading zeros)
        next_id = max_id + 1
        return f"{next_id:04d}"
    
    def _load_existing_embeddings(self):
        """
        Load all existing embeddings for duplicate checking.
        Returns dictionary of {user_id: embeddings_array}
        """
        embeddings = {}
        
        # Load from database
        try:
            if self.db_manager.is_initialized():
                templates = self.template_model.get_all()
                for template in templates:
                    user_id = template['user_id']
                    embedding_path = Path(template['embedding_path'])
                    
                    if embedding_path.exists():
                        embeddings[user_id] = np.load(embedding_path)
        except Exception as e:
            self.logger.warning(f"Could not load embeddings from database: {e}")
        
        # Also check file system (for backward compatibility)
        for file in EMBEDDINGS_DIR.glob("*.npy"):
            user_id = file.stem
            if user_id not in embeddings:  # Don't overwrite database entries
                try:
                    embeddings[user_id] = np.load(file)
                except Exception as e:
                    self.logger.warning(f"Could not load embedding file {file}: {e}")
        
        return embeddings
    
    def check_duplicate_face(self, test_embedding):
        """
        Check if the test embedding matches any existing enrolled face.
        Returns (is_duplicate, matched_user_id, similarity_score) or (False, None, None)
        """
        existing_embeddings = self._load_existing_embeddings()
        
        if not existing_embeddings:
            return False, None, None
        
        for user_id, stored_embeddings in existing_embeddings.items():
            is_match, score = FaceRecognizer.compare(test_embedding, stored_embeddings)
            if is_match:
                return True, user_id, score
        
        return False, None, None

    def update_enrollment(self, user_id: str, name: str = None, role: str = None):
        """
        Update/re-enroll an existing user by rescanning face and QR code.
        
        Args:
            user_id: The user ID to update
            name: Optional name update
            role: Optional role update
        """
        # Check if user exists
        existing_user = self.user_model.get_by_id(user_id)
        if not existing_user:
            print(f"Error: User '{user_id}' not found.")
            self.logger.error(f"Update enrollment failed: User {user_id} not found")
            return False
        
        print(f"\nUpdating enrollment for user: {user_id}")
        print("This will capture new face samples and QR code.")
        
        # Proceed with enrollment (same process, but will update existing user)
        self.enroll(user_id=user_id, name=name, role=role, update_mode=True)
    
    def enroll(self, user_id: str = None, name: str = None, role: str = None, update_mode: bool = False):
        # Require name and role for new enrollments
        if not update_mode:
            if not name or name.strip() == "":
                print("Error: Name is required for enrollment.")
                return False
            if not role or role.strip() == "":
                print("Error: Role is required for enrollment.")
                return False
        
        # Generate user ID if not provided
        if user_id is None or user_id.strip() == "":
            user_id = self.generate_user_id()
            print(f"Auto-generated User ID: {user_id}")
        
        user_id = user_id.strip()
        name = name.strip() if name else None
        role = role.strip() if role else None
        
        cap = cv2.VideoCapture(0)
        
        # Verify webcam is accessible
        if not cap.isOpened():
            self.logger.error("Failed to open webcam")
            print("Error: Could not access webcam. Please check if it's connected and not in use by another application.")
            return
        
        # Set webcam properties for better performance
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        
        # Allow webcam to initialize
        time.sleep(0.5)
        
        # Read a few frames to let the camera stabilize
        for _ in range(5):
            cap.read()
        
        # Create window explicitly and set properties
        cv2.namedWindow("Enrollment", cv2.WINDOW_NORMAL)
        cv2.resizeWindow("Enrollment", 640, 480)
        
        embeddings = []
        duplicate_checked = False
        qr_code_scanned = None
        qr_scan_complete = False
        qr_generated = False
        
        mode_text = "Updating enrollment" if update_mode else "Enrollment"
        self.logger.info(f"{mode_text} started for user: {user_id}")
        print(f"{mode_text} started for user: {user_id}")
        print("Position your face in front of the camera. Press ESC to cancel.")
        print("Options:")
        print("  - Press 'G' to generate a QR code for this user")
        print("  - Show your QR code to scan it (will be captured automatically)")
        if update_mode:
            print("  - New face samples and QR code will replace existing data")

        while len(embeddings) < ENROLLMENT_SAMPLE_COUNT:
            ret, frame = cap.read()
            if not ret:
                print("Warning: Could not read frame from webcam")
                continue

            # Flip frame horizontally for mirror effect
            frame = cv2.flip(frame, 1)
            
            # Draw status on frame
            status_text = f"Sample {len(embeddings)}/{ENROLLMENT_SAMPLE_COUNT}"
            cv2.putText(frame, status_text, (10, 30), 
                       cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
            
            # Scan for QR code during enrollment (continuous scanning)
            if not qr_scan_complete:
                scanned_qr = self.id_validator.scan(frame)
                if scanned_qr:
                    qr_code_scanned = scanned_qr
                    qr_scan_complete = True
                    print(f"\n✓ QR code detected: {qr_code_scanned}")
                    # Optionally validate QR matches user_id if user_id was provided
                    if user_id and scanned_qr != user_id:
                        print(f"⚠️  Warning: QR code ({scanned_qr}) doesn't match User ID ({user_id})")
                        if not update_mode:  # Only ask in new enrollment, auto-accept in update mode
                            response = input("Continue anyway? (yes/no): ").strip().lower()
                            if response not in ['yes', 'y']:
                                cap.release()
                                cv2.destroyAllWindows()
                                print("Enrollment cancelled.")
                                return
                
                # Show QR scan status
                if qr_scan_complete:
                    qr_status = f"QR: {qr_code_scanned} ✓"
                    qr_color = (0, 255, 0)
                else:
                    qr_status = "Show QR code..."
                    qr_color = (255, 255, 0)
                
                cv2.putText(frame, qr_status, (10, 70), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.7, qr_color, 2)
            
            faces = self.detector.detect(frame)
            
            if len(faces) == 0:
                face_status = "No face detected"
                face_y = 100 if qr_scan_complete else 100
                cv2.putText(frame, face_status, (10, face_y), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
            elif len(faces) > 1:
                face_status = "Multiple faces detected"
                face_y = 100 if qr_scan_complete else 100
                cv2.putText(frame, face_status, (10, face_y), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
            else:
                # Draw bounding box around detected face
                bbox = faces[0].bbox.astype(int)
                cv2.rectangle(frame, (bbox[0], bbox[1]), 
                            (bbox[2], bbox[3]), (0, 255, 0), 2)
                
                # Extract embedding
                embedding = FaceRecognizer.extract_embedding(faces[0])
                
                # Check for duplicate face on first sample (skip if updating same user)
                if not duplicate_checked and len(embeddings) == 0:
                    is_duplicate, matched_user_id, similarity_score = self.check_duplicate_face(embedding)
                    
                    if is_duplicate:
                        # In update mode, allow if it's the same user
                        if update_mode and matched_user_id == user_id:
                            print("✓ Face check passed - same user detected (update mode)")
                            duplicate_checked = True
                        else:
                            cap.release()
                            cv2.destroyAllWindows()
                            print(f"\n⚠️  WARNING: This face is already enrolled!")
                            print(f"   Matched with existing user: {matched_user_id}")
                            print(f"   Similarity score: {similarity_score:.3f}")
                            if update_mode:
                                print(f"   Cannot update: face belongs to different user ({matched_user_id})")
                            else:
                                print(f"\n   Enrollment cancelled to prevent duplicate registration.")
                            self.logger.warning(
                                f"Duplicate face detected during enrollment. "
                                f"Attempted user_id: {user_id}, Matched existing: {matched_user_id}"
                            )
                            return
                    else:
                        duplicate_checked = True
                        print("✓ Face check passed - not a duplicate")
                
                embeddings.append(embedding)
                self.logger.info(
                    f"Captured sample {len(embeddings)}/{ENROLLMENT_SAMPLE_COUNT}"
                )
                print(f"Captured sample {len(embeddings)}/{ENROLLMENT_SAMPLE_COUNT}")

            # Ensure frame is valid and display it
            if frame is not None and frame.size > 0:
                cv2.imshow("Enrollment", frame)
                # Use waitKey with a small delay to ensure window updates properly
                key = cv2.waitKey(30) & 0xFF
                if key == 27:  # ESC key
                    print("Enrollment cancelled by user")
                    break
                elif key == ord('g') or key == ord('G'):  # Generate QR code
                    if not qr_generated:
                        try:
                            qr_data, qr_path = self.qr_generator.generate(user_id)
                            qr_code_scanned = qr_data  # Use generated QR as scanned QR
                            qr_scan_complete = True
                            qr_generated = True
                            print(f"\n✓ QR code generated: {qr_path}")
                            print(f"  QR data: {qr_data}")
                        except Exception as e:
                            print(f"\n✗ Failed to generate QR code: {e}")
                            self.logger.error(f"QR generation failed: {e}")
            else:
                print("Warning: Invalid frame received")
                time.sleep(0.1)

        cap.release()
        cv2.destroyAllWindows()

        if len(embeddings) > 0:
            embeddings = np.array(embeddings)
            embedding_path = EMBEDDINGS_DIR / f"{user_id}.npy"
            np.save(embedding_path, embeddings)
            
            # Auto-generate QR code if none was scanned
            if not qr_code_scanned:
                try:
                    qr_data, qr_path = self.qr_generator.generate(user_id)
                    qr_code_scanned = qr_data
                    qr_generated = True
                    print(f"\n✓ QR code auto-generated: {qr_path}")
                    print(f"  QR data: {qr_data}")
                    self.logger.info(f"Auto-generated QR code for user: {user_id}")
                except Exception as e:
                    print(f"\n⚠️  Warning: Could not auto-generate QR code: {e}")
                    self.logger.warning(f"Failed to auto-generate QR code for {user_id}: {e}")
            
            # Save to database
            db_success = False
            try:
                # Debug: Log what we're about to save
                self.logger.info(f"Preparing to save enrollment - User: {user_id}, Name: {name}, Role: {role}, QR: {qr_code_scanned}, UpdateMode: {update_mode}")
                
                # Check if user exists, create if not
                existing_user = self.user_model.get_by_id(user_id)
                if not existing_user:
                    # Create new user with all data
                    try:
                        result = self.user_model.create(user_id, name, role, qr_code_scanned, 'active')
                        if result:
                            self.logger.info(f"Created new user record: {user_id} - Name: {name}, Role: {role}, QR: {qr_code_scanned}")
                            db_success = True
                        else:
                            raise Exception("Create returned False without exception")
                    except Exception as create_error:
                        # If create failed, it might be because user exists (race condition or file system user)
                        error_msg = str(create_error)
                        self.logger.warning(f"Create failed for {user_id}: {error_msg}")
                        
                        # Check if user exists now (might have been created by another process)
                        existing_user = self.user_model.get_by_id(user_id)
                        if existing_user:
                            self.logger.info(f"User {user_id} exists after failed create, switching to update mode")
                            # Will fall through to update logic below
                        else:
                            # Re-raise with full error details
                            raise Exception(f"Failed to create user record: {error_msg}") from create_error
                
                # If user exists (either found initially or after failed create), update
                if existing_user or (not db_success and self.user_model.get_by_id(user_id)):
                    # Re-check if we need to get existing_user
                    if not existing_user:
                        existing_user = self.user_model.get_by_id(user_id)
                    # User exists - update with new enrollment data
                    # For new enrollments (not update_mode), always update name, role, and QR
                    # For update_mode, only update provided fields
                    if update_mode:
                        # Update mode: only update provided fields
                        update_params = {}
                        if name is not None:
                            update_params['name'] = name
                        if role is not None:
                            update_params['role'] = role
                        if qr_code_scanned:
                            update_params['qr_code'] = qr_code_scanned
                        
                        if update_params:
                            result = self.user_model.update(user_id, **update_params)
                            if result:
                                self.logger.info(f"Updated user record: {user_id}")
                                db_success = True
                            else:
                                raise Exception("Failed to update user record in database")
                    else:
                        # New enrollment: always update name, role, and QR code (even if user exists)
                        # Ensure QR code is set (should be auto-generated if not scanned)
                        final_qr_code = qr_code_scanned if qr_code_scanned else None
                        result = self.user_model.update(user_id, name=name, role=role, qr_code=final_qr_code)
                        if result:
                            self.logger.info(f"Updated existing user record with new enrollment data: {user_id} - Name: {name}, Role: {role}, QR: {final_qr_code}")
                            db_success = True
                        else:
                            raise Exception("Failed to update user record in database")
                    
                    # In update mode, delete old face templates and create new ones
                    if update_mode:
                        old_templates = self.template_model.get_by_user_id(user_id)
                        for template in old_templates:
                            self.template_model.delete(template['id'])
                        self.logger.info(f"Removed old face templates for: {user_id}")
                
                # Create face template record (new or updated) - only if database save succeeded
                if db_success:
                    self.template_model.create(user_id, str(embedding_path))
                    action = "Updated" if update_mode else "Created"
                    self.logger.info(f"{action} face template record for: {user_id}")
                
            except Exception as e:
                error_msg = str(e)
                error_type = type(e).__name__
                self.logger.error(f"Database operation failed: {error_type}: {error_msg}")
                self.logger.error(f"Full error details: {repr(e)}")
                
                print(f"\n✗ Error: Failed to save to database")
                print(f"  Error Type: {error_type}")
                print(f"  Error Message: {error_msg}")
                
                # Check database schema/table structure for debugging
                try:
                    table_info = self.db_manager.execute_query("PRAGMA table_info(users)")
                    columns = [row['name'] for row in table_info]
                    self.logger.info(f"Users table columns: {columns}")
                    print(f"\n  Database table 'users' columns: {', '.join(columns)}")
                except Exception as schema_error:
                    self.logger.error(f"Could not check table structure: {schema_error}")
                    print(f"  Warning: Could not verify table structure: {schema_error}")
                
                # Only cleanup if we didn't successfully retry
                if not db_success:
                    # Remove embedding file if database save failed
                    try:
                        if embedding_path.exists():
                            embedding_path.unlink()
                            print(f"  - Removed embedding file: {embedding_path}")
                            self.logger.info(f"Removed embedding file due to database failure: {embedding_path}")
                        
                        # Also remove QR code if it was generated
                        if qr_generated:
                            qr_path = self.qr_generator.get_qr_path(user_id)
                            if qr_path.exists():
                                qr_path.unlink()
                                print(f"  - Removed QR code: {qr_path}")
                    except Exception as cleanup_error:
                        self.logger.warning(f"Failed to cleanup files: {cleanup_error}")
                    
                    print("\nEnrollment cancelled. Please try again.")
                    print("Check the logs for detailed error information.")
                    return False
            
            # Only show success message if database save was successful
            if db_success:
                action = "Updated" if update_mode else "Enrollment completed"
                self.logger.info(f"{action} for user: {user_id}")
                
                print(f"\n✓ {action}! Saved {len(embeddings)} face samples for user: {user_id}")
                if qr_code_scanned:
                    if qr_generated:
                        qr_path = self.qr_generator.get_qr_path(user_id)
                        print(f"✓ QR code generated and saved: {qr_path}")
                    else:
                        print(f"✓ QR code scanned and saved: {qr_code_scanned}")
                else:
                    print("⚠️  Warning: QR code could not be generated or scanned.")
                    print("  You can generate one later using option 5 from the main menu.")
        else:
            self.logger.warning(f"Enrollment failed - no samples collected for user: {user_id}")
            print("Enrollment failed - no samples were collected.")
    
    def remove_enrollment(self, user_id: str):
        """
        Remove user enrollment: delete embedding file, database records.
        Attendance records are preserved for audit purposes.
        """
        user_id = user_id.strip()
        
        # Check if user exists
        user = self.user_model.get_by_id(user_id)
        if not user:
            # Check if embedding file exists (for backward compatibility)
            embedding_file = EMBEDDINGS_DIR / f"{user_id}.npy"
            if not embedding_file.exists():
                print(f"User {user_id} not found.")
                self.logger.warning(f"Attempted to remove non-existent user: {user_id}")
                return False
            else:
                # File exists but no database record - just delete file
                try:
                    embedding_file.unlink()
                    print(f"Removed embedding file for user: {user_id}")
                    self.logger.info(f"Removed embedding file for user: {user_id}")
                    return True
                except Exception as e:
                    print(f"Error removing embedding file: {e}")
                    self.logger.error(f"Failed to remove embedding file for {user_id}: {e}")
                    return False
        
        # Get face templates to find embedding path
        templates = self.template_model.get_by_user_id(user_id)
        
        # Delete embedding file(s)
        deleted_files = 0
        for template in templates:
            embedding_path = Path(template['embedding_path'])
            if embedding_path.exists():
                try:
                    embedding_path.unlink()
                    deleted_files += 1
                    self.logger.info(f"Deleted embedding file: {embedding_path}")
                except Exception as e:
                    self.logger.warning(f"Could not delete embedding file {embedding_path}: {e}")
        
        # Also check for direct .npy file (backward compatibility)
        embedding_file = EMBEDDINGS_DIR / f"{user_id}.npy"
        if embedding_file.exists():
            try:
                embedding_file.unlink()
                deleted_files += 1
                self.logger.info(f"Deleted embedding file: {embedding_file}")
            except Exception as e:
                self.logger.warning(f"Could not delete embedding file {embedding_file}: {e}")
        
        # Delete user record (cascade will delete face_templates)
        if self.user_model.delete(user_id):
            print(f"✓ Successfully removed enrollment for user: {user_id}")
            if deleted_files > 0:
                print(f"  - Deleted {deleted_files} embedding file(s)")
            print(f"  - Removed database records")
            print(f"  - Note: Attendance records preserved for audit")
            self.logger.info(f"Removed enrollment for user: {user_id}")
            return True
        else:
            print(f"Error: Failed to remove user from database.")
            self.logger.error(f"Failed to remove user {user_id} from database")
            return False
    
    def list_enrolled_users(self):
        """
        List all enrolled users with their details.
        """
        users = []
        
        # Get users from database
        try:
            if self.db_manager.is_initialized():
                db_users = self.user_model.get_all()
                for user in db_users:
                    users.append({
                        'user_id': user['user_id'],
                        'name': user.get('name', 'N/A'),
                        'role': user.get('role', 'N/A'),
                        'status': user.get('status', 'active'),
                        'qr_code': user.get('qr_code', 'Not set'),
                        'created_at': user.get('created_at', 'N/A')
                    })
        except Exception as e:
            self.logger.warning(f"Could not load users from database: {e}")
        
        # Also check file system for users not in database
        for file in EMBEDDINGS_DIR.glob("*.npy"):
            user_id = file.stem
            # Check if already in list
            if not any(u['user_id'] == user_id for u in users):
                users.append({
                    'user_id': user_id,
                    'name': 'N/A',
                    'role': 'N/A',
                    'status': 'active',
                    'qr_code': 'Not set',
                    'created_at': 'N/A'
                })
        
        if not users:
            print("\nNo enrolled users found.")
            return users
        
        print(f"\n{'User ID':<15} {'Name':<20} {'Role':<15} {'Status':<10} {'QR Code':<10} {'Created':<20}")
        print("-" * 100)
        for user in users:
            qr_status = "Yes" if user.get('qr_code') and user.get('qr_code') != 'Not set' else "No"
            print(f"{user['user_id']:<15} {user.get('name', 'N/A'):<20} {user.get('role', 'N/A'):<15} {user.get('status', 'N/A'):<10} {qr_status:<10} {str(user.get('created_at', 'N/A')):<20}")
        print("-" * 100)
        
        return users
    
    def generate_qr_for_user(self, user_id: str):
        """
        Generate QR code for an existing user.
        
        Args:
            user_id: The user ID to generate QR code for
        """
        # Normalize user_id (strip whitespace)
        original_user_id = user_id.strip()
        user_id = original_user_id
        
        # Check if user exists with exact match first (database)
        user = self.user_model.get_by_id(user_id)
        
        # Also check file system if not found in database
        if not user:
            embedding_file = EMBEDDINGS_DIR / f"{user_id}.npy"
            if embedding_file.exists():
                # User exists in file system but not in database - create database record
                print(f"Note: User '{user_id}' found in file system but not in database.")
                print("Creating database record...")
                try:
                    self.user_model.create(user_id, status='active')
                    user = self.user_model.get_by_id(user_id)
                    self.logger.info(f"Created database record for existing user: {user_id}")
                except Exception as e:
                    self.logger.warning(f"Could not create database record: {e}")
        
        if not user:
            # Try to find user with different formatting (e.g., "0003" vs "3")
            # First, try as integer if it's numeric
            try:
                user_num = int(user_id)
                # Try different formats: preserve original length, then try common formats
                # Get the original length to preserve formatting
                original_length = len(user_id)
                
                formats_to_try = [
                    f"{user_num:0{original_length}d}",  # Preserve original format length (e.g., "0003" stays "0003")
                    f"{user_num:04d}",  # 4-digit format (most common)
                    str(user_num),  # No leading zeros (e.g., "3")
                    f"{user_num:05d}",  # 5-digit format (less common)
                ]
                
                # Remove duplicates while preserving order
                seen = {user_id}  # Start with original to avoid duplicates
                unique_formats = []
                for fmt_id in formats_to_try:
                    if fmt_id not in seen:
                        seen.add(fmt_id)
                        unique_formats.append(fmt_id)
                
                for fmt_id in unique_formats:
                    test_user = self.user_model.get_by_id(fmt_id)
                    if test_user:
                        if fmt_id != original_user_id:
                            print(f"Note: Found user with ID '{fmt_id}' (you entered '{original_user_id}')")
                        user_id = fmt_id
                        user = test_user
                        break
            except ValueError:
                pass  # Not a numeric ID, skip format variations
            
            if not user:
                print(f"Error: User '{original_user_id}' not found.")
                # Show available user IDs to help user (from both database and file system)
                try:
                    # Get users from database
                    db_users = self.user_model.get_all()
                    user_ids_from_db = {u['user_id'] for u in db_users}
                    
                    # Get users from file system
                    file_user_ids = set()
                    for file in EMBEDDINGS_DIR.glob("*.npy"):
                        file_user_ids.add(file.stem)
                    
                    # Combine both sources
                    all_user_ids = sorted(user_ids_from_db | file_user_ids)
                    
                    if all_user_ids:
                        print("\nAvailable User IDs:")
                        for uid in all_user_ids[:10]:  # Show first 10
                            source = "(DB)" if uid in user_ids_from_db else "(File)"
                            print(f"  - '{uid}' {source}")
                        if len(all_user_ids) > 10:
                            print(f"  ... and {len(all_user_ids) - 10} more")
                    else:
                        print("No users found.")
                except Exception as e:
                    self.logger.warning(f"Could not list available users: {e}")
                print("\nTip: Use option 7 to list all enrolled users and their exact IDs.")
                return False
        
        try:
            # Generate QR code
            qr_data, qr_path = self.qr_generator.generate(user_id)
            
            # Update user record with QR code data
            self.user_model.update(user_id, qr_code=qr_data)
            
            print(f"\n✓ QR code generated successfully for user: {user_id}")
            print(f"  QR data: {qr_data}")
            print(f"  Image saved: {qr_path}")
            self.logger.info(f"QR code generated for user: {user_id}")
            return True
            
        except Exception as e:
            print(f"\n✗ Failed to generate QR code: {e}")
            self.logger.error(f"QR generation failed for {user_id}: {e}")
            return False
    
    def generate_qr_for_all_users(self):
        """
        Generate QR codes for all users who don't have one yet.
        """
        users = self.user_model.get_all()
        if not users:
            print("No users found.")
            return
        
        generated_count = 0
        skipped_count = 0
        
        for user in users:
            user_id = user['user_id']
            if user.get('qr_code'):
                print(f"Skipping {user_id} - already has QR code")
                skipped_count += 1
                continue
            
            if self.generate_qr_for_user(user_id):
                generated_count += 1
        
        print(f"\n✓ Generated {generated_count} QR code(s)")
        if skipped_count > 0:
            print(f"  Skipped {skipped_count} user(s) (already have QR codes)")


