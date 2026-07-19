import json
import os
from datetime import datetime

USER_MEMORY_PATH = os.getenv("USER_MEMORY_PATH", "./data/user_memory.json")


class UserMemoryStore:
    """Long-term persistent profile storage per user.
    
    Each user (identified by WhatsApp JID) has a JSON profile
    containing personal facts (name, age, profession, preferences, etc.)
    persisted to disk so data survives server restarts.
    """

    def __init__(self, file_path: str = USER_MEMORY_PATH):
        self.file_path = file_path
        self._ensure_file()

    def _ensure_file(self):
        os.makedirs(os.path.dirname(self.file_path), exist_ok=True)
        if not os.path.exists(self.file_path):
            with open(self.file_path, "w") as f:
                json.dump({}, f)

    def _load_all(self) -> dict:
        with open(self.file_path, "r") as f:
            return json.load(f)

    def _save_all(self, data: dict):
        with open(self.file_path, "w") as f:
            json.dump(data, f, indent=2)

    def get_profile(self, user_id: str) -> dict:
        data = self._load_all()
        return data.get(user_id, {})

    def update_profile(self, user_id: str, updates: dict):
        data = self._load_all()
        if user_id not in data:
            data[user_id] = {}
        data[user_id].update(updates)
        data[user_id]["_last_updated"] = datetime.now().isoformat()
        self._save_all(data)


class ConversationBuffer:
    """Short-term in-memory conversation history.
    
    Keeps the last N messages per user for context continuity.
    Resets on server restart — only the profile store is persistent.
    """

    def __init__(self, max_messages: int = 10):
        self.max_messages = max_messages
        self._stores: dict[str, list[dict]] = {}

    def add_message(self, user_id: str, role: str, content: str):
        if user_id not in self._stores:
            self._stores[user_id] = []
        self._stores[user_id].append(
            {"role": role, "content": content, "timestamp": datetime.now().isoformat()}
        )
        if len(self._stores[user_id]) > self.max_messages:
            self._stores[user_id] = self._stores[user_id][-self.max_messages:]

    def get_history(self, user_id: str) -> list[dict]:
        return self._stores.get(user_id, [])

    def clear(self, user_id: str):
        self._stores.pop(user_id, None)


profile_store = UserMemoryStore()
conversation_buffer = ConversationBuffer()
