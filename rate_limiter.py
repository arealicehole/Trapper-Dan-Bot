import json
import os
from datetime import datetime, timedelta
from utils import setup_logger
import random

logger = setup_logger(__name__)

RATE_LIMIT_FILE = "rate_limits.json"
SOFT_LIMIT = 10  # Show donation message
HARD_LIMIT = 20  # Block further generations
LIMIT_WINDOW_HOURS = 24

# Unique Trapper Dan responses for soft limit (at 10)
SOFT_LIMIT_RESPONSES = [
    "Ayy, you cookin' with gas! You got a couple more left, keep it 100. 💯",
    "Damn fam, you been busy! Got a couple more designs left for ya. 🔥",
    "Yo you really love this huh? You got a couple more in the tank. 💪",
    "Sheesh, you on a roll! A couple more left, make 'em count. 🎨",
    "Aight player, you got a couple more shots left. Let's get it! 🚀",
]

# Unique responses for hard limit (at 20)
HARD_LIMIT_RESPONSES = [
    "Yo fam, you hit the limit! Hit up **A a real ice hole** or **Tricon Digital** to get your limit extended. 💸",
    "Damn, you maxed out! Holla at **A a real ice hole** or **Tricon Digital** if you need more designs. 🔥",
    "Aight that's it for now! Contact **A a real ice hole** or **Tricon Digital** to keep going. 💯",
    "You tapped out the daily limit! Hit **A a real ice hole** or **Tricon Digital** to extend it. 📞",
]

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
            # Hard limit - block and tell them to contact A a real ice hole or Tricon Digital
            return {
                "allowed": False,
                "count": count,
                "message": random.choice(HARD_LIMIT_RESPONSES)
            }
        elif count == SOFT_LIMIT:
            # Soft limit - show unique message when they hit exactly 10
            return {
                "allowed": True,
                "count": count,
                "message": random.choice(SOFT_LIMIT_RESPONSES)
            }
        else:
            # Under soft limit or between soft and hard - no message
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
