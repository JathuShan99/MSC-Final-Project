from insightface.app import FaceAnalysis
from app.config.settings import FACE_MODEL_NAME, CTX_ID

class FaceDetector:
    """
    Face detection using RetinaFace (InsightFace).
    """
    def __init__(self):
        self._model = FaceAnalysis(name=FACE_MODEL_NAME)
        self._model.prepare(ctx_id=CTX_ID)

    def detect(self, frame):
        """
        Detect faces in a frame.
        Returns a list of face objects.
        """
        return self._model.get(frame)


