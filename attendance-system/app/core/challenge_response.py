import random
import time
from app.utils.logging import setup_logger


class ChallengeResponse:
    """
    Handles randomised liveness challenges.
    Prevents pre-recorded video replay attacks by requiring
    real-time responses to random instructions.
    """

    def __init__(self):
        self.logger = setup_logger()
        self.challenges = [
            "BLINK",
            "TURN_LEFT",
            "TURN_RIGHT"
        ]
        self.current_challenge = None
        self.start_time = None
        self.TIME_LIMIT = 4  # seconds

    def generate_challenge(self):
        """
        Generate a random challenge.
        Returns the challenge type.
        """
        self.current_challenge = random.choice(self.challenges)
        self.start_time = time.time()
        self.logger.info(f"Generated challenge: {self.current_challenge}")
        return self.current_challenge

    def is_expired(self):
        """
        Check if the current challenge has expired.
        """
        if self.current_challenge is None or self.start_time is None:
            return True
        return (time.time() - self.start_time) > self.TIME_LIMIT

    def get_remaining_time(self):
        """
        Get remaining time for current challenge.
        Returns seconds remaining, or 0 if expired.
        """
        if self.current_challenge is None or self.start_time is None:
            return 0
        elapsed = time.time() - self.start_time
        remaining = self.TIME_LIMIT - elapsed
        return max(0, remaining)

    def reset(self):
        """
        Reset challenge state.
        """
        self.current_challenge = None
        self.start_time = None

