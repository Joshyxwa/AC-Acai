import os
from dotenv import load_dotenv
from supabase import create_client
import json
import re

def get_span_ranges(content: str, content_span: str, target_spans: list[str]):
    # Extract span_id -> inner text
    span_pattern = re.compile(r"<(span\d+)>(.*?)</\1>", re.DOTALL)
    matches = span_pattern.findall(content_span)
    span_map = {span_id: inner_text for span_id, inner_text in matches}

    results = []
    for span_id in target_spans:
        inner = span_map.get(span_id)
        if inner:
            start = content.find(inner)
            if start != -1:
                end = start + len(inner)
                results.append({"start": start, "end": end})
    return results

class Database():
    def __init__(self):
        load_dotenv("./secrets/.env.dev")
        self.__URL = os.environ.get("SUPABASE_URL")
        self.__KEY = os.environ.get("SUPABASE_KEY")
        self.supabase = create_client(self.__URL, self.__KEY)
    
    def save_data(self, table, data):
        response = self.supabase.table(table).insert(data).execute()
        return response

    def load_data(self, table, **kwargs):
        target = self.supabase.table(table).select("*")
        for key, value in kwargs.items():
            target = target.eq(key, value)
        response = target.execute()
        return response.data
    
    def get_conversation(self, conv_id: int | None = None) -> int:
        """Resolve an existing conversation id or create a new conversation row.
        If conv_id is provided but not found, create it.
        Returns the resolved/created conv_id.
        """
        try:
            if conv_id is not None:
                resp = (
                    self.supabase.table("Conversation").select("conv_id").eq("conv_id", conv_id).limit(1).execute()
                )
                if resp.data:
                    return conv_id
                # Not found: create with provided conv_id
                self.save_data("Conversation", {
                    "conv_id": conv_id,
                    "created_at": self.get_current_timestamp(),
                    "audit_id": None
                })
                return conv_id
            # No conv_id: create new
            new_id = self.get_next_id("Conversation", "conv_id")
            self.save_data("Conversation", {
                "conv_id": new_id,
                "created_at": self.get_current_timestamp(),
                "audit_id": None
            })
            return new_id
        except Exception:
            # Best-effort fallback
            return conv_id if conv_id is not None else 1

    def save_audit(self, project_id: int, status: str, audit_id: int | None = None):
        """Create an Audit row with optional explicit audit_id."""
        return self.save_data("Audit", {
            "audit_id": audit_id or self.get_next_id("Audit", "audit_id"),
            "created_at": self.get_current_timestamp(),
            "project_id": project_id,
            "status": status
        })

    def save_message(self, message: str | None = None, type: str | None = None, conv_id: int | None = None, created_at: str | None = None):
        """Persist a message. If conv_id is not provided, create/resolve a conversation id automatically."""
        cid = conv_id
        if cid is None:
            # Try to use an existing attribute if set, else create a new conversation id
            cid = getattr(self, "conv_id", None)
            if cid is None:
                cid = self.get_conversation(None)
        payload = {
            "msg_id": self.get_next_id("Message", "msg_id"),
            "created_at": created_at or self.get_current_timestamp(),
            "type": type,
            "content": message,
            "conv_id": cid,
        }
        return self.save_data("Message", payload)
        
    def save_issue(self, audit_id, issue_id = None, issue_description = None, ent_id = None, status = None):
        return self.save_data("Issue", {
            "issue_id": issue_id or self.get_next_id("Issue", "issue_id"),
            "created_at": self.get_current_timestamp(),
            "audit_id": audit_id,
            "issue_description": issue_description,
            "ent_id": ent_id,
            "status": status
        })
        
    def save_article_definition(self, art_num, belongs_to, content, word, embedding = None):
        return self.save_data("Article_Entry", {
            "ent_id": self.get_next_id("Article_Entry", "ent_id"),
            # Keep 'contents' for consistency with other codepaths
            "contents": content,
            "word": word,
            "art_num": art_num,
            "belongs_to": belongs_to,
            "embedding": embedding,
            "type": "Definition"
        })

    def save_article_document(self, art_num, belongs_to, type, contents, word = None, embedding = None):
        if type == "Definition":
            return self.save_article_definition(art_num, belongs_to, contents, word, embedding) if word else None
        return self.save_data("Article_Entry", {
            "ent_id": self.get_next_id("Article_Entry", "ent_id"),
            "art_num": art_num,
            "type": type,
            "belongs_to": belongs_to,
            "contents": contents,
            "word": word,
            "embedding": embedding
        })

    def update_audit_status(self, audit_id: int, status: str):
        """Update the status of an existing audit row."""
        return self.supabase.table("Audit").update({"status": status}).eq("audit_id", audit_id).execute()
    
    def save_document(self, project_id, doc_id = None, type = None, content = None, version = None):
        return self.save_data("Document", {
            "doc_id": doc_id or self.get_next_id("Document", "doc_id"),
            "created_at": self.get_current_timestamp(),
            "type": type,
            "content": content,
            "version": version,
            "project_id": project_id
        })
        
    def save_project(self, project_id = None, status = None, description = None, name = None):
        return self.save_data("Project", {
            "project_id": project_id or self.get_next_id("Project", "project_id"),
            "created_at": self.get_current_timestamp(),
            "status": status,
            "description": description,
            "name": name
        })

    def get_audit(self, audit_id: int):
        resp = (
            self.supabase
            .table("Audit")
            .select("*")
            .eq("audit_id", audit_id)
            .single()
            .execute()
        )
        return resp.data

    def load_conversation(self, conv_id, **kwargs):
        return self.load_data("Conversation", conv_id, **kwargs)

    def load_message(self, msg_id, **kwargs):
        return self.load_data("Message", msg_id, **kwargs)

    def load_article(self, article_id, **kwargs):
        return self.load_data("Article_Entry", article_id, **kwargs)

    def load_issue(self, issue_id, **kwargs):
        return self.load_data("Issue", issue_id, **kwargs)

    def get_project_with_documents(self, project_id: int):
        proj = (
            self.supabase
            .table("Project")
            .select("project_id, name")
            .eq("project_id", project_id)
            .single()
            .execute()
        )

        if not proj.data: return None

        docs = (
            self.supabase
            .table("Document")
            .select("*")
            .eq("project_id", project_id)
            .order("doc_id")
            .execute()
        ).data

        # 4. Construct the response
        result = {
            "id": str(proj.data["project_id"]),
            "title": proj.data["name"],
            "documents": docs
        }
        return result

    def load_document_with_highlighting(self, project_id, document_id):
        document = (
            self.supabase
            .table("Document")
            .select("*")
            .eq("project_id", project_id)
            .eq("doc_id", document_id)
            .single()
            .execute()
        ).data

        if not document:
            return None

        audits = (
            self.supabase
            .table("Audit")
            .select("audit_id")
            .eq("project_id", project_id)
            .execute()
        ).data

        issues = []
        highlights = []

        for audit in audits:
            issue_details = (
                self.supabase
                .table("Issue")
                .select("*")
                .eq("audit_id", audit["audit_id"])
                .execute()
            ).data
            if issue_details:
                issues.extend(issue_details)

        for issue in issues: 
            evidence = issue.get('evidence')
            if not evidence:
                continue
            if isinstance(evidence, str):
                evidence = json.loads(evidence)
            for key, value in evidence.items():
                if str(key) == str(document_id): # only find for this current document_id 
                    content = document.get("content") or ""
                    content_span = document.get("content_span") or ""
                    highlighting = get_span_ranges(content, content_span, value)

                    conv = (
                        self.supabase
                        .table("Conversation")
                        .select("*")
                        .eq("issue_id", issue["issue_id"])
                        .execute()
                    ).data

                    final_messages = []

                    if conv:
                        conv_id = conv[0]['conv_id']

                        messages = (
                            self.supabase
                            .table("Message")
                            .select("*")
                            .eq("conv_id", conv_id)
                            .execute()
                        ).data

                        for message in messages:
                            final_messages.append({
                                "id": message["msg_id"],
                                "author": "GeoCompliance AI" if message["type"] == "ai" else "User",
                                "content": message["content"],
                                "type": "system" if message["type"] == "ai" else "user",
                                "timestamp": message["created_at"]
                            })

                    highlight = {
                        "id": issue["issue_id"],
                        "highlighting": highlighting,
                        "reason": issue["issue_description"],
                        "clarification_qn": issue["clarification_qn"],
                        "comments": final_messages
                    }

                    if final_messages:
                        highlights.append(highlight)

        return {
            # "title": document["title"],
            "title": "DOCUMENT",
            "content": document["content"],
            "highlights": highlights
        }

    def load_all_projects(self):
        return self.load_data("Project")

    def get_next_id(self, table, id_field, minimum_value = 1):
        resp = self.supabase.table(table).select(id_field).order(id_field, desc=True).limit(1).execute()
        try:
            if resp and getattr(resp, "data", None):
                latest = resp.data[0].get(id_field)
                if isinstance(latest, int):
                    return latest + 1
        except Exception:
            pass
        return minimum_value

    def add_message_for_issue(self, issue_id: int, content: str, author_type: str = "user"):
        # Find (or validate) the conversation for this issue
        conv_rows = (
            self.supabase
            .table("Conversation")
            .select("conv_id")
            .eq("issue_id", issue_id)
            .limit(1)
            .execute()
        ).data or []

        if not conv_rows:
            raise ValueError(f"No conversation found for issue_id={issue_id}")

        conv_id = conv_rows[0]["conv_id"]

        # Insert new message
        created_at = self.get_current_timestamp()
        insert_payload = {
            "created_at": created_at,   # or omit if DB default handles it
            "type": author_type,        # "system" or "user"
            "content": content,
            "conv_id": conv_id,
        }

        ins = (
            self.supabase
            .table("Message")
            .insert(insert_payload)
            .execute()
        )
        return ins.data[0] if ins.data else None

    # 2) Add a message as a reply to an existing message (same conversation)
    def add_message_reply(self, reply_to_msg_id: int, content: str, author_type: str = "user"):
        # Look up the conversation of the original message
        base_msg_rows = (
            self.supabase
            .table("Message")
            .select("conv_id")
            .eq("msg_id", reply_to_msg_id)
            .limit(1)
            .execute()
        ).data or []

        if not base_msg_rows:
            raise ValueError(f"Base message not found: msg_id={reply_to_msg_id}")

        conv_id = base_msg_rows[0]["conv_id"]

        created_at = self.get_current_timestamp()
        insert_payload = {
            "created_at": created_at,
            "type": author_type,   # "ai" or "user"
            "content": content,
            "conv_id": conv_id,
        }

        ins = (
            self.supabase
            .table("Message")
            .insert(insert_payload)
            .execute()
        )
        return ins.data[0] if ins.data else None

    def get_current_timestamp(self):
        from datetime import datetime
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    def load_document_ids(self, project_id: int):
        print(project_id)
        target = self.supabase.table("Document").select("doc_id").eq("project_id", project_id)
        response = target.execute()
        doc_ids = [row['doc_id'] for row in response.data]
        return doc_ids

    def load_messages_for_conversation(self, conv_id: int):
        target = (
            self.supabase.table("Message")
            .select("*")
            .eq("conv_id", conv_id)
            .order("created_at", desc=False)
        )
        response = target.execute()
        return response.data
    
    def project_audit(self, project_id: int):
        response = self.supabase.table("Audit").insert({"project_id": project_id, "status": "in_progess"}).execute()
        print(response.data)
        return response.data[0]["audit_id"]
    
    def create_issue(self, audit_id: int, issue_description: str, ent_id: int, status: str = "open", evidence: dict = None, qn: str = None):
        response = self.supabase.table("Issue").insert({
            "audit_id": audit_id,
            "issue_description": issue_description,
            "ent_id": ent_id,
            "status": status,
            "evidence": evidence,
            "clarification_qn": qn
        }).execute()
        return response.data[0]["issue_id"]

    def create_conversation(self, audit_id: int, issue_id: int):
        response = self.supabase.table("Conversation").insert({
            "audit_id": audit_id,
            "issue_id": issue_id
        }).execute()
        return response.data[0]["conv_id"]
    
    def send_first_message(self, conv_id: int, role: str, content: str):
        response = self.supabase.table("Message").insert({
            "conv_id": conv_id,
            "type": role,
            "content": content,
            "created_at": self.get_current_timestamp(),
        }).execute()
        return response.data[0]["msg_id"]