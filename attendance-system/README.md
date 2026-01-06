# Attendance System - Phase 1 & 2A

## Overview

This system implements a modular biometric face recognition system using pre-trained RetinaFace and ArcFace models. The design follows enterprise software principles, separating configuration, core ML logic, and service workflows, while ensuring GDPR-compliant storage through embedding-only persistence.

## Completed Phases

### Phase 1: Enrollment System ✅
- Face detection using RetinaFace
- Face embedding extraction using ArcFace
- Enrollment workflow (5 samples per user)
- Configuration management
- Logging and auditability
- CPU-only inference (no GPU required)

### Phase 2A: Recognition System ✅
- Real-time face recognition
- Multi-user matching using cosine similarity
- Threshold-based decision making
- Live recognition service

### Excluded (Future Phases)
- Liveness detection
- Database logging
- Dashboard
- REST APIs

## Architecture

The system follows a layered architecture:

- **Configuration Layer**: Centralized settings and path management
- **Core ML Layer**: Face detection and embedding extraction
- **Service Layer**: Business logic and workflows
- **Utility Layer**: Logging and helper functions

## Installation

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. The InsightFace models will be automatically downloaded on first run.

## Usage

Run the application:

```bash
py -3.10 -m app.main
```

### Menu Options:

**1. Enroll user**
- Prompts for a User ID
- Opens webcam
- Collects 5 face samples (when exactly one face is detected)
- Saves embeddings to `data/embeddings/{user_id}.npy`
- Logs all events to `logs/system.log`
- Press `ESC` to cancel

**2. Run recognition**
- Loads all enrolled users
- Opens webcam for real-time recognition
- Compares detected faces against enrolled templates
- Displays recognition results with similarity scores
- Press `ESC` to exit

## Project Structure

```
attendance-system/
├── app/
│   ├── main.py                 # Entry point
│   ├── config/                 # Configuration
│   │   ├── settings.py
│   │   └── paths.py
│   ├── core/                   # ML components
│   │   ├── face_detector.py
│   │   └── face_recognizer.py
│   ├── services/               # Business logic
│   │   ├── enrollment_service.py
│   │   └── recognition_service.py
│   └── utils/                  # Utilities
│       └── logging.py
├── data/
│   └── embeddings/             # Saved embeddings
├── logs/
│   └── system.log              # System logs
└── requirements.txt
```

## Technical Details

- **Face Detection**: RetinaFace (InsightFace)
- **Embedding Model**: ArcFace (512-dimensional vectors)
- **Recognition**: Cosine similarity matching
- **Similarity Threshold**: 0.5 (configurable in `app/config/settings.py`)
- **Storage**: NumPy arrays (.npy files)
- **Compliance**: No raw images stored (GDPR-friendly)
- **Hardware**: CPU-only inference

## Academic Contribution

This system demonstrates:
- Feature extraction from biometric data
- Representation learning using deep learning models
- Real-time face recognition and matching
- Similarity-based classification
- Ethical data handling practices (embedding-only storage)
- Reproducible experiment setup
- Enterprise-grade software architecture

## Status

✅ **Phase 1**: Enrollment System - **COMPLETE**  
✅ **Phase 2A**: Recognition System - **COMPLETE**

The system is fully functional for enrollment and real-time recognition.

## License

[Add your license here]


