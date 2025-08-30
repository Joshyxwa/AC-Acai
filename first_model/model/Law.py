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
        super().__init__()
        
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

    def _embed_text(self, text: str or List[str]) -> List[float]:
        """Generates embeddings for a given text or list of texts."""
        inputs = self.tokenizer(text, padding=True, truncation=True, return_tensors='pt', max_length=512).to(self.device)
        with torch.no_grad():
            outputs = self.embedding_model(**inputs)
            embeddings = outputs.last_hidden_state.mean(dim=1)
        print(embeddings.cpu().numpy().tolist())
        return embeddings.cpu().numpy().tolist()

    def __generate_hypothetical_document(self, query: str) -> str:
        """Uses the LLM to generate a hypothetical document."""
        prompt = (
            "Generate a comprehensive, detailed legal article that would be the perfect answer to the following user query. "
            "Focus on capturing the key legal concepts, terminology, and context implied by the query.\n\n"
            f"USER QUERY: \"{query}\"\n\n"
            "HYPOTHETICAL ARTICLE:"
        )
        print("\n--- Generating Hypothetical Document ---")
        response = self.llm_client.models.generate_content(model="gemini-2.5-flash", contents=prompt)
        print("--- Generation Complete ---")
        return response.text

    def __vector_search(self, embedding: List[float], top_k: int = 3) -> List[dict]:
        """Performs vector search using a Supabase RPC function."""
        print("\n--- Performing Vector Search in Supabase ---")
        index_list = self.docs.query(
            data=embedding,              # required
            limit=3,                         # number of records to return
            # filters={"year": {"$eq": 2012}}, # metadata filters
        )
        return index_list
    
    def __fetch_document_content(self, doc_id: int) -> str:
        """Fetches the content of a single document to be audited."""
        response = self.supabase.table("Document").select("content").eq("doc_id", doc_id).single().execute()
        if response.data:
            return response.data["content"]
        else:
            raise ValueError(f"Document with ID {doc_id} not found.")

    def audit(self, doc_ids: List[int], top_k: int = 3):
        """
        Audits multiple documents together by first synthesizing their content
        and then running the HyDE pipeline on the unified context.
        """
        print(f"\n🚀 Starting combined audit for document IDs: {doc_ids}")
        
        # 1. Fetch the content of all documents
        document_contents = [self.__fetch_document_content(doc_id) for doc_id in doc_ids]
        
        # 2. Synthesize the contents into a single description (NEW STEP)
        synthesized_context = self.__synthesize_documents(document_contents)
        print(f"\nSynthesized Context: \"{synthesized_context[:200]}...\"")
        
        # 3. Create the initial query from the synthesized context
        initial_query = (
            f"Are any of the legal articles relevant to the feature described in the following synthesized summary: {synthesized_context} "
            "If so, which articles?"
        )
        
        # 4. Generate the hypothetical document from this unified query
        hypothetical_doc = self.__generate_hypothetical_document(initial_query)
        print(f"\nHypothetical Doc: \"{hypothetical_doc[:150]}...\"")

        # 5. Embed the hypothetical document
        query_embedding = self._embed_text(hypothetical_doc)[0]

        # 6. Search for relevant articles
        relevant_articles = self.__vector_search(embedding=query_embedding, top_k=top_k)

        print("\n✅ Combined audit complete.")
        return relevant_articles
    
    def __synthesize_documents(self, contents: List[str]) -> str:
        """
        Uses the LLM to read multiple document contents and synthesize them
        into a single, coherent description.
        """
        print("\n--- 🧠 Synthesizing content from multiple documents ---")
        
        # Prepare the documents for the prompt, clearly separating them
        formatted_docs = ""
        for i, content in enumerate(contents):
            formatted_docs += f"--- DOCUMENT {i+1} ---\n{content}\n\n"

        prompt = (
            "You are a legal tech analyst. Read the following documents, which describe different aspects of a single product feature or situation. "
            "Your task is to synthesize them into one cohesive description. Identify the core functionality, the data involved, and the user interactions. "
            "The goal is to create a single, clear context that can be used to find relevant legal articles.\n\n"
            f"{formatted_docs}"
            "--- SYNTHESIZED DESCRIPTION ---"
        )
        
        response = self.llm_client.models.generate_content(model="gemini-2.5-flash", contents=prompt)
        print("--- Synthesis Complete ---")
        return response.text
    
# if __name__ == "__main__":
#     print("--- Initializing Auditor ---")
#     auditor = Auditor()
    
#     # --- Provide the list of document IDs to check TOGETHER ---
#     # These documents will be read and analyzed as a single unit.
#     combined_document_ids = [1, 2] 
    
#     try:
#         # Call the new combined audit method
#         final_results = auditor.audit(doc_ids=combined_document_ids)
        
#         print("\n\n--- FINAL COMBINED AUDIT RESULTS ---")
#         print(final_results)
        
#     except Exception as e:
#         print(f"\n\n--- ❌ AN UNEXPECTED ERROR OCCURRED ---")
#         print(f"Error Type: {type(e).__name__}")
#         print(f"Error Details: {e}")