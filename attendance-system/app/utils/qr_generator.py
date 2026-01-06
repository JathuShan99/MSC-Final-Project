import qrcode
from pathlib import Path
from app.config.paths import DATA_DIR
from app.utils.logging import setup_logger


class QRGenerator:
    """
    Generates QR codes for user IDs.
    """
    
    def __init__(self):
        self.logger = setup_logger()
        self.qr_codes_dir = DATA_DIR / 'qr_codes'
        self.qr_codes_dir.mkdir(parents=True, exist_ok=True)
    
    def generate(self, user_id: str, save_image: bool = True):
        """
        Generate a QR code containing the user_id.
        
        Args:
            user_id: The user ID to encode in the QR code
            save_image: Whether to save the QR code as an image file
        
        Returns:
            tuple: (qr_data_string, image_path) or (qr_data_string, None) if save_image=False
        """
        try:
            # Create QR code instance
            qr = qrcode.QRCode(
                version=1,
                error_correction=qrcode.constants.ERROR_CORRECT_L,
                box_size=10,
                border=4,
            )
            qr.add_data(user_id)
            qr.make(fit=True)
            
            # Create image
            img = qr.make_image(fill_color="black", back_color="white")
            
            image_path = None
            if save_image:
                # Save QR code image
                image_path = self.qr_codes_dir / f"{user_id}_qr.png"
                img.save(image_path)
                self.logger.info(f"QR code generated and saved: {image_path}")
            
            return user_id, image_path
            
        except Exception as e:
            self.logger.error(f"Failed to generate QR code for {user_id}: {e}")
            raise
    
    def get_qr_path(self, user_id: str):
        """
        Get the expected path for a user's QR code image.
        
        Args:
            user_id: The user ID
        
        Returns:
            Path to the QR code image file
        """
        return self.qr_codes_dir / f"{user_id}_qr.png"
    
    def qr_exists(self, user_id: str):
        """
        Check if a QR code image already exists for a user.
        
        Args:
            user_id: The user ID
        
        Returns:
            bool: True if QR code image exists
        """
        return self.get_qr_path(user_id).exists()
    
    def delete_qr(self, user_id: str):
        """
        Delete a QR code image file.
        
        Args:
            user_id: The user ID
        
        Returns:
            bool: True if deleted successfully
        """
        qr_path = self.get_qr_path(user_id)
        if qr_path.exists():
            try:
                qr_path.unlink()
                self.logger.info(f"Deleted QR code: {qr_path}")
                return True
            except Exception as e:
                self.logger.warning(f"Failed to delete QR code {qr_path}: {e}")
                return False
        return False

