import os
import json
import torch
import time
from typing import List, Optional
from anthropic import Anthropic
from supabase import create_client, Client
from dotenv import load_dotenv
import vecs
load_dotenv("./secrets/.env.dev")

class Auditor():
    def __init__(self):
        # --- LLM and Embedding Model Setup ---
        anthropic_key = os.environ.get("ANTHROPIC_API_KEY")
        self.llm_client = Anthropic(
            api_key=anthropic_key,
        )

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

    def audit(self, feature_description, ent_ids: List[int], threat_scenario) -> str:
        """Main method to audit a threat scenario against specified legal articles."""
        article_contents = [self.__fetch_article_entry_content(ent_id) for ent_id in ent_ids]
        prompt = self.format_prompt( article_contents,threat_scenario)
        print("\n--- Auditing with LLM ---")
        response = self.__llm_audit(prompt)
        return response
    
    def __fetch_article_entry_content(self, ent_id: int) -> str:
        """Fetches the content of a single document to be audited."""
        response = self.supabase.table("Article_Entry").select("contents").eq("ent_id", ent_id).single().execute()
        if response.data:
            return {"ent_id": ent_id, "content":response.data["contents"]}
        else:
            raise ValueError(f"Article with ID {ent_id} not found.")
        
    
    def format_prompt(self, article_contents: List[str], threat_scenario) -> str:
        """Formats the prompt for the LLM using the threat scenario and article contents."""
        with open("first_model/model/prompt_template/auditor_prompt.txt", "r") as file:
            prompt_template = file.read()
            file.close()

        # prd_dict, tdd_dict = self.__fetch_document_content(doc_ids)
        # prd_content, tdd_content = prd_dict["content_span"], tdd_dict["content_span"]
        
        article_contents_str = ""
        for article in article_contents:
            article_contents_str+= f"Article ID: {article['ent_id']}\nContent: {article['content']}\n\n"
        final_prompt = prompt_template.format(
            THREAT_SCENARIO=threat_scenario,
            POTENTIAL_LAW_BROKEN=article_contents_str
        )
        return final_prompt
    
    def __fetch_document_content(self, doc_ids: List[int]) -> str:
        """Fetches the content of a single document to be audited."""
        prd_dict, tdd_dict = None, None
        for doc_id in doc_ids:
            response = self.supabase.table("Document").select("content_span", "type").eq("doc_id", doc_id).single().execute()
            doc_type = response.data["type"]
            if doc_type == "PRD":
                prd_dict = {"doc_id": doc_id, "doc_type": doc_type, "content_span": response.data["content_span"]}
            if doc_type == "TDD":
                tdd_dict = {"doc_id": doc_id, "doc_type": doc_type, "content_span": response.data["content_span"]}
        if prd_dict is None or tdd_dict is None:
            raise ValueError("Expected one PRD and one TDD document in doc_ids")
        return prd_dict, tdd_dict
    
    def __llm_audit(self, prompt: str):
        last_err = None
        for attempt in range(5):
            try:
                response = self.llm_client.messages.create(
                    model="claude-sonnet-4-20250514",
                    max_tokens=4000,
                    messages=[{"role": "user", "content": prompt}],
                )
                # basic sanity checks
                if not response.content or not getattr(response.content[0], "text", "").strip():
                    raise RuntimeError("Empty response from LLM.")

                response_object = json.loads(response.content[0].text)
                print("--- Audit Complete ---")
                return response_object

            except Exception as e:
                last_err = e
                # simple exponential backoff: 1, 2, 4, 8, 16s
                sleep_s = 2 ** attempt
                print(f"⚠️ LLM audit attempt {attempt+1}/5 failed: {e}. Retrying in {sleep_s}s...")
                time.sleep(sleep_s)
    
# if __name__ == "__main__":

#     print("--- Initializing Auditor Test Case ---")
#     auditor = Auditor()
    
#     # --- DEFINE YOUR TEST INPUTS HERE ---
#     # These should be REAL IDs from your Supabase tables.
#     # The list should contain one PRD and one TDD document ID.
#     document_ids_to_test = [1, 2] 
    
#     # A list of legal article IDs to check against.
#     article_ids_to_test = [101, 102] 
    
#     try:
#         print(f"\n--- Starting test run ---")
#         # Call the main audit method
#         analysis_result = auditor.audit(
#             doc_ids=document_ids_to_test,
#             ent_ids=article_ids_to_test
#         )
        
#         print("\n\n--- ✅ FINAL ANALYSIS RESULT ---")
#         print(analysis_result)
        
#     except Exception as e:
#         print(f"\n\n--- ❌ AN ERROR OCCURRED ---")
#         print(f"Error Type: {type(e).__name__}")
#         print(f"Error Details: {e}")