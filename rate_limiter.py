import json
import os
from datetime import datetime, timedelta
from utils import setup_logger
import random

logger = setup_logger(__name__)

RATE_LIMIT_FILE = "rate_limits.json"
LIMIT_WINDOW_HOURS = 24

# Per-model limits
MODEL_LIMITS = {
    "pro": 5,      # Nano Banana Pro (2K, best quality)
    "grok": 10,    # Grok Imagine (artistic style)
    "nano": 10     # Nano Banana (1K)
}

# Model display names
MODEL_NAMES = {
    "pro": "Nano Banana Pro",
    "grok": "Grok Imagine",
    "nano": "Nano Banana"
}

# Messages when a specific model limit is hit
MODEL_LIMIT_RESPONSES = {
    "pro": [
        "Yo, you used up your Pro designs for today! Try Grok or Nano instead. 🔥",
        "Pro tier's maxed out fam! Switch to Grok for that artistic vibe or Nano. 💪",
        "That's all your Pro shots for today! Grok and Nano still available. 🎨",
    ],
    "grok": [
        "Grok's tapped out for today! Try Pro or Nano instead. 🔥",
        "No more Grok designs left fam! Switch to Pro or Nano. 💪",
        "Grok Imagine is done for today! Pro and Nano still available. 🎨",
    ],
    "nano": [
        "Nano tier's maxed out! Try Pro or Grok instead. 🔥",
        "No more Nano designs left fam! Switch to Pro or Grok. 💪",
        "Nano is done for today! Pro and Grok still available. 🎨",
    ]
}

# Messages when ALL models are exhausted
ALL_EXHAUSTED_RESPONSES = [
    "Yo fam, you hit ALL the limits! Hit up **A a real ice hole** or **Tricon Digital** to get extended. 💸",
    "Damn, you maxed out everything! Holla at **A a real ice hole** or **Tricon Digital** for more. 🔥",
    "Aight that's ALL models done! Contact **A a real ice hole** or **Tricon Digital** to keep going. 💯",
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

    def _ensure_user_structure(self, user_id: str):
        """Ensure user has proper data structure for per-model tracking."""
        if user_id not in self.data:
            self.data[user_id] = {"pro": [], "grok": [], "nano": []}
        # Handle legacy data format (list instead of dict)
        if isinstance(self.data[user_id], list):
            self.data[user_id] = {"pro": [], "grok": [], "nano": []}
        # Ensure all model keys exist
        for model in MODEL_LIMITS.keys():
            if model not in self.data[user_id]:
                self.data[user_id][model] = []

    def _clean_old_entries(self, user_id: str):
        """Remove entries older than 24 hours for a user."""
        self._ensure_user_structure(user_id)
        cutoff_time = datetime.now() - timedelta(hours=LIMIT_WINDOW_HOURS)

        for model in MODEL_LIMITS.keys():
            self.data[user_id][model] = [
                timestamp for timestamp in self.data[user_id][model]
                if datetime.fromisoformat(timestamp) > cutoff_time
            ]

    def get_model_usage(self, user_id: str, model: str) -> int:
        """Get current usage count for a specific model."""
        user_id = str(user_id)
        self._clean_old_entries(user_id)
        return len(self.data[user_id].get(model, []))

    def get_all_usage(self, user_id: str) -> dict:
        """Get usage counts for all models."""
        user_id = str(user_id)
        self._clean_old_entries(user_id)
        return {
            model: len(self.data[user_id].get(model, []))
            for model in MODEL_LIMITS.keys()
        }

    def check_rate_limit(self, user_id: str, model: str) -> dict:
        """
        Check if user can use a specific model.

        Returns:
            dict with:
                - allowed (bool): Whether generation is allowed
                - model (str): The model being checked
                - count (int): Current usage count for this model
                - limit (int): Max allowed for this model
                - message (str): Message to show user (if any)
                - alternatives (list): Other models still available
        """
        user_id = str(user_id)
        self._clean_old_entries(user_id)

        count = self.get_model_usage(user_id, model)
        limit = MODEL_LIMITS.get(model, 10)

        # Check what alternatives are available
        alternatives = []
        for m, m_limit in MODEL_LIMITS.items():
            if m != model and self.get_model_usage(user_id, m) < m_limit:
                alternatives.append(m)

        if count >= limit:
            # This model is exhausted
            if not alternatives:
                # ALL models exhausted
                return {
                    "allowed": False,
                    "model": model,
                    "count": count,
                    "limit": limit,
                    "message": random.choice(ALL_EXHAUSTED_RESPONSES),
                    "alternatives": []
                }
            else:
                # This model exhausted but others available
                return {
                    "allowed": False,
                    "model": model,
                    "count": count,
                    "limit": limit,
                    "message": random.choice(MODEL_LIMIT_RESPONSES[model]),
                    "alternatives": alternatives
                }
        else:
            # Allowed
            remaining = limit - count
            return {
                "allowed": True,
                "model": model,
                "count": count,
                "limit": limit,
                "message": None,
                "alternatives": alternatives,
                "remaining": remaining
            }

    def record_generation(self, user_id: str, model: str):
        """Record a new generation for a user and model."""
        user_id = str(user_id)
        self._ensure_user_structure(user_id)

        self.data[user_id][model].append(datetime.now().isoformat())
        self._save_data()

        count = len(self.data[user_id][model])
        limit = MODEL_LIMITS[model]
        logger.info(f"Recorded {MODEL_NAMES[model]} generation for user {user_id}. Usage: {count}/{limit}")


# Global instance
rate_limiter = RateLimiter()
