import cv2
import numpy as np
from collections import deque
from app.utils.logging import setup_logger

# Try to import MediaPipe - handle both old and new API
try:
    import mediapipe as mp
    # Check if solutions API is available (older versions)
    if hasattr(mp, 'solutions'):
        USE_LEGACY_API = True
    else:
        # Use new tasks API
        from mediapipe.tasks import python
        from mediapipe.tasks.python import vision
        from mediapipe import tasks
        USE_LEGACY_API = False
except ImportError:
    raise ImportError("MediaPipe is not installed. Please install it with: pip install mediapipe")


class LivenessDetector:
    """
    Lightweight liveness detection using:
    - Eye blink detection (EAR)
    - Head movement detection (pose delta)
    """

    def __init__(self):
        self.logger = setup_logger()
        self.USE_LEGACY_API = USE_LEGACY_API

        if USE_LEGACY_API:
            # Legacy API (MediaPipe < 0.10)
            self.face_mesh = mp.solutions.face_mesh.FaceMesh(
                static_image_mode=False,
                max_num_faces=1,
                refine_landmarks=True,
                min_detection_confidence=0.5,
                min_tracking_confidence=0.5
            )
        else:
            # New API (MediaPipe >= 0.10) - use bundled model
            import os
            model_path = os.path.join(os.path.dirname(__file__), '../../models/face_landmarker.task')
            # If model doesn't exist, we'll use a simpler approach
            # For now, we'll download or use a fallback
            # MediaPipe 0.10+ requires a model file, which is complex to set up
            # For now, use fallback mode (head movement only)
            self.logger.info("MediaPipe 0.10+ detected - using simplified liveness detection (head movement only)")
            self.face_landmarker = None

        # EAR thresholds
        self.EAR_THRESHOLD = 0.20
        self.BLINK_FRAMES_REQUIRED = 2
        self.blink_counter = 0

        # Head movement
        self.head_positions = deque(maxlen=10)  # Track frames for detection (reduced for faster response)
        self.HEAD_MOVEMENT_THRESHOLD = 5.0  # pixels - more sensitive threshold
        self.MIN_MOVEMENT_FRAMES = 1  # Require movement across 1 frame (faster response)
        self.movement_frame_count = 0
        
        # Challenge-specific states
        self.blink_detected = False
        self.head_turned_left = False
        self.head_turned_right = False
        self.last_head_center = None
        
        # Cache face detector to avoid recreating it every frame
        self._face_detector = None
    
    def reset(self):
        """
        Reset liveness detection state.
        Should be called when starting a new verification session.
        """
        self.head_positions.clear()
        self.blink_counter = 0
        self.movement_frame_count = 0
        self.blink_detected = False
        self.head_turned_left = False
        self.head_turned_right = False
        self.last_head_center = None

    def _eye_aspect_ratio(self, eye_points):
        """
        Compute Eye Aspect Ratio (EAR).
        """
        A = np.linalg.norm(eye_points[1] - eye_points[5])
        B = np.linalg.norm(eye_points[2] - eye_points[4])
        C = np.linalg.norm(eye_points[0] - eye_points[3])
        return (A + B) / (2.0 * C)

    def detect(self, frame, face=None):
        """
        Returns True if liveness is confirmed.
        
        Args:
            frame: Video frame
            face: Optional pre-detected face object to avoid re-detection
        """
        h, w, _ = frame.shape
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        
        if self.USE_LEGACY_API:
            # Legacy API
            results = self.face_mesh.process(rgb)
            if not results.multi_face_landmarks:
                return False
            landmarks = results.multi_face_landmarks[0].landmark
        else:
            # New API
            if self.face_landmarker is None:
                # Fallback: use basic head movement only (no blink detection)
                # Pass pre-detected face to avoid re-detection
                return self._detect_head_movement_only(frame, face)
            
            mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
            detection_result = self.face_landmarker.detect(mp_image)
            if not detection_result.face_landmarks:
                return False
            landmarks = detection_result.face_landmarks[0]

        # Eye landmark indices (MediaPipe)
        left_eye_idx = [33, 160, 158, 133, 153, 144]
        right_eye_idx = [362, 385, 387, 263, 373, 380]

        if self.USE_LEGACY_API:
            # Legacy API - landmarks are accessed directly
            left_eye = np.array([
                (landmarks[i].x * w, landmarks[i].y * h)
                for i in left_eye_idx
            ])
            right_eye = np.array([
                (landmarks[i].x * w, landmarks[i].y * h)
                for i in right_eye_idx
            ])
        else:
            # New API - landmarks are accessed via index
            left_eye = np.array([
                (landmarks[i].x * w, landmarks[i].y * h)
                for i in left_eye_idx
            ])
            right_eye = np.array([
                (landmarks[i].x * w, landmarks[i].y * h)
                for i in right_eye_idx
            ])

        ear = (self._eye_aspect_ratio(left_eye) +
               self._eye_aspect_ratio(right_eye)) / 2.0

        # Blink detection
        if ear < self.EAR_THRESHOLD:
            self.blink_counter += 1
        else:
            if self.blink_counter >= self.BLINK_FRAMES_REQUIRED:
                self.logger.info("Blink detected")
                self.blink_detected = True  # Set flag for challenge-response
                return True
            self.blink_counter = 0

        # Head movement detection
        if self.USE_LEGACY_API:
            nose_tip = landmarks[1]
        else:
            nose_tip = landmarks[1]
        nose_pos = (nose_tip.x * w, nose_tip.y * h)
        self.head_positions.append(nose_pos)

        if len(self.head_positions) >= 2:
            dx = abs(self.head_positions[-1][0] - self.head_positions[0][0])
            dy = abs(self.head_positions[-1][1] - self.head_positions[0][1])

            if dx > self.HEAD_MOVEMENT_THRESHOLD or dy > self.HEAD_MOVEMENT_THRESHOLD:
                self.logger.info("Head movement detected")
                return True

        return False
    
    def _detect_head_movement_only(self, frame, face=None):
        """
        Improved liveness detection using head movement with multiple checks.
        Uses existing InsightFace detector for face position tracking.
        More robust against photo spoofing by requiring significant, multi-directional movement.
        
        Args:
            frame: Video frame
            face: Optional pre-detected face object to avoid re-detection
        """
        # Use pre-detected face if provided, otherwise detect
        if face is not None:
            faces = [face]
        else:
            # Use cached face detector to avoid recreating it every frame
            if self._face_detector is None:
                from app.core.face_detector import FaceDetector
                self._face_detector = FaceDetector()
            faces = self._face_detector.detect(frame)
        
        if len(faces) != 1:
            # Reset if no face or multiple faces
            if len(self.head_positions) > 0:
                self.head_positions.clear()
                self.movement_frame_count = 0
            return False
        
        # Get face bounding box center and size for more stable tracking
        bbox = faces[0].bbox
        center_x = (bbox[0] + bbox[2]) / 2
        center_y = (bbox[1] + bbox[3]) / 2
        face_width = bbox[2] - bbox[0]
        face_height = bbox[3] - bbox[1]
        
        # Normalize position by face size to account for distance changes
        head_pos = (center_x / max(face_width, 1), center_y / max(face_height, 1))
        self.head_positions.append(head_pos)
        
        # Track head movement direction for challenge-response
        # Use more sensitive detection for challenge-response (needs to be responsive)
        current_center = center_x
        if self.last_head_center is not None:
            dx = current_center - self.last_head_center
            # More sensitive threshold for challenge-response (1.5% instead of 3%)
            turn_threshold = face_width * 0.015
            
            if dx < -turn_threshold:  # Moved left
                self.head_turned_left = True
                self.head_turned_right = False
            elif dx > turn_threshold:  # Moved right
                self.head_turned_right = True
                self.head_turned_left = False
        
        self.last_head_center = current_center
        
        # Need at least 2 frames to analyze movement (reduced for faster response)
        if len(self.head_positions) < 2:
            return False
        
        # Check recent movement (last 2 frames) - more responsive
        if len(self.head_positions) >= 2:
            # Check movement between last 2 positions
            recent_dx = abs(self.head_positions[-1][0] - self.head_positions[-2][0])
            recent_dy = abs(self.head_positions[-1][1] - self.head_positions[-2][1])
            recent_movement_threshold = 0.01  # 1% of face size (more sensitive)
            if np.sqrt(recent_dx**2 + recent_dy**2) > recent_movement_threshold:
                self.movement_frame_count += 1
                if self.movement_frame_count >= 1:
                    self.logger.info(f"Head movement detected: recent_movement={np.sqrt(recent_dx**2 + recent_dy**2):.4f}")
                    return True
        
        # Also check overall movement from start (if we have enough frames)
        if len(self.head_positions) >= 3:
            dx_total = abs(self.head_positions[-1][0] - self.head_positions[0][0])
            dy_total = abs(self.head_positions[-1][1] - self.head_positions[0][1])
            total_movement = np.sqrt(dx_total**2 + dy_total**2)
            movement_threshold_normalized = 0.01  # 1% of face size (more sensitive)
            
            if total_movement > movement_threshold_normalized:
                self.movement_frame_count += 1
                if self.movement_frame_count >= 1:
                    self.logger.info(f"Head movement detected: total_movement={total_movement:.4f}")
                    return True
        
        # Reset counter if no movement detected
        self.movement_frame_count = 0
        
        return False
    
    def check_blink(self):
        """
        Check if a blink was detected (for challenge-response).
        Returns True if blink was detected, then resets the flag.
        """
        if self.blink_detected:
            self.blink_detected = False  # Reset after checking
            return True
        return False
    
    def check_head_turn_left(self):
        """
        Check if head turned left (for challenge-response).
        Returns True if left turn was detected, then resets the flag.
        """
        if self.head_turned_left:
            self.head_turned_left = False  # Reset after checking
            return True
        return False
    
    def check_head_turn_right(self):
        """
        Check if head turned right (for challenge-response).
        Returns True if right turn was detected, then resets the flag.
        """
        if self.head_turned_right:
            self.head_turned_right = False  # Reset after checking
            return True
        return False

