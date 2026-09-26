import json
import time
from streamlit_local_storage import LocalStorage


class HistoryStore:
    """Wraps browser localStorage persistence for the conversation history.

    All localStorage read/write quirks (timing, JSON encoding, key naming)
    are isolated here so the rest of the app only deals with plain Python
    lists/dicts.
    """

    STORAGE_KEY = "chat_history"

    def __init__(self):
        self.local_storage = LocalStorage()

    def load(self) -> list:
        """Load the history list from localStorage. Returns [] if empty/missing."""
        try:
            all_items = self.local_storage.getAll()
            stored = all_items.get(self.STORAGE_KEY) if all_items else None
            history = json.loads(stored) if stored else []
            print(f"[HistoryStore] Loaded {len(history)} entries from localStorage")
            return history
        except Exception as e:
            print(f"[HistoryStore] Failed to load history: {e}")
            return []

    def save(self, history: list) -> None:
        """Persist the given history list to localStorage."""
        try:
            self.local_storage.setItem(
                self.STORAGE_KEY,
                json.dumps(history),
                key="save_history_item",
            )
            print(f"[HistoryStore] Saved {len(history)} entries to localStorage")
        except Exception as e:
            print(f"[HistoryStore] Failed to save history: {e}")

    def upsert_conversation(self, history: list, conversation_id: str, title: str, conversation: list) -> list:
        """Add a new conversation entry, or update an existing one by id.
        Returns the updated history list (also mutates in place).
        """
        for entry in history:
            if entry["id"] == conversation_id:
                entry["conversation"] = conversation
                entry["timestamp"] = time.strftime("%Y-%m-%d %H:%M")
                return history

        history.append({
            "id": conversation_id,
            "title": title,
            "timestamp": time.strftime("%Y-%m-%d %H:%M"),
            "conversation": conversation,
        })
        return history

    def delete_entry(self, history: list, entry_id: str) -> list:
        """Remove an entry by id. Returns the filtered list."""
        return [h for h in history if h["id"] != entry_id]