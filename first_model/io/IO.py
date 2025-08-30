import logging
from typing import Optional, Dict, Any, List

# Prefer package-relative imports so this works when imported as first_model.io.IO
from ..database.Database import Database
from ..model.Auditor import Auditor
from ..model.Attacker import Attacker
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

        # Agents are optional; initialize safely so missing env doesn't break the server
        self.auditor = None
        self.attacker = None
        self.law = None
        try:
            self.auditor = Auditor()
        except Exception as e:
            self.logger.warning(f"Auditor init skipped: {e}")
        try:
            self.attacker = Attacker()
        except Exception as e:
            self.logger.warning(f"Attacker init skipped: {e}")
        try:
            # Lazy import so missing optional deps (e.g., transformers) don't break server startup
            from ..model.Law import Law as _Law
            self.law = _Law()
        except Exception as e:
            self.logger.warning(f"Law init skipped: {e}")

        # Active chatboxes by conv_id
        self._chatboxes: Dict[int, Chatbox] = {}

        self.logger.info("IO initialized")

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
            agents = []
            if self.auditor is not None:
                agents.append("auditor")
            if self.attacker is not None:
                agents.append("attacker")
            if self.law is not None:
                agents.append("law")
            return self._ok({"db": has_db, "agents": agents})
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
    def list_projects(self) -> Dict[str, Any]:
        try:
            data = self.database.load_all_projects()
            return self._ok(data)
        except Exception as e:
            self.logger.exception("list_projects failed")
            return self._err(str(e))

    def get_project_with_documents(self, project_id: int) -> Dict[str, Any]:
        try:
            data = self.database.get_project_with_documents(project_id)
            return self._ok(data)
        except Exception as e:
            self.logger.exception("get_project_with_documents failed")
            return self._err(str(e))

    def load_document_with_highlighting(self, project_id: int, document_id: int) -> Dict[str, Any]:
        try:
            data = self.database.load_document_with_highlighting(project_id, document_id)
            return self._ok(data)
        except Exception as e:
            self.logger.exception("load_document_with_highlighting failed")
            return self._err(str(e))

    # ------------------------
    # Audit pipeline (Law -> Attacker -> Auditor -> DB)
    # ------------------------
    def run_audit_pipeline(self, project_id: int, max_scenarios: int = 3) -> Dict[str, Any]:
        """Run the full audit pipeline for a project.
        Steps:
        - Fetch project doc_ids
        - Use Law to retrieve relevant ent_ids
        - Use Attacker to generate scenarios (max_scenarios)
        - Create Audit row
        - For each scenario, call Auditor, create Issue, Conversation, and seed a first message

        Returns { ok, data, error } with data summarizing audit_id, issues, and conversations.
        """
        try:
            if self.database is None:
                return self._err("database is not initialized")
            # 1. Collect document ids for project
            doc_ids = self.database.load_document_ids(project_id)
            if not doc_ids:
                return self._err("no documents found for project")

            # 2. Law → ent_ids (with graceful fallback)
            def _mock_ent_ids(k: int = 3) -> List[int]:
                try:
                    # Try to read a few ent_ids from Article_Entry as a best-effort
                    rows = (
                        self.database.supabase
                        .table("Article_Entry")
                        .select("ent_id")
                        .limit(k)
                        .execute()
                    ).data or []
                    ids = [int(r.get("ent_id")) for r in rows if r.get("ent_id") is not None]
                    return ids or [1, 2, 3][:k]
                except Exception:
                    return [1, 2, 3][:k]

            ent_ids: List[int]
            if self.law is None or not hasattr(self.law, "audit"):
                self.logger.warning("Law unavailable; using mock ent_ids")
                ent_ids = _mock_ent_ids()
            else:
                ent_ids = self.law.audit(doc_ids=doc_ids)
                # If Law returns objects, attempt to map them to ent_id ints
                if ent_ids and not isinstance(ent_ids[0], int):
                    try:
                        ent_ids = [int(getattr(x, "id", x.get("id"))) for x in ent_ids]  # type: ignore[attr-defined]
                    except Exception:
                        pass

            # 3. Attacker → scenarios (with graceful fallback)
            def _mock_scenarios(max_n: int, ent_ids: List[int], prd_doc_id: int) -> List[Dict[str, Any]]:
                out: List[Dict[str, Any]] = []
                for i in range(max_n):
                    out.append({
                        "description": f"Scenario {i+1}: Potential misuse pathway referencing PRD {prd_doc_id} (Attack vector: unspecified)",
                        "potential_violations": ["General Safety", "Privacy"],
                        "jurisdictions": ["Generic"],
                        "law_citations": ent_ids[:3] or [1],
                        "rationale": "Generated by mock attacker due to unavailable LLM.",
                        "prd_spans": [],
                    })
                return out

            if self.attacker is None or not hasattr(self.attacker, "run_attack"):
                self.logger.warning("Attacker unavailable; generating mock scenarios")
                scenarios = _mock_scenarios(max_scenarios, ent_ids, doc_ids[0])
            else:
                bundle = self.attacker.run_attack(ent_ids=ent_ids, max_n=max_scenarios, prd_doc_id=doc_ids[0])
                scenarios = (bundle or {}).get("scenarios", [])
                if not scenarios:
                    self.logger.warning("Attacker returned no scenarios; falling back to mock scenarios")
                    scenarios = _mock_scenarios(max_scenarios, ent_ids, doc_ids[0])

            # 4. Create Audit
            audit_id = self.database.project_audit(project_id=project_id)

            issues_out: List[Dict[str, Any]] = []

            # 5. For each scenario, call Auditor and persist Issue/Conversation/Message
            auditor_available = self.auditor is not None and hasattr(self.auditor, "audit")
            for scenario in scenarios:
                law_used = scenario.get("law_citations", []) if isinstance(scenario, dict) else []
                if auditor_available:
                    audit_resp = self.auditor.audit(ent_ids=ent_ids, doc_ids=doc_ids, threat_scenario=scenario)
                else:
                    self.logger.warning("Auditor unavailable; generating mock audit response")
                    audit_resp = {
                        "reasoning": f"Mock reasoning for scenario: {scenario.get('description', 'N/A')}",
                        "evidence": None,  # Optional; when None, no highlights will render
                        "clarification_question": "Can you provide more details about user consent and data flows?",
                    }

                # Normalize audit response to first item dict
                first = None
                if isinstance(audit_resp, list) and audit_resp:
                    first = audit_resp[0]
                elif isinstance(audit_resp, dict):
                    first = audit_resp

                reasoning = (first or {}).get("reasoning", "")
                evidence = (first or {}).get("evidence")
                clarification_qn = (first or {}).get("clarification_question", "")
                ent_id_for_issue = int(law_used[0]) if law_used else -1

                issue_id = self.database.create_issue(
                    audit_id=audit_id,
                    issue_description=reasoning,
                    ent_id=ent_id_for_issue,
                    status="open",
                    evidence=evidence,
                    qn=clarification_qn,
                )
                conv_id = self.database.create_conversation(audit_id=audit_id, issue_id=issue_id)
                _ = self.database.send_first_message(conv_id=conv_id, role="ai", content=clarification_qn or "Please provide clarification.")

                issues_out.append({
                    "issue_id": issue_id,
                    "conv_id": conv_id,
                    "reason": reasoning,
                    "clarification_qn": clarification_qn,
                })

            return self._ok({
                "audit_id": audit_id,
                "project_id": project_id,
                "doc_ids": doc_ids,
                "ent_ids": ent_ids,
                "issues": issues_out,
                "count": len(issues_out),
            })
        except Exception as e:
            self.logger.exception("run_audit_pipeline failed")
            return self._err(str(e))

    def run_audit_pipeline_for_audit(self, audit_id: int, project_id: int, max_scenarios: int = 3) -> Dict[str, Any]:
        """Run the audit pipeline but use an existing audit_id instead of creating a new one."""
        try:
            if self.database is None:
                return self._err("database is not initialized")
            doc_ids = self.database.load_document_ids(project_id)
            if not doc_ids:
                return self._err("no documents found for project")

            # Law → ent_ids (with graceful fallback)
            def _mock_ent_ids(k: int = 3) -> List[int]:
                try:
                    rows = (
                        self.database.supabase
                        .table("Article_Entry")
                        .select("ent_id")
                        .limit(k)
                        .execute()
                    ).data or []
                    ids = [int(r.get("ent_id")) for r in rows if r.get("ent_id") is not None]
                    return ids or [1, 2, 3][:k]
                except Exception:
                    return [1, 2, 3][:k]

            ent_ids: List[int]
            if self.law is None or not hasattr(self.law, "audit"):
                self.logger.warning("Law unavailable; using mock ent_ids")
                ent_ids = _mock_ent_ids()
            else:
                ent_ids = self.law.audit(doc_ids=doc_ids)
                if ent_ids and not isinstance(ent_ids[0], int):
                    try:
                        ent_ids = [int(getattr(x, "id", x.get("id"))) for x in ent_ids]  # type: ignore[attr-defined]
                    except Exception:
                        pass

            # Attacker → scenarios (with graceful fallback)
            def _mock_scenarios(max_n: int, ent_ids: List[int], prd_doc_id: int) -> List[Dict[str, Any]]:
                out: List[Dict[str, Any]] = []
                for i in range(max_n):
                    out.append({
                        "description": f"Scenario {i+1}: Potential misuse pathway referencing PRD {prd_doc_id} (Attack vector: unspecified)",
                        "potential_violations": ["General Safety", "Privacy"],
                        "jurisdictions": ["Generic"],
                        "law_citations": ent_ids[:3] or [1],
                        "rationale": "Generated by mock attacker due to unavailable LLM.",
                        "prd_spans": [],
                    })
                return out

            if self.attacker is None or not hasattr(self.attacker, "run_attack"):
                self.logger.warning("Attacker unavailable; generating mock scenarios")
                scenarios = _mock_scenarios(max_scenarios, ent_ids, doc_ids[0])
            else:
                bundle = self.attacker.run_attack(ent_ids=ent_ids, max_n=max_scenarios, prd_doc_id=doc_ids[0])
                scenarios = (bundle or {}).get("scenarios", [])
                if not scenarios:
                    self.logger.warning("Attacker returned no scenarios; falling back to mock scenarios")
                    scenarios = _mock_scenarios(max_scenarios, ent_ids, doc_ids[0])

            issues_out: List[Dict[str, Any]] = []
            auditor_available = self.auditor is not None and hasattr(self.auditor, "audit")
            for scenario in scenarios:
                law_used = scenario.get("law_citations", []) if isinstance(scenario, dict) else []
                if auditor_available:
                    audit_resp = self.auditor.audit(ent_ids=ent_ids, doc_ids=doc_ids, threat_scenario=scenario)
                else:
                    self.logger.warning("Auditor unavailable; generating mock audit response")
                    audit_resp = {
                        "reasoning": f"Mock reasoning for scenario: {scenario.get('description', 'N/A')}",
                        "evidence": None,
                        "clarification_question": "Can you provide more details about user consent and data flows?",
                    }

                first = None
                if isinstance(audit_resp, list) and audit_resp:
                    first = audit_resp[0]
                elif isinstance(audit_resp, dict):
                    first = audit_resp

                reasoning = (first or {}).get("reasoning", "")
                evidence = (first or {}).get("evidence")
                clarification_qn = (first or {}).get("clarification_question", "")
                ent_id_for_issue = int(law_used[0]) if law_used else -1

                issue_id = self.database.create_issue(
                    audit_id=audit_id,
                    issue_description=reasoning,
                    ent_id=ent_id_for_issue,
                    status="open",
                    evidence=evidence,
                    qn=clarification_qn,
                )
                conv_id = self.database.create_conversation(audit_id=audit_id, issue_id=issue_id)
                _ = self.database.send_first_message(conv_id=conv_id, role="ai", content=clarification_qn or "Please provide clarification.")

                issues_out.append({
                    "issue_id": issue_id,
                    "conv_id": conv_id,
                    "reason": reasoning,
                    "clarification_qn": clarification_qn,
                })

            return self._ok({
                "audit_id": audit_id,
                "project_id": project_id,
                "doc_ids": doc_ids,
                "ent_ids": ent_ids,
                "issues": issues_out,
                "count": len(issues_out),
            })
        except Exception as e:
            self.logger.exception("run_audit_pipeline_for_audit failed")
            return self._err(str(e))

    def run_audit_pipeline_for_audit_and_update(self, audit_id: int, project_id: int, max_scenarios: int = 3) -> Dict[str, Any]:
        """Run audit pipeline for an existing audit and update status (in_progress -> completed/failed)."""
        try:
            # Mark in progress
            try:
                self.database.update_audit_status(audit_id, "in_progress")
            except Exception as _:
                pass
            res = self.run_audit_pipeline_for_audit(audit_id=audit_id, project_id=project_id, max_scenarios=max_scenarios)
            if res.get("ok"):
                try:
                    self.database.update_audit_status(audit_id, "completed")
                except Exception:
                    pass
            else:
                try:
                    self.database.update_audit_status(audit_id, "failed")
                except Exception:
                    pass
            return res
        except Exception as e:
            try:
                self.database.update_audit_status(audit_id, "failed")
            except Exception:
                pass
            self.logger.exception("run_audit_pipeline_for_audit_and_update failed")
            return self._err(str(e))
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