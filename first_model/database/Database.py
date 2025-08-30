import os
from dotenv import load_dotenv
from supabase import create_client

class Database():
    def __init__(self):
        load_dotenv("./secrets/.env.dev")
        self.__URL = os.environ.get("SUPABASE_URL")
        self.__KEY = os.environ.get("SUPABASE_KEY")
        self.supabase = create_client(self.__URL, self.__KEY)
    
    def save_data(self, table, data):
        response = self.supabase.table(table).insert(data).execute()
        return response

    def load_data(self, table, query, **kwargs):
        target = self.supabase.table(table).select("*").eq("id", query)
        for key, value in kwargs.items():
            target = target.eq(key, value)
        response = target.execute()
        return response
    
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

    def save_audit(self, audit_id = None, project_id = None, status = None):
        return self.save_data("Audit", {
            "audit_id": audit_id or self.get_next_id("Audit", "audit_id"),
            "created_at": self.get_current_timestamp(),
            "project_id": project_id,
            "status": status
        })

    def save_message(self, message: str | None = None, type: str | None = None, conv_id: int | None = None, created_at: str | None = None):
        """Persist a message. Prefer passing conv_id explicitly; falls back to self.conv_id if set."""
        cid = conv_id if conv_id is not None else self.conv_id
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
            "content": content,
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

    def save_audit(self, project_id, status):
        return self.save_data("Audit", {
            "audit_id": self.get_next_id("Audit", "audit_id"),
            "created_at": self.get_current_timestamp(),
            "project_id": project_id,
            "status": status,
        })
    
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

    def load_audit(self, audit_id, **kwargs):
        return self.load_data("Audit", audit_id, **kwargs)

    def load_conversation(self, conv_id, **kwargs):
        return self.load_data("Conversation", conv_id, **kwargs)

    def load_message(self, msg_id, **kwargs):
        return self.load_data("Message", msg_id, **kwargs)

    def load_article(self, article_id, **kwargs):
        return self.load_data("Article_Entry", article_id, **kwargs)

    def load_issue(self, issue_id, **kwargs):
        return self.load_data("Issue", issue_id, **kwargs)

    def load_project(self, project_id, **kwargs):
        return self.load_data("Project", project_id, **kwargs)

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