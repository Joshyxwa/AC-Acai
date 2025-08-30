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

class Database:
    def __init__(self, conv_id = None):
        load_dotenv("./secrets/.env.dev")
        self.__URL = os.environ.get("SUPABASE_URL")
        self.__KEY = os.environ.get("SUPABASE_KEY")
        self.supabase = create_client(self.__URL, self.__KEY)
    
        # self.conv_id = self.get_conversation(conv_id)
    
    def save_data(self, table, data):
        response = self.supabase.table(table).insert(data).execute()
        return response

    def load_data(self, table, **kwargs):
        target = self.supabase.table(table).select("*")
        for key, value in kwargs.items():
            target = target.eq(key, value)
        response = target.execute()
        return response.data
    
    def get_conversation(self, conv_id = None):
        if self.supabase.table("Conversation").select("*").eq("conv_id", conv_id).execute():
            return conv_id
        conv_id = self.get_next_id("Conversation", "conv_id")
        self.save_data("Conversation", {
            "conv_id": conv_id,
            "created_at": self.get_current_timestamp(),
            "audit_id": None
        })
        return conv_id

    def save_audit(self, audit_id = None, project_id = None, status = None):
        return self.save_data("Audit", {
            "audit_id": audit_id or self.get_next_id("Audit", "audit_id"),
            "created_at": self.get_current_timestamp(),
            "project_id": project_id,
            "status": status
        })

    def save_message(self, message = None, type = None):
        return self.save_data("Message", {
            "msg_id": self.get_next_id("Message", "msg_id"),
            "created_at": self.get_current_timestamp(),
            "type": type,
            "content": message,
            "conv_id": self.conv_id
        })
        
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
            evidence = issue['evidence']
            if isinstance(evidence, str):
                evidence = json.loads(evidence)
            for key, value in evidence.items():
                if str(key) == str(document_id): # only find for this current document_id 
                    highlighting = get_span_ranges(document["content"], document["content_span"], value)

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
        return self.supabase.table(table).select(id_field).order(id_field, desc=True).limit(1).execute() or minimum_value

    def get_current_timestamp(self):
        from datetime import datetime
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")
