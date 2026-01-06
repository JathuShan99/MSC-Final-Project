import cv2
from pyzbar.pyzbar import decode
from app.utils.logging import setup_logger


class IDValidator:
    """
    Validates institutional ID using QR codes.
    """

    def __init__(self):
        self.logger = setup_logger()

    def scan(self, frame):
        """
        Scan QR code from frame.
        Returns decoded ID string or None.
        """
        try:
            # Convert to grayscale for better QR detection
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            decoded_objects = decode(gray)
            
            for obj in decoded_objects:
                qr_data = obj.data.decode("utf-8")
                self.logger.info(f"QR detected: {qr_data}")
                return qr_data
            
            return None
        except Exception as e:
            self.logger.warning(f"QR scan error: {e}")
            return None

