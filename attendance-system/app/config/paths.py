from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[2]
DATA_DIR = BASE_DIR / "data"
EMBEDDINGS_DIR = DATA_DIR / "embeddings"
DB_DIR = DATA_DIR / "database"
LOG_DIR = BASE_DIR / "logs"
EXPORTS_DIR = DATA_DIR / "exports"

# Database path
DB_PATH = DB_DIR / "attendance.db"

# Create directories
EMBEDDINGS_DIR.mkdir(parents=True, exist_ok=True)
DB_DIR.mkdir(parents=True, exist_ok=True)
LOG_DIR.mkdir(parents=True, exist_ok=True)
EXPORTS_DIR.mkdir(parents=True, exist_ok=True)
(EXPORTS_DIR / "evaluation").mkdir(parents=True, exist_ok=True)  # Evaluation plots directory


