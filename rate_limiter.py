import json
import os
from datetime import datetime, timedelta
from utils import setup_logger

logger = setup_logger(__name__)

RATE_LIMIT_FILE = "rate_limits.json"
SOFT_LIMIT = 10  # Show donation message
HARD_LIMIT = 20  # Block further generations
LIMIT_WINDOW_HOURS = 24

class RateLimiter:
    def __init__(self):
        self.data = self._load_data()

    def _load_data(self):
        """Load rate limit data from file."""
        if os.path.exists(RATE_LIMIT_FILE):
            try:
                with open(RATE_LIMIT_FILE, 'r') as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Error loading rate limit data: {e}")
                return {}
        return {}

    def _save_data(self):
        """Save rate limit data to file."""
        try:
            with open(RATE_LIMIT_FILE, 'w') as f:
                json.dump(self.data, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving rate limit data: {e}")

    def _clean_old_entries(self, user_id: str):
        """Remove entries older than 24 hours for a user."""
        if user_id not in self.data:
            return

        cutoff_time = datetime.now() - timedelta(hours=LIMIT_WINDOW_HOURS)
        self.data[user_id] = [
            timestamp for timestamp in self.data[user_id]
            if datetime.fromisoformat(timestamp) > cutoff_time
        ]

    def check_rate_limit(self, user_id: str) -> dict:
        """
        Check if user has exceeded rate limits.

        Returns:
            dict with:
                - allowed (bool): Whether generation is allowed
                - count (int): Current generation count in window
                - message (str): Message to show user (if any)
        """
        user_id = str(user_id)
        self._clean_old_entries(user_id)

        count = len(self.data.get(user_id, []))

        if count >= HARD_LIMIT:
            return {
                "allowed": False,
                "count": count,
                "message": (
                    f"Yo fam, you've hit the daily limit ({HARD_LIMIT} designs in 24 hours). "
                    "Come back tomorrow or support the bot to keep it running! "
                    "Cash App: **$trapperdan** 💸"
                )
            }
        elif count >= SOFT_LIMIT:
            return {
                "allowed": True,
                "count": count,
                "message": (
                    f"Ayy, you've made {count} designs today! You're loving this huh? 😎\n"
                    "If you want to support Trapper Dan Bot and keep it running smooth, "
                    "consider sending some love to Cash App: **$trapperdan** 💰\n"
                    f"(You got {HARD_LIMIT - count} more designs left today)"
                )
            }
        else:
            return {
                "allowed": True,
                "count": count,
                "message": None
            }

    def record_generation(self, user_id: str):
        """Record a new generation for a user."""
        user_id = str(user_id)
        if user_id not in self.data:
            self.data[user_id] = []

        self.data[user_id].append(datetime.now().isoformat())
        self._save_data()
        logger.info(f"Recorded generation for user {user_id}. Total in window: {len(self.data[user_id])}")

# Global instance
rate_limiter = RateLimiter()
