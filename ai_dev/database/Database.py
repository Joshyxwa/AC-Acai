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
            "msg_id": self.get_next_id("Message", "msg_id"),
            "created_at": self.get_current_timestamp(),
            "content": message
        })
        
    def get_next_id(self, table, id):
        response = self.supabase.table(table).select(id).order(id, desc=True).limit(1).execute()
        if response.data:
            return response.data[0][id] + 1
        return 1
    
    def get_current_timestamp(self):
        from datetime import datetime
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")
