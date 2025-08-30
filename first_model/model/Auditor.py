import os
import json
import torch
from typing import List
from google import genai
from supabase import create_client, Client
from dotenv import load_dotenv
from transformers import AutoTokenizer, AutoModel
from Model import Model
import vecs
load_dotenv("../../secrets/.env.dev")

class Auditor():
    def __init__(self):
        # --- LLM and Embedding Model Setup ---
        gemini_api_key = os.environ.get("GEMINI_API_KEY")
        self.llm_client = genai.Client(
            api_key=gemini_api_key,
        )

        model_name = "nlpaueb/legal-bert-base-uncased"
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        print(f"Using device: {self.device}")
        self.tokenizer = AutoTokenizer.from_pretrained(model_name)
        self.embedding_model = AutoModel.from_pretrained(model_name).to(self.device)

        # --- Database Client Setup (Simplified) ---
        url: str = os.environ.get("SUPABASE_URL")
        key: str = os.environ.get("SUPABASE_KEY")
        ref: str = os.environ.get("SUPABASE_REF")
        password: str = os.environ.get("SUPABASE_PASSWORD")
        DB_CONNECTION = f"postgresql://postgres.{ref}:{password}@aws-1-ap-southeast-1.pooler.supabase.com:6543/postgres"
        # create vector store client
        vx = vecs.create_client(DB_CONNECTION)
        self.docs = vx.get_or_create_collection(name="Article_Entry", dimension=768)
        self.supabase: Client = create_client(url, key)

    def audit(self, threat_scenario, issues_broken):
        with open("./prompt_template/auditor_prompt.txt", "r") as file:
            prompt_template = file.read()
            file.close()
            
        with open("threat1.txt", "r") as file:
            threat_scenario = file.read()

        with open("issues1.txt", "r") as file:
            issues_broken = file.read()

    def retrieve_relevant_laws(self, law_names):
        relevant_laws = self.database.table("Law").select("*").in_("name", law_names).execute().data
        return relevant_laws