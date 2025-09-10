import os
import re
import json
import torch
import torch.nn.functional as F
from typing import List, Union
from google import genai
try:
    from google.api_core import exceptions as gcloud_exceptions
except Exception:
    class _Exc:
        class ServiceUnavailable(Exception):
            pass
        class ResourceExhausted(Exception):
            pass
    gcloud_exceptions = _Exc()  # fallback so except clauses work even if package missing
from supabase import create_client, Client
from dotenv import load_dotenv
from transformers import AutoTokenizer, AutoModel
# from sklearn.metrics import precision_score, recall_score, f1_score
import vecs
import pandas as pd
import itertools

load_dotenv("./secrets/.env.dev")
import time

class Law():
    def __init__(self, bill="All"):
        super().__init__()
        
        # --- LLM and Embedding Model Setup ---
        gemini_api_key = os.environ.get("GEMINI_API_KEY")
        self.llm_client = genai.Client(
            api_key=gemini_api_key,
        )

        model_name = "nlpaueb/legal-bert-base-uncased"
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
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
        self.bill = bill

    def _embed_text(self, text: Union[str, List[str]]) -> List[float]:
        """Generates embeddings for a given text or list of texts."""
        inputs = self.tokenizer(text, padding=True, truncation=True, return_tensors='pt', max_length=512).to(self.device)
        with torch.no_grad():
            outputs = self.embedding_model(**inputs)
            embeddings = outputs.last_hidden_state.mean(dim=1)
        return embeddings.cpu().numpy().tolist()
    
    def __format_scenarios_prompt(self, law_string):
        start_index = law_string.find('{')

        # Find the index of the last '}'
        end_index = law_string.rfind('}')

        # Slice the string to get only the valid JSON part
        clean_json_string = law_string[start_index : end_index + 1]
        print(clean_json_string)
        # --- END FIX ---

    def __generate_hypothetical_document(self, query: str) -> str:
        """Uses the LLM to generate a hypothetical document."""
        prompt = (
            "Generate a comprehensive, detailed legal article that would be the perfect answer to the following user query. "
            "Focus on capturing the key legal concepts, terminology, and context implied by the query.\n\n"
            f"USER QUERY: \"{query}\"\n\n"
            "HYPOTHETICAL ARTICLE:"
        )
        response = None
        for attempt in range(5):
            try:
                print(f"Attempting to generate content (Attempt {attempt + 1}/10)...")
                response = self.llm_client.models.generate_content(
                model="gemini-2.5-flash",
                contents=prompt
            )
                # If the call is successful, print a confirmation and exit the loop
                print("✅ Success! Content generated.")
                break
            
            # Catch the specific error for "service unavailable" or "resource exhausted".
            # This is better than a generic 'except Exception'.
            except Exception as e:
                print(f"⚠️ Error: {e}")
                # If this is the last attempt, print a final failure message.
                if attempt == 5 - 1:
                    print("❌ All retries failed. The server may be busy. Please try again later.")
                else:
                    # Wait for a moment before the next attempt
                    wait_time = 2 ** attempt  # This is exponential backoff
                    print(f"🔁 Server overloaded. Retrying in {wait_time} second(s)...")
                    time.sleep(wait_time)
        return response.text if response else ""

    def __vector_search(self, bill: str, embedding: List[float], top_k: int = 3) -> List[dict]:
        """Performs vector search using a Supabase RPC function."""
        if bill == "All":
            # This part was already correct, as it only has one filter condition
            index_list = self.docs.query(
                data=embedding,
                limit=top_k,
                filters={"type": {"$eq": "Law"}},
            )
        else:
            # Correctly combine multiple filters using the $and operator ✅
            index_list = self.docs.query(
                data=embedding,
                limit=top_k,
                filters={
                    "$and": [
                        {"belongs_to": {"$eq": bill}},
                        {"type": {"$eq": "Law"}}
                    ]
                }
            )
        return index_list
    
    def __fetch_document_content(self, doc_id: int) -> str:
        """Fetches the content of a single document to be audited."""
        response = self.supabase.table("Document").select("content").eq("doc_id", doc_id).single().execute()
        if response.data:
            return response.data["content"]
        else:
            raise ValueError(f"Document with ID {doc_id} not found.")

    def audit(self, bill:str, doc_ids: List[int], top_k: int = 3):
        """
        Audits multiple documents together by first synthesizing their content
        and then running the HyDE pipeline on the unified context.
        """

        # 1. Fetch the content of all documents
        document_contents = [self.__fetch_document_content(doc_id) for doc_id in doc_ids]
        
        # 2. Synthesize the contents into a single description (NEW STEP)
        synthesized_potential_law = self.__synthesize_documents(document_contents)
        
        self.__format_scenarios_prompt(synthesized_potential_law)
        # 4. Generate the hypothetical document from this unified query
        # hypothetical_doc = self.__generate_hypothetical_document(synthesized_potential_law)

        # # 5. Embed the hypothetical document
        # query_embedding = self._embed_text(hypothetical_doc)[0]

        # # 6. Search for relevant articles
        # relevant_articles = self.__vector_search(embedding=query_embedding, top_k=top_k, bill=bill)
        # return relevant_articles
    
    def __synthesize_documents(self, contents: List[str]) -> str:
        """
        Uses the LLM to read multiple document contents and synthesize them
        into a single, coherent description.
        """
        
        # Prepare the documents for the prompt, clearly separating them
        formatted_docs = ""
        for i, content in enumerate(contents):
            formatted_docs += f"--- DOCUMENT {i+1} ---\n{content}\n\n"

        prompt = self.__format_document_prompt(formatted_docs)
        # prompt = (
        #     "You are a legal tech analyst. Read the following documents, which describe different aspects of a single product feature or situation. "
        #     "Your task is to synthesize them into one cohesive description. Identify the core functionality, the data involved, and the user interactions. "
        #     "The goal is to create a single, clear context that can be used to find relevant legal articles.\n\n"
        #     f"{formatted_docs}"
        #     "--- SYNTHESIZED DESCRIPTION ---"
        # )
        response = None
        for attempt in range(10):
            try:
                print(f"Attempting to generate content (Attempt {attempt + 1}/10)...")
                response = self.llm_client.models.generate_content(
                    model="gemini-2.5-flash",
                    contents=prompt
                )
                # If the call is successful, print a confirmation and exit the loop
                print("✅ Success! Content generated.")
                break
            
            # Catch the specific error for service overload; fall back to a broad catch if types unavailable
            except Exception as e:
                print(f"⚠️ Error: {e}")
                # If this is the last attempt, print a final failure message.
                if attempt == 5 - 1:
                    print("❌ All retries failed. The server may be busy. Please try again later.")
                else:
                    # Wait for a moment before the next attempt
                    wait_time = 2 ** attempt  # This is exponential backoff
                    print(f"🔁 Server overloaded. Retrying in {wait_time} second(s)...")
                    time.sleep(wait_time)
        with open("demofile.txt", "w") as f:
            f.write(response.text) 
        f.close()
        return response.text

    def __format_document_prompt(self, formatted_docs: str,) -> str:
        """Formats the follow-up prompt for the Adjudicator agent."""
        with open("first_model/model/prompt_template/potential_scenario_prompt.txt", "r") as file:
            prompt_template = file.read()


        final_prompt = prompt_template.format(
            formatted_docs=formatted_docs,
        )
        return final_prompt

    def evaluate(self):
        def find_best_matching_article(name, threshold=0.70, k=3):
            # Perform semantic search on article collection
            emb_name = self._embed_text(name)

            results = self.docs.query(
                data=[emb_name],   # your raw article name
                limit=k,       # how many matches to return
                include_value=True,   # include the stored article name
                include_metadata=True # include article metadata (id, art_num, belongs_to)
            )

            # results is a list of [(id, score, value, metadata), ...]
            best_match = results[0][0]
            best_score = results[0][1]

            if best_score >= threshold:
                return best_match
            return None


        def extract_ground_truth_ids(sample_output):
            match = re.search(r"Relevant law\(s\):\s*(.*?)\s*(?:—|$)", sample_output)
            if not match:
                return []
            
            raw_list = match.group(1)
            names = [a.strip() for a in raw_list.split(",")]

            ids = []
            for name in names:
                matched_id = find_best_matching_article(name)
                if matched_id:
                    ids.append(matched_id)
            return ids

        def evaluate_single_document(document_text, sample_output):
            expected_ids = set(extract_ground_truth_ids(sample_output))
    
            # Predicted IDs from audit agent
            predicted_ids = set(self.audit(document_text))

            # Build label space: union of all IDs that appear in either prediction or ground truth
            all_ids = list(expected_ids | predicted_ids)

            # Create binary labels for each article in label space
            y_true = [1 if i in expected_ids else 0 for i in all_ids]
            y_pred = [1 if i in predicted_ids else 0 for i in all_ids]

            # Calculate metrics using sklearn
            precision = precision_score(y_true, y_pred, zero_division=0)
            recall = recall_score(y_true, y_pred, zero_division=0)
            f1 = f1_score(y_true, y_pred, zero_division=0)

            return {
                "expected_ids": list(expected_ids),
                "predicted_ids": list(predicted_ids),
                "precision": precision,
                "recall": recall,
                "f1": f1
            }



        df = pd.read_csv("standata.csv")
        row = df.iloc[59]
        document_text = str(row["feature_name"]) + " " + str(row["feature_description"])

        # Evaluate just that one row
        result = evaluate_single_document(document_text, row["sample_output"])
        print("Single Row Evaluation:")
        print(result)

    def eval_hyde(self, doc_ids: List[int], num):
        def compute_total_similarity(embeddings: list[list[float]]) -> float:
            """
            Computes the overall similarity of a list of embeddings using cosine similarity.
            Returns the average similarity as a percentage (0-100).

            Args:
                embeddings (list[list[float]]): List of embeddings, each embedding is a list of floats.

            Returns:
                float: Average similarity percentage across all unique embedding pairs.
            """
            # Convert list to tensor
            embeddings_tensor = torch.tensor(embeddings, dtype=torch.float32)

            # Normalize embeddings to unit vectors
            embeddings_tensor = F.normalize(embeddings_tensor, p=2, dim=1)

            # Compute cosine similarity matrix
            similarity_matrix = torch.matmul(embeddings_tensor, embeddings_tensor.T)

            # Extract upper-triangle values (unique pairs only, no duplicates, no self-comparisons)
            n = similarity_matrix.shape[0]
            upper_tri_indices = torch.triu_indices(n, n, offset=1)
            similarities = similarity_matrix[upper_tri_indices[0], upper_tri_indices[1]]

            # Convert to percentage [0,100]
            total_similarity_percentage = ((similarities.mean().item() + 1) / 2) * 100

            return total_similarity_percentage
        
        document_contents = [self.__fetch_document_content(doc_id) for doc_id in doc_ids]

        hydes = []
        for i in range(num):
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
            hydes.append(query_embedding)

        similarity = compute_total_similarity(hydes)
        print(f"Total similarity between different hyde documents: {similarity:.2f}%")
        

if __name__ == "__main__":
    print("--- Initializing Law ---")
    law = Law()

    # --- Provide the list of document IDs to check TOGETHER ---
    # These documents will be read and analyzed as a single unit.
    combined_document_ids = [1, 2] 

    try:
        # Call the new combined audit method
        # final_results = law.audit(doc_ids=combined_document_ids, bill="All")
        law.audit(doc_ids=combined_document_ids, bill="All")
        
        print("\n\n--- FINAL COMBINED AUDIT RESULTS ---")
        print(final_results)

        # print("--- Evaluation document similarity ---")
        # law.eval_hyde(doc_ids=combined_document_ids, num=10)
        #print("--- Evaluating agent against synthatic data ---")
        #auditor.evaluate()
        
    except Exception as e:
        print(f"\n\n--- ❌ AN UNEXPECTED ERROR OCCURRED ---")
        print(f"Error Type: {type(e).__name__}")
        print(f"Error Details: {e}")

