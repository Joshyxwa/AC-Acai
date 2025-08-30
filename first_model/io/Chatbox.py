import logging
from typing import Any, Dict, List, Optional

from ..database.Database import Database


class Chatbox:
    """Container for a single conversation's state and history.

    Responsibilities:
    - Hold a conv_id that identifies the conversation.
    - Load message history from the database on initialization (optional).
    - Provide getters to retrieve sorted history for the server/UI.
    - Append new messages (user/system/agent) and persist them.
    """

    def __init__(self, database: Database, conv_id: Optional[int] = None, preload: bool = True):
        self.logger = logging.getLogger(__name__ + ".Chatbox")
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            self.logger.addHandler(handler)
        self.logger.setLevel(logging.INFO)

        self._db = database
        # Ensure a conversation exists or create one via Database helper
        try:
            self.conv_id = self._db.get_conversation(conv_id)
        except Exception:
            # Fallback: trust provided conv_id if DB helper fails; caller should ensure validity
            self.conv_id = conv_id
        self.messages: List[Dict[str, Any]] = []

        if preload:
            self.reload()

    # ------------------------
    # Data accessors
    # ------------------------
    def reload(self) -> None:
        """Reload messages for this conversation from the database and sort by created_at asc."""
        if self.conv_id is None:
            self.logger.warning("reload called without a conv_id")
            self.messages = []
            return
        try:
            resp = (
                self._db.supabase
                .table("Message")
                .select("*")
                .eq("conv_id", self.conv_id)
                .order("created_at", desc=False)
                .execute()
            )
            self.messages = list(resp.data or [])
        except Exception as e:
            self.logger.exception("Failed to reload messages: %s", e)
            self.messages = []

    def get_history(self) -> List[Dict[str, Any]]:
        """Return a copy of sorted message history for this chatbox."""
        return list(self.messages)

    # ------------------------
    # Mutations
    # ------------------------
    def append_message(self, role: str, content: str, extra: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
        """Persist a message to DB and append to local history. Returns the stored row if successful."""
        if self.conv_id is None:
            self.logger.error("append_message called without a conv_id")
            return None
        payload: Dict[str, Any] = {
            "conv_id": self.conv_id,
            "type": role,
            "content": content,
        }
        if extra:
            payload.update(extra)
        try:
            resp = self._db.supabase.table("Message").insert(payload).execute()
            row = (resp.data or [None])[0]
            if row:
                self.messages.append(row)
            return row
        except Exception as e:
            self.logger.exception("Failed to append message: %s", e)
            return None

    def record_inference(self, audit: Any = None, attack: Any = None) -> Dict[str, Optional[Dict[str, Any]]]:
        """Append inference results as messages (auditor/attacker)."""
        results: Dict[str, Optional[Dict[str, Any]]] = {"audit": None, "attack": None}
        if audit is not None:
            results["audit"] = self.append_message("auditor", str(audit))
        if attack is not None:
            results["attack"] = self.append_message("attacker", str(attack))
        return results
