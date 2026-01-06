from app.services.enrollment_service import EnrollmentService
from app.services.recognition_service import RecognitionService
from app.database.db_manager import DatabaseManager

def initialize_database():
    """
    Initialize database if it doesn't exist.
    """
    db_manager = DatabaseManager()
    
    if not db_manager.is_initialized():
        try:
            db_manager.initialize_db()
            print("Database initialized successfully.")
        except Exception as e:
            print(f"Warning: Database initialization failed: {e}")
            print("System will continue with file-based storage.")
    else:
        print("Database connection verified.")

def main():
    # Initialize database on startup
    initialize_database()
    
    enrollment_service = EnrollmentService()  # Initialize once for reuse
    
    # Main menu loop
    while True:
        print()
        print("=" * 60)
        print("ATTENDANCE SYSTEM - MAIN MENU")
        print("=" * 60)
        print("1. Enroll user")
        print("2. Run recognition")
        print("3. Remove enrollment")
        print("4. Update enrollment (rescan face + QR)")
        print("5. Generate QR code for user")
        print("6. Generate QR codes for all users")
        print("7. List enrolled users")
        print("8. Run QR code scanner test")
        print("9. Exit")
        print("=" * 60)
        choice = input("Select option: ").strip()

        if choice == "1":
            print("\nUser ID options:")
            print("  - Press Enter to auto-generate ID")
            print("  - Or enter a custom User ID")
            user_id_input = input("Enter User ID (or press Enter for auto): ").strip()
            
            # Ask for required user details
            name = input("Enter name (required): ").strip()
            if not name:
                print("Error: Name is required for enrollment.")
                print("\nPress Enter to return to menu...")
                input()
                continue
            
            role = input("Enter role (required, e.g., 'student' or 'staff'): ").strip()
            if not role:
                print("Error: Role is required for enrollment.")
                print("\nPress Enter to return to menu...")
                input()
                continue
            
            # Pass empty string if user wants auto-generation
            user_id = user_id_input if user_id_input else None
            enrollment_service.enroll(user_id, name=name, role=role)
            print("\nPress Enter to return to menu...")
            input()
            
        elif choice == "2":
            RecognitionService().run_realtime()
            print("\nPress Enter to return to menu...")
            input()
            
        elif choice == "3":
            enrollment_service.list_enrolled_users()
            
            user_id = input("\nEnter User ID to remove (or 'cancel' to abort): ").strip()
            
            if user_id.lower() == 'cancel':
                print("Cancelled.")
                print("\nPress Enter to return to menu...")
                input()
                continue
            
            if not user_id:
                print("Invalid User ID.")
                print("\nPress Enter to return to menu...")
                input()
                continue
            
            # Confirm deletion
            confirm = input(f"Are you sure you want to remove enrollment for '{user_id}'? (yes/no): ").strip().lower()
            
            if confirm in ['yes', 'y']:
                enrollment_service.remove_enrollment(user_id)
            else:
                print("Cancelled.")
            print("\nPress Enter to return to menu...")
            input()
            
        elif choice == "4":
            enrollment_service.list_enrolled_users()
            
            user_id = input("\nEnter User ID to update (or 'cancel' to abort): ").strip()
            
            if user_id.lower() == 'cancel':
                print("Cancelled.")
                print("\nPress Enter to return to menu...")
                input()
                continue
            
            if not user_id:
                print("Invalid User ID.")
                print("\nPress Enter to return to menu...")
                input()
                continue
            
            # Check if user exists
            from app.database.db_manager import DatabaseManager
            from app.database.models import User
            db_manager = DatabaseManager()
            user_model = User(db_manager)
            user = user_model.get_by_id(user_id)
            
            if not user:
                print(f"Error: User '{user_id}' not found.")
                print("\nPress Enter to return to menu...")
                input()
                continue
            
            print(f"\nUpdating enrollment for: {user_id}")
            print("Current info:")
            print(f"  Name: {user.get('name', 'N/A')}")
            print(f"  Role: {user.get('role', 'N/A')}")
            print(f"  QR Code: {user.get('qr_code', 'Not set')}")
            
            # Ask for optional updates
            name = input("\nEnter new name (or press Enter to keep current): ").strip() or None
            role = input("Enter new role (or press Enter to keep current): ").strip() or None
            
            print("\nStarting update process...")
            print("This will capture new face samples and QR code simultaneously.")
            enrollment_service.update_enrollment(user_id, name=name, role=role)
            print("\nPress Enter to return to menu...")
            input()
            
        elif choice == "5":
            enrollment_service.list_enrolled_users()
            
            user_id = input("\nEnter User ID to generate QR code for (or 'cancel' to abort): ").strip()
            
            if user_id.lower() == 'cancel':
                print("Cancelled.")
                print("\nPress Enter to return to menu...")
                input()
                continue
            
            if not user_id:
                print("Invalid User ID.")
                print("\nPress Enter to return to menu...")
                input()
                continue
            
            enrollment_service.generate_qr_for_user(user_id)
            print("\nPress Enter to return to menu...")
            input()
            
        elif choice == "6":
            print("\nGenerating QR codes for all users without QR codes...")
            enrollment_service.generate_qr_for_all_users()
            print("\nPress Enter to return to menu...")
            input()
            
        elif choice == "7":
            enrollment_service.list_enrolled_users()
            print("\nPress Enter to return to menu...")
            input()
            
        elif choice == "8":
            import test_qr_scanner
            test_qr_scanner.run_scanner()
            print("\nPress Enter to return to menu...")
            input()
            
        elif choice == "9":
            print("\nExiting application...")
            break
            
        else:
            print("Invalid option. Please try again.")
            print("\nPress Enter to continue...")
            input()

if __name__ == "__main__":
    main()


