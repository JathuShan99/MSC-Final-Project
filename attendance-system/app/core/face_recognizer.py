import numpy as np
from sklearn.metrics.pairwise import cosine_similarity
from app.config.settings import SIMILARITY_THRESHOLD

class FaceRecognizer:
    """
    Face embedding extraction and comparison.
    """
    @staticmethod
    def extract_embedding(face):
        """
        Returns a 512-D embedding vector.
        """
        embedding = face.embedding
        return np.asarray(embedding, dtype="float32")

    @staticmethod
    def compare(test_embedding, stored_embeddings):
        """
        Compare test embedding with stored embeddings.
        Returns (is_match, similarity_score).
        """
        test_embedding = test_embedding.reshape(1, -1)
        scores = cosine_similarity(test_embedding, stored_embeddings)
        avg_score = float(scores.mean())
        return avg_score >= SIMILARITY_THRESHOLD, avg_score


