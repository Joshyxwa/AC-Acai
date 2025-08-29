import os
from dotenv import load_dotenv
from supabase import create_client

class Database:
    def __init__(self):
        load_dotenv("./secrets/.env.dev")
        self.__URL = os.environ.get("SUPABASE_URL")
        self.__KEY = os.environ.get("SUPABASE_KEY")
        self.supabase = create_client(self.__URL, self.__KEY)

    def save_data(self, table, data):
        response = self.supabase.table(table).insert(data).execute()
        return response

    def load_data(self, table, query):
        response = self.supabase.table(table).select("*").eq("id", query).execute()
        return response

    def save_message(self, message):
        return self.save_data("Message", {
            "msg_id": self.supabase.table("Message").select("id").order("id", desc=True).limit(1).execute() or 1,
            "created_at": self.get_current_timestamp(),
            "content": message
        })
        
    def save_article_definition(self, art_num, belongs_to, embedding, content, word):
        return self.save_data("Article_Entry", {
            "ent_id": self.supabase.table("Article_Entry").select("id").order("id", desc=True).limit(1).execute() or 1,
            "content": content,
            "word": word,
            "art_num": art_num,
            "belongs_to": belongs_to,
            "embedding": embedding,
            "type": "Definition"
        })
        
    def save_article_document(self, art_num, belongs_to, embedding, type, content, word = None):
        if type == "Definition":
            return self.save_article_definition(art_num, belongs_to, embedding, content, word) if word else None
        return self.save_data("Article_Entry", {
            "ent_id": self.supabase.table("Article_Entry").select("ent_id").order("ent_id", desc=True).limit(1).execute() or 1,
            "content": content,
            "word": word,
            "art_num": art_num,
            "belongs_to": belongs_to,
            "embedding": embedding,
            "type": type
        })
    
    def get_current_timestamp(self):
        from datetime import datetime
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")
