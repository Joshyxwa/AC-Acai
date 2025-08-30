import logging
from typing import Optional, Dict, Any, List

# Prefer package-relative imports so this works when imported as first_model.io.IO
from ..database.Database import Database
from ..model.Auditor import Auditor
from ..model.Attacker import Attacker
from enum import Enum
from .Chatbox import Chatbox

class IO:
    """
    IO is the façade between the FastAPI server and the internal system
    (Database + AI agents). It provides high-level, safe, and uniform
    functions for the server to call.

    Return contract for public methods:
    - dict with keys { ok: bool, data: Any | None, error: str | None }
    - never raise on expected failures; capture and return error string
    """

    def __init__(self):
        # Logger setup
        self.logger = logging.getLogger(__name__ + ".IO")
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                "%(asctime)s | %(levelname)s | %(name)s | %(message)s"
            )
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
        self.logger.setLevel(logging.INFO)

        # Core services
        self.database = Database()
        self.auditor = Auditor(self.database)
        self.attacker = Attacker(self.database)

        self.logger.info("IO initialized with Database, Auditor, Attacker")
    # Active chatboxes by conv_id
    self._chatboxes: Dict[int, Chatbox] = {}

    def display(self, audit_response, attack_response):
        print("Audit Response:", audit_response)
        print("Attack Response:", attack_response)

    # ------------------------
    # Helpers (internal)
    # ------------------------
    def _ok(self, data: Any = None) -> Dict[str, Any]:
        return {"ok": True, "data": data, "error": None}

    def _err(self, msg: str) -> Dict[str, Any]:
        return {"ok": False, "data": None, "error": msg}

    # ------------------------
    # Health / Info
    # ------------------------
    def ping(self) -> Dict[str, Any]:
        return self._ok({"service": "io", "status": "ok"})

    def status(self) -> Dict[str, Any]:
        try:
            # Lightweight DB check (does not query network if DB object creation failed)
            has_db = self.database is not None
            return self._ok({"db": has_db, "agents": ["auditor", "attacker"]})
        except Exception as e:
            self.logger.exception("Status check failed")
            return self._err(str(e))

    # ------------------------
    # Messaging
    # ------------------------
    def get_or_create_chatbox(self, conv_id: Optional[int] = None, preload: bool = True) -> Dict[str, Any]:
        """Return a chatbox for the given conv_id, creating it if necessary."""
        try:
            if conv_id is not None and conv_id in self._chatboxes:
                return self._ok({"conv_id": conv_id, "created": False})
            cb = Chatbox(self.database, conv_id=conv_id, preload=preload)
            if cb.conv_id is None:
                return self._err("failed to create or resolve conversation id")
            self._chatboxes[cb.conv_id] = cb
            return self._ok({"conv_id": cb.conv_id, "created": True})
        except Exception as e:
            self.logger.exception("get_or_create_chatbox failed")
            return self._err(str(e))

    def get_history(self, conv_id: int, reload: bool = False) -> Dict[str, Any]:
        try:
            cb = self._chatboxes.get(conv_id)
            if not cb:
                return self._err("chatbox not found; call get_or_create_chatbox first")
            if reload:
                cb.reload()
            return self._ok({"conv_id": conv_id, "messages": cb.get_history()})
        except Exception as e:
            self.logger.exception("get_history failed")
            return self._err(str(e))

    def post_user_message(self, conv_id: int, content: str, type: Optional[str] = "user") -> Dict[str, Any]:
        """Append a user message to a chatbox and persist."""
        try:
            if not content or not content.strip():
                return self._err("message is empty")
            cb = self._chatboxes.get(conv_id)
            if not cb:
                return self._err("chatbox not found; call get_or_create_chatbox first")
            row = cb.append_message(role=type or "user", content=content)
            if row is None:
                return self._err("failed to persist message")
            return self._ok({"msg": row})
        except Exception as e:
            self.logger.exception("post_user_message failed")
            return self._err(str(e))

    def infer_and_record(self, conv_id: int, message: str) -> Dict[str, Any]:
        """Run auditor/attacker on message and record results into chatbox."""
        try:
            cb = self._chatboxes.get(conv_id)
            if not cb:
                return self._err("chatbox not found; call get_or_create_chatbox first")
            audit = self.auditor.audit(message) if hasattr(self.auditor, "audit") else None
            attack = self.attacker.attack(message) if hasattr(self.attacker, "attack") else None
            recorded = cb.record_inference(audit=audit, attack=attack)
            return self._ok({"audit": recorded.get("audit"), "attack": recorded.get("attack")})
        except Exception as e:
            self.logger.exception("infer_and_record failed")
            return self._err(str(e))

    def handle_incoming(self, conv_id: int, content: str, run_inference: bool = True) -> Dict[str, Any]:
        """End-to-end handling: append user message, optionally run agents, return results."""
        try:
            post = self.post_user_message(conv_id, content)
            if not post.get("ok"):
                return post
            if not run_inference:
                return self._ok({"posted": post.get("data")})
            infer = self.infer_and_record(conv_id, content)
            if not infer.get("ok"):
                return infer
            return self._ok({"posted": post.get("data"), "inference": infer.get("data")})
        except Exception as e:
            self.logger.exception("handle_incoming failed")
            return self._err(str(e))
    def save_message(self, message: str, type: Optional[str] = None) -> Dict[str, Any]:
        """Persist a raw message to storage."""
        try:
            if not message or not message.strip():
                return self._err("message is empty")
            result = self.database.save_message(message=message, type=type)
            return self._ok(result)
        except Exception as e:
            self.logger.exception("save_message failed")
            return self._err(str(e))

    def process_message(self, message: str) -> Dict[str, Any]:
        """Run the message through AI agents (auditor and attacker)."""
        try:
            audit_response = None
            attack_response = None
            if hasattr(self.auditor, "audit"):
                audit_response = self.auditor.audit(message)
            if hasattr(self.attacker, "attack"):
                attack_response = self.attacker.attack(message)
            data = {"audit": audit_response, "attack": attack_response}
            return self._ok(data)
        except Exception as e:
            self.logger.exception("process_message failed")
            return self._err(str(e))

    def input_message(self, message: str, type: Optional[str] = None) -> Dict[str, Any]:
        """High-level: save + process a message, return structured result.
        Backwards-compatible function; prefer chatbox flow for conversations.
        """
        try:
            save_res = self.save_message(message, type)
            if not save_res.get("ok"):
                return save_res
            proc_res = self.process_message(message)
            if not proc_res.get("ok"):
                return proc_res
            combined = {
                "saved": save_res.get("data"),
                "inference": proc_res.get("data"),
            }
            return self._ok(combined)
        except Exception as e:
            self.logger.exception("input_message failed")
            return self._err(str(e))

    def output_chatbox(self, message):
        return message
    
    def input_file(self, file: str, encoding: str = "utf-8") -> Dict[str, Any]:
        """Read a text file and process its content like a normal message."""
        try:
            with open(file, "r", encoding=encoding) as f:
                content = f.read()
            return self.input_message(content, type="file")
        except FileNotFoundError:
            return self._err("file not found")
        except Exception as e:
            self.logger.exception("input_file failed")
            return self._err(str(e))

    # ------------------------
    # Projects / Documents (thin wrappers over Database)
    # ------------------------
    def create_project(self, name: Optional[str] = None, description: Optional[str] = None, status: Optional[str] = None) -> Dict[str, Any]:
        try:
            data = self.database.save_project(name=name, description=description, status=status)
            return self._ok(data)
        except Exception as e:
            self.logger.exception("create_project failed")
            return self._err(str(e))

    def save_document(self, project_id: int, content: str, type: Optional[str] = None, version: Optional[str] = None, doc_id: Optional[int] = None) -> Dict[str, Any]:
        try:
            data = self.database.save_document(project_id=project_id, doc_id=doc_id, type=type, content=content, version=version)
            return self._ok(data)
        except Exception as e:
            self.logger.exception("save_document failed")
            return self._err(str(e))

    def list_document_ids(self, project_id: int) -> Dict[str, Any]:
        try:
            data = self.database.load_document_ids(project_id)
            return self._ok(data)
        except Exception as e:
            self.logger.exception("list_document_ids failed")
            return self._err(str(e))

    def load_project(self, project_id: int, **filters) -> Dict[str, Any]:
        try:
            data = self.database.load_project(project_id, **filters)
            return self._ok(data)
        except Exception as e:
            self.logger.exception("load_project failed")
            return self._err(str(e))

    def create_audit(self, project_id: int, status: str = "pending") -> Dict[str, Any]:
        try:
            # Support either of the DB signatures by using named args
            if "save_audit" in dir(self.database):
                data = self.database.save_audit(project_id=project_id, status=status)
            else:
                data = self.database.project_audit(project_id)
            return self._ok(data)
        except Exception as e:
            self.logger.exception("create_audit failed")
            return self._err(str(e))

    # ------------------------
    # Issues / Conversations
    # ------------------------
    def create_conversation(self, audit_id: int, issue_id: int) -> Dict[str, Any]:
        try:
            data = self.database.create_conversation(audit_id=audit_id, issue_id=issue_id)
            return self._ok(data)
        except Exception as e:
            self.logger.exception("create_conversation failed")
            return self._err(str(e))

    def send_first_message(self, conv_id: int, role: str, content: str) -> Dict[str, Any]:
        try:
            data = self.database.send_first_message(conv_id=conv_id, role=role, content=content)
            return self._ok(data)
        except Exception as e:
            self.logger.exception("send_first_message failed")
            return self._err(str(e))

    # ------------------------
    # Legal articles (definitions/documents)
    # ------------------------
    def save_law_definition(self, art_num: str, belongs_to: str, content: str, word: str, embedding: Optional[List[float]] = None) -> Dict[str, Any]:
        try:
            data = self.database.save_article_definition(art_num=art_num, belongs_to=belongs_to, content=content, word=word, embedding=embedding)
            return self._ok(data)
        except Exception as e:
            self.logger.exception("save_law_definition failed")
            return self._err(str(e))

    def save_law_document(self, art_num: str, belongs_to: str, type: str, contents: str, word: Optional[str] = None, embedding: Optional[List[float]] = None) -> Dict[str, Any]:
        try:
            data = self.database.save_article_document(art_num=art_num, belongs_to=belongs_to, type=type, contents=contents, word=word, embedding=embedding)
            return self._ok(data)
        except Exception as e:
            self.logger.exception("save_law_document failed")
            return self._err(str(e))