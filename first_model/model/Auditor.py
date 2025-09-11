import os
import json
import torch
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

    def audit(self, ent_ids: List[int], doc_ids: List[int], threat_scenario) -> str:
        """Main method to audit a threat scenario against specified legal articles."""
        article_contents = [self.__fetch_article_entry_content(ent_id) for ent_id in ent_ids]
        prompt = self.format_prompt( article_contents, doc_ids, threat_scenario)
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
        
    
    def format_prompt(self, article_contents: List[str], doc_ids: List[int], threat_scenario) -> str:
        """Formats the prompt for the LLM using the threat scenario and article contents."""
        with open("first_model/model/prompt_template/auditor_prompt.txt", "r") as file:
            prompt_template = file.read()
            file.close()

        prd_dict, tdd_dict = self.__fetch_document_content(doc_ids)
        prd_content, tdd_content = prd_dict["content_span"], tdd_dict["content_span"]
        
        article_contents_str = ""
        for article in article_contents:
            article_contents_str+= f"Article ID: {article['ent_id']}\nContent: {article['content']}\n\n"
        final_prompt = prompt_template.format(
            PRD_CONTENT=prd_content,
            TDD_CONTENT=tdd_content,
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
    
    def __llm_audit(self, prompt: str) -> str:
        response = self.llm_client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=4000,
            messages=[
                {"role": "user", "content": prompt}
            ]
        )
        print("--- Audit Complete ---")
        response_object = json.loads(response.content[0].text)
        return response_object
    
if __name__ == "__main__":

    print("--- Initializing Auditor Test Case ---")
    auditor = Auditor()
    
    # --- DEFINE YOUR TEST INPUTS HERE ---
    # These should be REAL IDs from your Supabase tables.
    # The list should contain one PRD and one TDD document ID.
    document_ids_to_test = [7, 8] 
    
    # A list of legal article IDs to check against.
    article_ids_to_test = [6, 9, 11, 278, 31, 32, 35, 51, 57, 58, 59, 60, 62, 63, 191, 67, 69, 358, 360] 

    threat_scenario = """
    [{'description': "A malicious actor exploits the OAuth 2.0 authentication flow described in the PRD by creating a fake Google Photos authorization page that mimics the legitimate OAuth consent screen. When users attempt to connect their cloud storage accounts through the app's import feature, they are redirected to this phishing site which harvests their Google credentials. The attacker then uses these credentials to access the victim's entire Google account, including emails, documents, and payment information stored in Google Pay. This occurs because the app fails to properly validate the OAuth redirect URI and doesn't implement certificate pinning for the authentication flow. (Attack vector: OAuth phishing through unvalidated redirects)", 'potential_violations': ['Failure to implement secure authentication protocols', 'Inadequate verification of third-party authentication endpoints', 'Insufficient protection against credential harvesting'], 'jurisdictions': ['EU Digital Service Act'], 'law_citations': [358], 'rationale': "This scenario is plausible because the PRD requires OAuth 2.0 implementation for third-party authentication (FR-1, span 17) but doesn't specify security measures like redirect URI validation or certificate pinning. The TDD mentions OAuth 2.0 will be managed but lacks detail on validating authentication endpoints. Article 67 of the DSA is relevant as it pertains to platforms' obligations to provide information about security incidents and their duty to protect users from harm through their services. When users' accounts are compromised through the platform's authentication flow, the platform may be required to provide information about the breach to authorities.", 'prd_spans': [17, 18]}, {'description': "A 15-year-old user in California connects their iCloud account to import photos for a school video project. The app's content scanning system (CDS) incorrectly flags innocent family beach photos as potentially inappropriate content due to exposed skin detection algorithms. Following the false positive, the system automatically generates an alert to the Trust & Safety team as described in the TDD, which includes the minor's personal information, the flagged images, and metadata about their account. This data is retained for 90 days in accordance with the platform's retention policy, but the minor and their parents are never notified that their private family photos have been flagged, reviewed by human moderators, and stored in a separate compliance database. (Attack vector: Algorithmic overreach in content moderation)", 'potential_violations': ["Processing minors' personal data without parental consent", 'Failure to provide transparency about automated decision-making affecting minors', 'Retention of sensitive data about minors without justification'], 'jurisdictions': ['SB 976 (2024) California', 'CS/CS/HB 3 (2024) Florida'], 'law_citations': [69, 31], 'rationale': "This scenario directly relates to FR-4 (span 20) which mandates content safety scanning for all imported media. The TDD specifies that the CDS pipeline will scan all content and generate alerts for Trust & Safety review. California's SB 976 Article 27001 requires verifiable parental consent for processing minors' data, which would include scanning and human review of their personal photos. Florida's HB 3 Article 501.1736(3) requires parental consent for 14-15 year olds' accounts. The scenario is plausible because the system doesn't distinguish between adult and minor users when scanning imported content, and false positives in content moderation systems are well-documented.", 'prd_spans': [20, 12]}, {'description': "An attacker discovers that the cloud-importer-service's temporary S3 bucket in Singapore, mentioned in the TDD, has misconfigured access controls that allow enumeration of stored assets through predictable URL patterns. By exploiting timing attacks on the import process and the known 90-day retention period, the attacker systematically harvests thousands of users' imported photos and videos before they are deleted. The stolen media includes sensitive personal content, medical records photographed for insurance claims, and private family moments. The attacker then threatens to release this content unless users pay a ransom, targeting creators who rely on the platform for their livelihood. (Attack vector: S3 bucket misconfiguration exploit)", 'potential_violations': ['Failure to implement adequate technical security measures', 'Unauthorized disclosure of personal data', 'Insufficient access controls on data storage'], 'jurisdictions': ['EU Digital Service Act'], 'law_citations': [360], 'rationale': "The TDD explicitly mentions assets will be stored in an S3 bucket with 'access-controlled' settings, but doesn't specify the security configuration. The 90-day retention period creates a large window for exploitation. FR-3 (span 19) emphasizes fast and reliable import but doesn't address security during temporary storage. Article 69 of the DSA grants authorities power to conduct inspections of platforms' security measures, which would be triggered by such a data breach. The scenario exploits the gap between the PRD's emphasis on 'secure' import (span 17) and the TDD's implementation details that prioritize speed over security.", 'prd_spans': [17, 19, 20]}]
    """
    
    try:
        print(f"\n--- Starting test run ---")
        # Call the main audit method
        analysis_result = auditor.audit(
            doc_ids=document_ids_to_test,
            ent_ids=article_ids_to_test,
            threat_scenario=threat_scenario
        )
        
        print("\n\n--- ✅ FINAL ANALYSIS RESULT ---")
        print(analysis_result)
        
    except Exception as e:
        print(f"\n\n--- ❌ AN ERROR OCCURRED ---")
        print(f"Error Type: {type(e).__name__}")
        print(f"Error Details: {e}")