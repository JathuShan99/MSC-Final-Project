"""
Simple QR code scanner test script.
Opens webcam and scans for QR codes.
"""
import cv2
from app.core.id_validator import IDValidator

def main():
    print("QR Code Scanner Test")
    print("Press ESC to exit")
    print("-" * 40)
    
    validator = IDValidator()
    cap = cv2.VideoCapture(0)
    
    if not cap.isOpened():
        print("Error: Could not access webcam")
        return
    
    # Set webcam properties
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
    
    print("\nShow a QR code to the camera...")
    
    last_scanned = None
    
    while True:
        ret, frame = cap.read()
        if not ret:
            continue
        
        # Flip frame horizontally for mirror effect
        frame = cv2.flip(frame, 1)
        
        # Scan for QR code
        scanned_qr = validator.scan(frame)
        
        if scanned_qr:
            if scanned_qr != last_scanned:
                print(f"\n✓ QR Code detected: {scanned_qr}")
                last_scanned = scanned_qr
            # Draw green border and text
            h, w = frame.shape[:2]
            cv2.rectangle(frame, (10, 10), (w-10, h-10), (0, 255, 0), 3)
            cv2.putText(frame, f"QR: {scanned_qr}", (20, 40),
                       cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
        else:
            last_scanned = None
            # Draw yellow border
            h, w = frame.shape[:2]
            cv2.rectangle(frame, (10, 10), (w-10, h-10), (0, 255, 255), 2)
            cv2.putText(frame, "Show QR code...", (20, 40),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 255), 2)
        
        cv2.imshow("QR Code Scanner", frame)
        
        key = cv2.waitKey(30) & 0xFF
        if key == 27:  # ESC key
            break
    
    cap.release()
    cv2.destroyAllWindows()
    print("\nQR scanner closed.")

if __name__ == "__main__":
    main()

