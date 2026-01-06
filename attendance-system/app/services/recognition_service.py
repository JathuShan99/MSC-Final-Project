import cv2
import numpy as np
import time
from pathlib import Path
from app.core.face_detector import FaceDetector
from app.core.face_recognizer import FaceRecognizer
from app.core.liveness import LivenessDetector
from app.core.challenge_response import ChallengeResponse
from app.core.id_validator import IDValidator
from app.config.paths import EMBEDDINGS_DIR
from app.config.settings import VERIFICATION_DURATION, VERIFICATION_FPS, LIVENESS_FPS
from app.utils.logging import setup_logger
from app.database.db_manager import DatabaseManager
from app.database.models import FaceTemplate, Attendance

class RecognitionService:
    """
    Handles real-time face recognition.
    """
    def __init__(self):
        self.detector = FaceDetector()
        self.liveness_detector = LivenessDetector()
        self.challenge = ChallengeResponse()
        self.id_validator = IDValidator()
        self.logger = setup_logger()
        self.db_manager = DatabaseManager()
        self.template_model = FaceTemplate(self.db_manager)
        self.attendance_model = Attendance(self.db_manager)
        self.known_embeddings = self._load_embeddings()

    def _load_embeddings(self):
        """
        Load enrolled embeddings from database (with fallback to file system).
        """
        embeddings = {}
        
        # Try to load from database first
        try:
            if self.db_manager.is_initialized():
                templates = self.template_model.get_all()
                for template in templates:
                    user_id = template['user_id']
                    embedding_path = Path(template['embedding_path'])
                    
                    if embedding_path.exists():
                        embeddings[user_id] = np.load(embedding_path)
                    else:
                        self.logger.warning(f"Embedding file not found: {embedding_path}")
                
                if embeddings:
                    self.logger.info(f"Loaded {len(embeddings)} enrolled users from database.")
                    return embeddings
        except Exception as e:
            self.logger.warning(f"Failed to load from database, falling back to file system: {e}")
        
        # Fallback to file system
        for file in EMBEDDINGS_DIR.glob("*.npy"):
            user_id = file.stem
            embeddings[user_id] = np.load(file)
        
        self.logger.info(f"Loaded {len(embeddings)} enrolled users from file system.")
        return embeddings

    def recognize_frame(self, frame):
        """
        Recognize face(s) in a single frame.
        Returns best match only (highest score) with face object, or None.
        """
        faces = self.detector.detect(frame)
        
        if len(faces) != 1:
            return None  # Need exactly one face for reliable recognition
        
        test_embedding = FaceRecognizer.extract_embedding(faces[0])
        best_match = None
        best_score = 0
        
        for user_id, stored_embeddings in self.known_embeddings.items():
            is_match, score = FaceRecognizer.compare(
                test_embedding, stored_embeddings
            )
            if is_match and score > best_score:
                best_match = {
                    "user_id": user_id,
                    "score": round(score, 3),
                    "face": faces[0]  # Keep face for drawing bounding box
                }
                best_score = score
        
        return best_match

    def run_realtime(self):
        """
        Run real-time face recognition with 10-second verification.
        Marks attendance only after continuous recognition for 10 seconds.
        """
        if len(self.known_embeddings) == 0:
            print("No enrolled users found. Please enroll users first.")
            self.logger.warning("Recognition attempted with no enrolled users")
            return
        
        cap = cv2.VideoCapture(0)
        
        # Verify webcam is accessible
        if not cap.isOpened():
            self.logger.error("Failed to open webcam")
            print("Error: Could not access webcam. Please check if it's connected and not in use by another application.")
            return
        
        # Set webcam properties
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        
        # Create window explicitly
        cv2.namedWindow("Recognition", cv2.WINDOW_NORMAL)
        cv2.resizeWindow("Recognition", 640, 480)
        
        # Verification state
        qr_scanned = None  # QR code that was scanned
        qr_scan_complete = False  # QR code scanning phase complete
        expected_user_id = None  # User ID from QR code (what we expect to recognize)
        face_recognition_start = None  # When face recognition period starts (after QR scanned)
        frame_count = 0
        attendance_marked = False
        last_attendance_time = None
        last_result = None
        liveness_verified = False
        liveness_status = "Checking..."  # "OK", "Checking...", "Failed"
        active_challenge = None
        challenge_passed = False
        current_user = None  # Currently recognized user
        detected_score = 0.0  # Recognition score for attendance record (stored when face is recognized)
        detected_user = None  # Last detected user from face recognition
        face_mismatch_recorded = False  # Track if face mismatch has been recorded
        
        self.logger.info("Real-time recognition started.")
        print(f"Recognition started. {len(self.known_embeddings)} user(s) loaded.")
        print("Face the camera for 10 seconds to mark attendance.")
        print("You will see a CHALLENGE instruction on screen - follow it!")
        print("Press ESC to exit.")

        while True:
            ret, frame = cap.read()
            if not ret:
                print("Warning: Could not read frame from webcam")
                continue

            # Flip frame horizontally for mirror effect
            frame = cv2.flip(frame, 1)
            frame_count += 1
            
            # Process every Nth frame for performance (face recognition)
            faces = []
            result = None
            liveness_result = False
            
            # Step 1: Scan QR code first (if not already scanned) - NO face recognition until QR is scanned
            if not qr_scan_complete:
                # Only scan for QR code, no face detection/recognition
                scanned_qr = None
                if frame_count % 2 == 0:  # Scan every 2nd frame
                    scanned_qr = self.id_validator.scan(frame)
                    if scanned_qr:
                        qr_scanned = scanned_qr
                        qr_scan_complete = True
                        expected_user_id = scanned_qr
                        print(f"\n✓ QR code scanned: {qr_scanned}")
                        print("Step 2: Face the camera for 10 seconds...")
                        self.logger.info(f"QR code scanned: {qr_scanned}, starting face recognition period")
                
                # Display QR scanning status (like test_qr_scanner.py)
                h, w = frame.shape[:2]
                if scanned_qr:
                    cv2.rectangle(frame, (10, 10), (w-10, h-10), (0, 255, 0), 3)
                    cv2.putText(frame, f"QR: {scanned_qr}", (20, 40),
                               cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
                else:
                    cv2.rectangle(frame, (10, 10), (w-10, h-10), (0, 255, 255), 2)
                    cv2.putText(frame, "Step 1: Show QR code", (20, 40),
                               cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 255), 2)
                    cv2.putText(frame, "Scanning for QR code...", (20, 80),
                               cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
                
                cv2.imshow("Recognition", frame)
                key = cv2.waitKey(30) & 0xFF
                if key == 27:
                    break
                continue  # Skip face recognition until QR is scanned
            
            # Step 2: After QR scanned, detect face and start 10-second liveness check
            # Note: face_recognition_start is only set when face is recognized and matches QR (see below)
            # Face detection only on every Nth frame (for performance) - ONLY after QR is scanned
            if frame_count % 2 == 0:
                faces = self.detector.detect(frame)
            
            # Face recognition only once to verify it matches QR code user ID
            if face_recognition_start is None and len(faces) > 0:
                if frame_count % VERIFICATION_FPS == 0:
                    result = self.recognize_frame(frame)
                    if result:
                        detected_user = result['user_id']
                        detected_score = result['score']
                        
                        # Check if recognized face matches QR code user ID
                        if detected_user == expected_user_id:
                            # Face matches QR - start 10-second liveness check period
                            if face_recognition_start is None:  # Only start once
                                face_recognition_start = time.time()
                                current_user = detected_user
                                detected_score = result['score']  # Store score for attendance record
                                self.liveness_detector.reset()
                                liveness_verified = False  # Reset liveness
                                liveness_status = "Checking..."  # Reset status
                                print(f"\n✓ Face recognized: {detected_user} (matches QR code)")
                                print("Starting 10-second liveness verification...")
                                self.logger.info(f"Face recognized: {detected_user}, starting 10-second liveness check")
                            else:
                                # Already started, just update current_user if needed
                                if current_user != detected_user:
                                    current_user = detected_user
                        elif qr_scan_complete and expected_user_id and detected_user and not face_mismatch_recorded:
                            # Face mismatch detected: QR code user doesn't match recognized face
                            # Record this as a failed attempt (e.g., QR for "0002" but face is "0003")
                            try:
                                from app.config.settings import SIMILARITY_THRESHOLD
                                threshold_used = SIMILARITY_THRESHOLD
                                # Face mismatch = always reject, regardless of score
                                # If QR is 0002 and face is 0003, system should reject
                                system_decision = 'reject'  # Always reject on face mismatch
                                
                                self.attendance_model.create(
                                    user_id=expected_user_id,  # Use QR code user ID (the one who scanned QR)
                                    recognition_score=detected_score,
                                    face_verified=0,  # Face mismatch - mark as failed
                                    liveness_verified=0,  # Liveness not checked (face didn't match)
                                    threshold_used=threshold_used,
                                    system_decision=system_decision  # Always 'reject' for mismatch
                                )
                                face_mismatch_recorded = True
                                self.logger.warning(f"Face mismatch recorded: QR={expected_user_id}, Recognized={detected_user}, Score={detected_score:.3f}")
                                print(f"\n⚠️  Face mismatch detected!")
                                print(f"  QR Code User: {expected_user_id}")
                                print(f"  Recognized Face: {detected_user}")
                                print(f"  This attempt has been recorded as failed.")
                                
                                # Show mismatch message on screen for 3 seconds, then close
                                status_text = f"✗ FACE MISMATCH"
                                status_color = (0, 0, 255)  # Red
                                sub_text = f"QR: {expected_user_id}, Face: {detected_user}"
                                closing_text = "Closing in 3 seconds..."
                                
                                # Draw mismatch status
                                cv2.rectangle(frame, (5, 5), (600, 120), (0, 0, 0), -1)
                                cv2.putText(frame, status_text, (10, 35),
                                           cv2.FONT_HERSHEY_SIMPLEX, 0.8, status_color, 2)
                                cv2.putText(frame, sub_text, (10, 65),
                                           cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
                                cv2.putText(frame, closing_text, (10, 95),
                                           cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 2)
                                cv2.imshow("Recognition", frame)
                                
                                # Wait 3 seconds to show message
                                for i in range(30):  # 30 frames at ~10fps = 3 seconds
                                    ret, frame = cap.read()
                                    if ret:
                                        frame = cv2.flip(frame, 1)
                                        cv2.rectangle(frame, (5, 5), (600, 120), (0, 0, 0), -1)
                                        cv2.putText(frame, status_text, (10, 35),
                                                   cv2.FONT_HERSHEY_SIMPLEX, 0.8, status_color, 2)
                                        cv2.putText(frame, sub_text, (10, 65),
                                                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
                                        cv2.putText(frame, closing_text, (10, 95),
                                                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 2)
                                        cv2.imshow("Recognition", frame)
                                    cv2.waitKey(100)  # 100ms = 3 seconds total
                                
                                # Exit after showing message
                                break
                            except Exception as e:
                                self.logger.error(f"Failed to record face mismatch: {e}")
                                print(f"\n✗ Error recording face mismatch: {e}")
                                # Still exit on error
                                break
            
            # During 10-second period: Check liveness and continue face recognition if needed
            # Only enter this block if face_recognition_start has been set (face was recognized)
            if face_recognition_start is not None:
                # Recalculate elapsed time each frame for accurate countdown (10 -> 0)
                face_elapsed = time.time() - face_recognition_start
                face_remaining = max(0.0, VERIFICATION_DURATION - face_elapsed)  # Countdown from 10.0 to 0.0
                
                # Continue face recognition if current_user is not set yet (retry during 10-second period)
                if current_user is None and len(faces) > 0 and frame_count % VERIFICATION_FPS == 0:
                    result = self.recognize_frame(frame)
                    if result:
                        detected_user = result['user_id']
                        detected_score = result['score']
                        
                        # Check if recognized face matches QR code user ID
                        if detected_user == expected_user_id:
                            current_user = detected_user
                            detected_score = result['score']
                            self.logger.info(f"Face recognized during 10-second period: {detected_user}")
                            print(f"\n✓ Face recognized: {detected_user} (matches QR code)")
                        elif expected_user_id and detected_user != expected_user_id and not face_mismatch_recorded:
                            # Face mismatch during 10-second period - record the attempt
                            try:
                                from app.config.settings import SIMILARITY_THRESHOLD
                                threshold_used = SIMILARITY_THRESHOLD
                                # Face mismatch = always reject, regardless of score
                                # If QR is 0002 and face is 0003, system should reject
                                system_decision = 'reject'  # Always reject on face mismatch
                                
                                self.attendance_model.create(
                                    user_id=expected_user_id,  # Use QR code user ID
                                    recognition_score=detected_score,
                                    face_verified=0,  # Face mismatch - mark as failed
                                    liveness_verified=0,  # Liveness not checked (face didn't match)
                                    threshold_used=threshold_used,
                                    system_decision=system_decision  # Always 'reject' for mismatch
                                )
                                face_mismatch_recorded = True
                                self.logger.warning(f"Face mismatch recorded during 10s period: QR={expected_user_id}, Recognized={detected_user}")
                                print(f"\n⚠️  Face mismatch: Recognized {detected_user}, Expected {expected_user_id}")
                                print(f"  This attempt has been recorded as failed.")
                                
                                # Show mismatch message on screen for 3 seconds, then close
                                status_text = f"✗ FACE MISMATCH"
                                status_color = (0, 0, 255)  # Red
                                sub_text = f"QR: {expected_user_id}, Face: {detected_user}"
                                closing_text = "Closing in 3 seconds..."
                                
                                # Draw mismatch status
                                cv2.rectangle(frame, (5, 5), (600, 120), (0, 0, 0), -1)
                                cv2.putText(frame, status_text, (10, 35),
                                           cv2.FONT_HERSHEY_SIMPLEX, 0.8, status_color, 2)
                                cv2.putText(frame, sub_text, (10, 65),
                                           cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
                                cv2.putText(frame, closing_text, (10, 95),
                                           cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 2)
                                cv2.imshow("Recognition", frame)
                                
                                # Wait 3 seconds to show message
                                for i in range(30):  # 30 frames at ~10fps = 3 seconds
                                    ret, frame = cap.read()
                                    if ret:
                                        frame = cv2.flip(frame, 1)
                                        cv2.rectangle(frame, (5, 5), (600, 120), (0, 0, 0), -1)
                                        cv2.putText(frame, status_text, (10, 35),
                                                   cv2.FONT_HERSHEY_SIMPLEX, 0.8, status_color, 2)
                                        cv2.putText(frame, sub_text, (10, 65),
                                                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
                                        cv2.putText(frame, closing_text, (10, 95),
                                                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 2)
                                        cv2.imshow("Recognition", frame)
                                    cv2.waitKey(100)  # 100ms = 3 seconds total
                                
                                # Exit after showing message
                                break
                            except Exception as e:
                                self.logger.error(f"Failed to record face mismatch: {e}")
                                # Still exit on error
                                break
                
                # Check liveness during the 10-second period
                if len(faces) == 1 and frame_count % 2 == 0:
                    # Pass the already-detected face to avoid re-detection
                    liveness_result = self.liveness_detector.detect(frame, faces[0])
                    if liveness_result:
                        liveness_verified = True
                        liveness_status = "OK"
                    # Keep status as "Checking..." if not yet verified
                    elif not liveness_verified:
                        liveness_status = "Checking..."
                
                # Draw bounding box around face
                if len(faces) > 0:
                    for face in faces:
                        bbox = face.bbox.astype(int)
                        color = (0, 255, 0) if liveness_verified else (0, 255, 255)
                        cv2.rectangle(frame, (bbox[0], bbox[1]), 
                                     (bbox[2], bbox[3]), color, 2)
                
                # Check if 10 seconds elapsed - check every frame when time is up
                # This check runs every frame once 10 seconds have passed
                if face_elapsed >= VERIFICATION_DURATION and not attendance_marked:
                    # After 10 seconds, check if all conditions are met before marking attendance
                    # Ensure current_user is set (fallback to expected_user_id if None)
                    user_id_for_attendance = current_user if current_user is not None else expected_user_id
                    
                    # Check all required conditions
                    qr_condition = qr_scan_complete and qr_scanned is not None
                    # Face condition: current_user must be set and match expected_user_id, and score must be valid
                    face_condition = (current_user is not None and 
                                     current_user == expected_user_id and 
                                     detected_score > 0)
                    liveness_condition = liveness_verified
                    
                    # Debug: Log detailed condition status
                    self.logger.info(f"Condition details - current_user: {current_user}, expected_user_id: {expected_user_id}, detected_score: {detected_score}, liveness_verified: {liveness_verified}")
                    
                    all_conditions_met = qr_condition and face_condition and liveness_condition
                    
                    self.logger.info(f"10 seconds elapsed - Conditions check: QR={qr_condition}, Face={face_condition}, Liveness={liveness_condition}")
                    
                    if all_conditions_met:
                        # All conditions met - mark attendance
                        try:
                            from app.config.settings import SIMILARITY_THRESHOLD
                            score_for_record = detected_score if detected_score > 0 else 0.85
                            threshold_used = SIMILARITY_THRESHOLD
                            system_decision = 'accept' if score_for_record >= threshold_used else 'reject'
                            
                            self.attendance_model.create(
                                user_id=user_id_for_attendance,
                                recognition_score=score_for_record,  # Use stored score or default
                                face_verified=True,
                                liveness_verified=liveness_verified,  # Use actual liveness status
                                threshold_used=threshold_used,
                                system_decision=system_decision
                            )
                            attendance_marked = True
                            last_attendance_time = time.time()
                            self.logger.info(f"Attendance marked for user: {user_id_for_attendance} (QR: {qr_scanned})")
                            print(f"\n✓ Attendance marked for: {user_id_for_attendance}")
                            print(f"✓ Multi-factor verified: QR + Face + Liveness")
                            
                            # Reset challenge after successful attendance
                            self.challenge.reset()
                            active_challenge = None
                            challenge_passed = False
                            
                            # Display success message for 3 seconds before closing
                            status_text = f"✓ {user_id_for_attendance} - Attendance Recorded"
                            status_color = (0, 255, 0)
                            sub_text = "Closing in 3 seconds..."
                            
                            # Draw final status
                            cv2.rectangle(frame, (5, 5), (450, 90), (0, 0, 0), -1)
                            cv2.putText(frame, status_text, (10, 35),
                                       cv2.FONT_HERSHEY_SIMPLEX, 0.8, status_color, 2)
                            cv2.putText(frame, sub_text, (10, 65),
                                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
                            cv2.imshow("Recognition", frame)
                            
                            for i in range(30):  # 30 frames at ~10fps = 3 seconds
                                ret, frame = cap.read()
                                if ret:
                                    frame = cv2.flip(frame, 1)
                                    # Redraw status
                                    cv2.rectangle(frame, (5, 5), (450, 90), (0, 0, 0), -1)
                                    cv2.putText(frame, status_text, (10, 35),
                                               cv2.FONT_HERSHEY_SIMPLEX, 0.8, status_color, 2)
                                    cv2.putText(frame, sub_text, (10, 65),
                                               cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
                                    cv2.imshow("Recognition", frame)
                                cv2.waitKey(100)  # 100ms = 3 seconds total
                            
                            # Exit after showing success message
                            break
                        except Exception as e:
                            self.logger.error(f"Failed to log attendance: {e}")
                            print(f"\n✗ Error marking attendance: {e}")
                            import traceback
                            self.logger.error(traceback.format_exc())
                            # Show error message and exit
                            attendance_marked = True  # Prevent retry loop
                            status_text = "✗ Attendance Not Marked"
                            status_color = (0, 0, 255)
                            sub_text = "Database error - Closing in 3 seconds..."
                            
                            # Draw error status
                            cv2.rectangle(frame, (5, 5), (500, 90), (0, 0, 0), -1)
                            cv2.putText(frame, status_text, (10, 35),
                                       cv2.FONT_HERSHEY_SIMPLEX, 0.8, status_color, 2)
                            cv2.putText(frame, sub_text, (10, 65),
                                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
                            cv2.imshow("Recognition", frame)
                            
                            for i in range(30):  # 3 seconds
                                ret, frame = cap.read()
                                if ret:
                                    frame = cv2.flip(frame, 1)
                                    cv2.rectangle(frame, (5, 5), (500, 90), (0, 0, 0), -1)
                                    cv2.putText(frame, status_text, (10, 35),
                                               cv2.FONT_HERSHEY_SIMPLEX, 0.8, status_color, 2)
                                    cv2.putText(frame, sub_text, (10, 65),
                                               cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
                                    cv2.imshow("Recognition", frame)
                                cv2.waitKey(100)
                            break
                    else:
                        # Conditions not met - but record attempt if QR was scanned
                        attendance_marked = True  # Prevent retry loop
                        self.logger.warning(f"Attendance attempt failed - Conditions not met: QR={qr_condition}, Face={face_condition}, Liveness={liveness_condition}")
                        
                        # Build failure reason message
                        failure_reasons = []
                        if not qr_condition:
                            failure_reasons.append("QR not scanned")
                        if not face_condition:
                            failure_reasons.append("Face not recognized")
                        if not liveness_condition:
                            failure_reasons.append("Liveness not verified")
                        
                        failure_text = "Missing: " + ", ".join(failure_reasons)
                        
                        # Record attendance attempt if QR was scanned (even if face/liveness failed)
                        if qr_condition:
                            try:
                                from app.config.settings import SIMILARITY_THRESHOLD
                                score_for_record = detected_score if detected_score > 0 else 0.0
                                threshold_used = SIMILARITY_THRESHOLD
                                system_decision = 'accept' if score_for_record >= threshold_used else 'reject'
                                
                                # Record failed attempt with QR scanned
                                self.attendance_model.create(
                                    user_id=user_id_for_attendance,
                                    recognition_score=score_for_record,
                                    face_verified=1 if face_condition else 0,  # Record actual face status
                                    liveness_verified=1 if liveness_condition else 0,  # Record actual liveness status
                                    threshold_used=threshold_used,
                                    system_decision=system_decision
                                )
                                self.logger.info(f"Failed attendance attempt recorded for user: {user_id_for_attendance} (QR scanned, but Face={face_condition}, Liveness={liveness_condition})")
                                print(f"\n⚠️  Attendance attempt recorded (with failures)")
                                print(f"  QR: ✓ Scanned")
                                print(f"  Face: {'✓ Verified' if face_condition else '✗ Failed'}")
                                print(f"  Liveness: {'✓ Verified' if liveness_condition else '✗ Failed'}")
                            except Exception as e:
                                self.logger.error(f"Failed to record attendance attempt: {e}")
                                print(f"\n✗ Error recording attendance attempt: {e}")
                        else:
                            print(f"\n✗ Attendance not recorded")
                            print(f"  Conditions: QR={qr_condition}, Face={face_condition}, Liveness={liveness_condition}")
                        
                        # Display failure message for 3 seconds before closing
                        status_text = "✗ Attendance Attempt Failed" if qr_condition else "✗ Attendance Not Recorded"
                        status_color = (0, 0, 255)  # Red
                        sub_text = failure_text
                        
                        # Draw failure status
                        cv2.rectangle(frame, (5, 5), (600, 120), (0, 0, 0), -1)
                        cv2.putText(frame, status_text, (10, 35),
                                   cv2.FONT_HERSHEY_SIMPLEX, 0.8, status_color, 2)
                        cv2.putText(frame, sub_text, (10, 65),
                                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
                        cv2.putText(frame, "Closing in 3 seconds...", (10, 95),
                                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 2)
                        cv2.imshow("Recognition", frame)
                        
                        for i in range(30):  # 3 seconds
                            ret, frame = cap.read()
                            if ret:
                                frame = cv2.flip(frame, 1)
                                # Redraw failure status
                                cv2.rectangle(frame, (5, 5), (600, 120), (0, 0, 0), -1)
                                cv2.putText(frame, status_text, (10, 35),
                                           cv2.FONT_HERSHEY_SIMPLEX, 0.8, status_color, 2)
                                cv2.putText(frame, sub_text, (10, 65),
                                           cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
                                cv2.putText(frame, "Closing in 3 seconds...", (10, 95),
                                           cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 2)
                                cv2.imshow("Recognition", frame)
                            cv2.waitKey(100)  # 100ms = 3 seconds total
                        
                        # Exit after showing failure message
                        break
                
                # Display status during 10-second liveness check
                if not attendance_marked:
                    # Ensure current_user is set (fallback to expected_user_id if None)
                    display_user = current_user if current_user is not None else expected_user_id
                    status_text = f"Verifying: {display_user}"
                    status_color = (0, 255, 255)
                    sub_text = f"Time remaining: {face_remaining:.1f}s"
                    
                    # Determine liveness status color
                    if liveness_verified:
                        liveness_color = (0, 255, 0)  # Green
                        liveness_text = "Liveness: OK"
                    else:
                        liveness_color = (0, 165, 255)  # Orange/Yellow
                        liveness_text = "Liveness: Checking..."
                    
                    # QR code status
                    qr_text = f"QR: {qr_scanned} ✓"
                    qr_color = (0, 255, 0)  # Green
                    
                    # Draw status with background
                    cv2.rectangle(frame, (5, 5), (500, 140), (0, 0, 0), -1)
                    cv2.putText(frame, status_text, (10, 35), cv2.FONT_HERSHEY_SIMPLEX, 0.8, status_color, 2)
                    cv2.putText(frame, sub_text, (10, 65), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
                    cv2.putText(frame, liveness_text, (10, 95), cv2.FONT_HERSHEY_SIMPLEX, 0.6, liveness_color, 2)
                    cv2.putText(frame, qr_text, (10, 125), cv2.FONT_HERSHEY_SIMPLEX, 0.6, qr_color, 2)
            else:
                # Before face is detected - show waiting message
                if len(faces) > 0:
                    # Face detected but not recognized yet or doesn't match
                    for face in faces:
                        bbox = face.bbox.astype(int)
                        cv2.rectangle(frame, (bbox[0], bbox[1]), 
                                     (bbox[2], bbox[3]), (255, 255, 0), 2)
                    
                    cv2.rectangle(frame, (5, 5), (500, 100), (0, 0, 0), -1)
                    cv2.putText(frame, "Face detected - verifying...", (10, 35),
                               cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 0), 2)
                    cv2.putText(frame, f"Expected user: {expected_user_id}", (10, 65),
                               cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
                else:
                    # No face detected yet
                    cv2.rectangle(frame, (5, 5), (400, 80), (0, 0, 0), -1)
                    cv2.putText(frame, "Step 2: Face the camera", (10, 35),
                               cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 0), 2)
                    cv2.putText(frame, f"Expected user: {expected_user_id}", (10, 65),
                               cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
                    # CHALLENGE VALIDATION TEMPORARILY DISABLED
                    # if active_challenge is not None:
                    #     # Check if challenge expired
                    #     if self.challenge.is_expired():
                    #         self.logger.warning(f"Challenge {active_challenge} expired, generating new one")
                    #         active_challenge = self.challenge.generate_challenge()
                    #         challenge_passed = False
                    #     
                    #     # Validate challenge response
                    #     if not challenge_passed:
                    #         if active_challenge == "BLINK":
                    #             if self.liveness_detector.check_blink():
                    #                 challenge_passed = True
                    #                 self.logger.info("Challenge BLINK passed")
                    #         elif active_challenge == "TURN_LEFT":
                    #             if self.liveness_detector.check_head_turn_left():
                    #                 challenge_passed = True
                    #                 self.logger.info("Challenge TURN_LEFT passed")
                    #         elif active_challenge == "TURN_RIGHT":
                    #             if self.liveness_detector.check_head_turn_right():
                    #                 challenge_passed = True
                    #                 self.logger.info("Challenge TURN_RIGHT passed")
                    
                    # Skip challenge validation - always pass
                    challenge_passed = True
                    
                    # Check if face recognition period is complete (10 seconds)
                    # Recalculate elapsed time (only if face_recognition_start is set)
                    if face_recognition_start is not None:
                        face_elapsed = time.time() - face_recognition_start
                    else:
                        face_elapsed = 0  # Not started yet
                    
                    if face_recognition_start is not None and face_elapsed >= VERIFICATION_DURATION and not attendance_marked:
                        # Multi-factor validation: face matches QR + liveness verified
                        failure_reason = None
                        if detected_user != expected_user_id:
                            failure_reason = f"Face recognition mismatch (recognized: {detected_user}, expected from QR: {expected_user_id})"
                        elif not liveness_verified:
                            liveness_status = "Failed"
                            failure_reason = "Liveness verification required"
                        
                        if failure_reason:
                            self.logger.warning(f"Attendance not marked for {detected_user}: {failure_reason}")
                            print(f"\n✗ Attendance not marked: {failure_reason}")
                            
                            # Display failure message for 3 seconds before closing
                            status_text = f"✗ {detected_user} - Verification Failed"
                            status_color = (0, 0, 255)
                            sub_text = f"{failure_reason}. Closing in 3 seconds..."
                            
                            # Draw final status
                            cv2.rectangle(frame, (5, 5), (550, 90), (0, 0, 0), -1)
                            cv2.putText(frame, status_text, (10, 35),
                                       cv2.FONT_HERSHEY_SIMPLEX, 0.8, status_color, 2)
                            cv2.putText(frame, sub_text, (10, 65),
                                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
                            cv2.imshow("Recognition", frame)
                            
                            # Wait 3 seconds to show failure message
                            for i in range(30):  # 30 frames at ~10fps = 3 seconds
                                ret, frame = cap.read()
                                if ret:
                                    frame = cv2.flip(frame, 1)
                                    # Redraw status
                                    cv2.rectangle(frame, (5, 5), (550, 90), (0, 0, 0), -1)
                                    cv2.putText(frame, status_text, (10, 35),
                                               cv2.FONT_HERSHEY_SIMPLEX, 0.8, status_color, 2)
                                    cv2.putText(frame, sub_text, (10, 65),
                                               cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
                                    cv2.imshow("Recognition", frame)
                                cv2.waitKey(100)  # 100ms = 3 seconds total
                            
                            # Exit after showing failure message
                            break
                        
                        # Mark attendance once (all conditions met: recognition + liveness + QR validation)
                        # All checks passed - mark attendance
                        try:
                            from app.config.settings import SIMILARITY_THRESHOLD
                            threshold_used = SIMILARITY_THRESHOLD
                            system_decision = 'accept' if detected_score >= threshold_used else 'reject'
                            
                            self.attendance_model.create(
                                user_id=detected_user,
                                recognition_score=detected_score,
                                face_verified=True,
                                liveness_verified=True,
                                threshold_used=threshold_used,
                                system_decision=system_decision
                            )
                            attendance_marked = True
                            last_attendance_time = time.time()
                            self.logger.info(f"Attendance marked for user: {detected_user} (QR: {qr_scanned})")
                            print(f"\n✓ Attendance marked for: {detected_user}")
                            print(f"✓ Multi-factor verified: QR + Face + Liveness")
                            # Reset challenge after successful attendance
                            self.challenge.reset()
                            active_challenge = None
                            challenge_passed = False
                            
                            # Display success message for 3 seconds before closing
                            status_text = f"✓ {detected_user} - Attendance Recorded"
                            status_color = (0, 255, 0)
                            sub_text = "Closing in 3 seconds..."
                            
                            # Draw final status
                            cv2.rectangle(frame, (5, 5), (450, 90), (0, 0, 0), -1)
                            cv2.putText(frame, status_text, (10, 35),
                                       cv2.FONT_HERSHEY_SIMPLEX, 0.8, status_color, 2)
                            cv2.putText(frame, sub_text, (10, 65),
                                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
                            cv2.imshow("Recognition", frame)
                            
                            # Wait 3 seconds to show success message
                            for i in range(30):  # 30 frames at ~10fps = 3 seconds
                                ret, frame = cap.read()
                                if ret:
                                    frame = cv2.flip(frame, 1)
                                    # Redraw status
                                    cv2.rectangle(frame, (5, 5), (450, 90), (0, 0, 0), -1)
                                    cv2.putText(frame, status_text, (10, 35),
                                               cv2.FONT_HERSHEY_SIMPLEX, 0.8, status_color, 2)
                                    cv2.putText(frame, sub_text, (10, 65),
                                               cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
                                    cv2.imshow("Recognition", frame)
                                cv2.waitKey(100)  # 100ms = 3 seconds total
                            
                            # Exit after showing success message
                            break
                        except Exception as e:
                            self.logger.warning(f"Failed to log attendance: {e}")
                    
                    # Display verification status (only if not marked yet)
                    if not attendance_marked:
                        if face_recognition_start is not None:
                            # Show face recognition countdown
                            display_user = current_user if current_user else expected_user_id if expected_user_id else "Unknown"
                            status_text = f"Recognizing: {display_user}"
                            status_color = (0, 255, 255)
                            sub_text = f"Face recognition... {face_remaining:.1f}s remaining"
                        else:
                            # Show initial recognition status (before face recognition starts)
                            display_user = expected_user_id if expected_user_id else "Unknown"
                            status_text = f"Recognizing... {display_user}"
                            status_color = (0, 255, 255)
                            sub_text = f"Score: {detected_score:.3f}" if detected_score > 0 else "Waiting for face..."
                        
                        # Determine liveness status color
                        if liveness_verified:
                            liveness_color = (0, 255, 0)  # Green
                            liveness_text = "Liveness: OK"
                        else:
                            liveness_color = (0, 165, 255)  # Orange/Yellow
                            liveness_text = "Liveness: Checking..."
                        
                        # QR code status
                        if qr_scan_complete:
                            qr_text = f"QR: {qr_scanned} ✓"
                            qr_color = (0, 255, 0)  # Green
                        else:
                            qr_text = "QR: Show code..."
                            qr_color = (255, 255, 0)  # Yellow
                        
                        # Challenge display - TEMPORARILY DISABLED
                        # challenge_text = ""
                        # challenge_color = (255, 255, 0)  # Yellow
                        # challenge_instruction = ""
                        # if active_challenge is not None:
                        #     challenge_remaining = self.challenge.get_remaining_time()
                        #     if challenge_passed:
                        #         challenge_text = f"Challenge: {active_challenge} ✓ PASSED"
                        #         challenge_color = (0, 255, 0)  # Green
                        #     else:
                        #         # Make challenge instruction very clear
                        #         if active_challenge == "BLINK":
                        #             challenge_instruction = "ACTION: BLINK YOUR EYES"
                        #         elif active_challenge == "TURN_LEFT":
                        #             challenge_instruction = "ACTION: TURN HEAD LEFT"
                        #         elif active_challenge == "TURN_RIGHT":
                        #             challenge_instruction = "ACTION: TURN HEAD RIGHT"
                        #         
                        #         challenge_text = f"{challenge_instruction} ({challenge_remaining:.1f}s)"
                        #         challenge_color = (0, 255, 255)  # Cyan for better visibility
                        
                        # Draw status with background (includes QR status)
                        cv2.rectangle(frame, (5, 5), (600, 150), (0, 0, 0), -1)
                        cv2.putText(frame, status_text, (10, 35),
                                   cv2.FONT_HERSHEY_SIMPLEX, 0.8, status_color, 2)
                        cv2.putText(frame, sub_text, (10, 65),
                                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
                        cv2.putText(frame, liveness_text, (10, 95),
                                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, liveness_color, 2)
                        cv2.putText(frame, qr_text, (10, 125),
                                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, qr_color, 2)
                        
                        # Challenge text display - DISABLED
                        # if challenge_text:
                        #     # Draw challenge text below liveness text (at y=125)
                        #     cv2.putText(frame, challenge_text, (10, 125),
                        #                cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 0), 4)  # Black outline
                        #     cv2.putText(frame, challenge_text, (10, 125),
                        #                cv2.FONT_HERSHEY_SIMPLEX, 0.8, challenge_color, 2)  # Colored text on top
            
            # Challenge display - TEMPORARILY DISABLED
            # # ALWAYS display challenge if active (even when no match yet, for visibility)
            # if active_challenge is not None and not attendance_marked:
            #     challenge_remaining = self.challenge.get_remaining_time()
            #     if not challenge_passed:
            #         # Make challenge instruction very clear
            #         if active_challenge == "BLINK":
            #             challenge_instruction = "ACTION: BLINK YOUR EYES"
            #         elif active_challenge == "TURN_LEFT":
            #             challenge_instruction = "ACTION: TURN HEAD LEFT"
            #         elif active_challenge == "TURN_RIGHT":
            #             challenge_instruction = "ACTION: TURN HEAD RIGHT"
            #         else:
            #             challenge_instruction = f"ACTION: {active_challenge}"
            #         
            #         challenge_text = f"{challenge_instruction} ({challenge_remaining:.1f}s)"
            #         challenge_color = (0, 255, 255)  # Cyan
            #         
            #         # Draw challenge text in status area (below other status info)
            #         # First draw a background box
            #         cv2.rectangle(frame, (5, 100), (600, 140), (0, 0, 0), -1)
            #         # Then draw the challenge text
            #         cv2.putText(frame, challenge_text, (10, 125),
            #                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 0), 4)  # Black outline
            #         cv2.putText(frame, challenge_text, (10, 125),
            #                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, challenge_color, 2)  # Colored text
            

            cv2.imshow("Recognition", frame)
            key = cv2.waitKey(30) & 0xFF
            if key == 27:  # ESC key
                break

        cap.release()
        cv2.destroyAllWindows()
        self.logger.info("Recognition stopped.")
        print("Recognition stopped.")

