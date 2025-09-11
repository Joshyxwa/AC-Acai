import os
import json
import torch
from typing import List, Optional, Dict, Union
from anthropic import Anthropic
from supabase import create_client, Client
from dotenv import load_dotenv
import vecs
import re
import datetime

load_dotenv("./secrets/.env.dev")

class Report():
    def __init__(self):
        """Initializes the Report agent with necessary clients."""
        anthropic_key = os.environ.get("ANTHROPIC_API_KEY")
        self.llm_client = Anthropic(api_key=anthropic_key)

        # --- Database Client Setup ---
        url: str = os.environ.get("SUPABASE_URL")
        key: str = os.environ.get("SUPABASE_KEY")
        self.supabase: Client = create_client(url, key)

    def generate(self, audit_id: int) -> str:
        """Orchestrates the generation of the final, executive-ready audit report."""
        print(f"--- [ReportAgent] Starting final report generation for Audit ID: {audit_id} ---")
        
        # 1. Fetch foundational data
        audit_details = self.__retrieve_audit(audit_id)
        project_details = self.__retrieve_project_details(audit_details['project_id'])
        documents = self.__retrieve_documents_for_project(audit_details['project_id'])
        
        # 2. Build the detailed "audit_findings" dossier
        all_issues = self.__retrieve_issues_for_audit(audit_id)
        audit_findings_dossier = []
        for issue in all_issues:
            # --- START OF MODIFICATION ---
            # For each issue, fetch the specific law name and content
            article_details = self.__retrieve_article_details(issue['ent_id'])
            # --- END OF MODIFICATION ---

            conv_id_data = self.__retrieve_conversation_id(issue['issue_id'])
            conversation_transcript = []
            if conv_id_data:
                conv_id = conv_id_data[0]['conv_id']
                conversation_transcript = self.__retrieve_conversation(conv_id)

            issue_dossier = {
                "initial_finding": {
                    "law_name": article_details["law_name"],
                    "article_content": article_details["article_content"],
                    "article_number": article_details["article_number"],
                    "reasoning": issue.get('issue_description'),
                    "evidence_quotes": self.__preprocess_evidence_spans(issue.get('evidence'))
                },
                "conversation_transcript": conversation_transcript
            }
            audit_findings_dossier.append(issue_dossier)

        # 3. Assemble the complete dossier object for the prompt
        final_dossier = {
            "project_details": project_details,
            "audit_details": { "id": audit_id, "documents": ", ".join([f"{doc['type'].upper()} (v{doc['version']})" for doc in documents]) },
            "audit_findings": audit_findings_dossier
        }
        
        # 4. Format the prompt and call the LLM to generate the report
        prompt = self.__format_report_agent_prompt(final_dossier)
        print("\n--- [ReportAgent] Generating final report with LLM ---")
        report_markdown = self.__llm_generate_text(prompt)
        
        return report_markdown

    ### --- NEW HELPER METHOD --- ###
    def __retrieve_article_details(self, ent_id: int) -> Dict:
        """Fetches the law name (belongs_to) and content for a given article entry ID."""
        response = self.supabase.table("Article_Entry").select("belongs_to, contents", "art_num").eq("ent_id", ent_id).single().execute()
        if response.data:
            return {
                "law_name": response.data.get("belongs_to", "Unknown Regulation"),
                "article_content": response.data.get("contents", "No content found."),
                "article_number": f"Article Number: {response.data.get('art_num')}"
            }
        raise ValueError(f"Article Entry with ID {ent_id} not found.")

    # ... (rest of the private helper methods are unchanged) ...
    def __retrieve_audit(self, audit_id: int) -> Dict:
        response = self.supabase.table("Audit").select("project_id").eq("audit_id", audit_id).single().execute()
        if response.data: return response.data
        raise ValueError(f"Audit with ID {audit_id} not found.")

    def __retrieve_project_details(self, project_id: int) -> Dict:
        response = self.supabase.table("Project").select("name", "description").eq("project_id", project_id).single().execute()
        if response.data: return response.data
        raise ValueError(f"Project with ID {project_id} not found.")

    def __retrieve_documents_for_project(self, project_id: int) -> List[Dict]:
        response = self.supabase.table("Document").select("type", "version").eq("project_id", project_id).execute()
        return response.data if response.data else []

    def __retrieve_issues_for_audit(self, audit_id: int) -> List[Dict]:
        response = self.supabase.table("Issue").select("*").eq("audit_id", audit_id).execute()
        return response.data if response.data else []
        
    def __retrieve_conversation_id(self, issue_id: int) -> List[Dict]:
        response = self.supabase.table("Conversation").select("conv_id").eq("issue_id", issue_id).order("created_at").execute()
        return response.data if response.data else []
        
    def __retrieve_conversation(self, conv_id: int) -> List[Dict]:
        response = self.supabase.table("Message").select("type", "content").eq("conv_id", conv_id).order("created_at").execute()
        return response.data if response.data else []
    
    def __preprocess_evidence_spans(self, evidence_input: Union[str, Dict]) -> Dict[int, List[str]]:
        if not evidence_input: return {}
        evidence_map = json.loads(evidence_input) if isinstance(evidence_input, str) else evidence_input
        processed_evidence = {}
        for doc_id_str, span_ids in evidence_map.items():
            doc_id = int(doc_id_str)
            full_span_content_string = self.__retrieve_span_content_document(doc_id)
            quotes = [match.group(1) for span_id in span_ids if (match := re.search(f"<{span_id}>(.*?)</{span_id}>", full_span_content_string))]
            processed_evidence[doc_id] = quotes
        return processed_evidence

    def __retrieve_span_content_document(self, doc_id: int) -> str:
        response = self.supabase.table("Document").select("content_span").eq("doc_id", doc_id).single().execute()
        if response.data and response.data["content_span"]: return response.data["content_span"]
        raise ValueError(f"Document or content_span for ID {doc_id} not found.")

    def __format_report_agent_prompt(self, dossier: Dict) -> str:
        # Assuming prompt is in a file named 'report_agent_prompt.txt'
        with open("first_model/model/prompt_template/report_agent_prompt.txt", "r") as file:
            prompt_template = file.read()
        dossier_str = json.dumps(dossier, indent=2)
        final_prompt = f"{prompt_template}\n\n## Mission Critical Inputs:\n\n```json\n{dossier_str}\n```"
        return final_prompt

    def __llm_generate_text(self, prompt: str) -> str:
        response = self.llm_client.messages.create(
            model="claude-3-haiku-20240307",
            max_tokens=4000,
            messages=[{"role": "user", "content": prompt}]
        )
        print("--- [ReportAgent] LLM Report Received ---")
        return response.content[0].text

# if __name__ == "__main__":
#     def run_test():
#         print("--- Initializing Report Agent Test Case ---")
#         # You need to initialize the clients first to pass them to the Report agent

#         report_agent = Report()

#         audit_id_to_test = 16
#         try:
#             print(f"\n--- Starting final report generation for Audit ID: {audit_id_to_test} ---")
#             final_report = report_agent.generate(audit_id=audit_id_to_test)
#             with open("test_report_output.md", "w") as f:
#                 f.write(final_report)
#                 print("\nReport saved to 'test_report_output.md'")
#                 f.close
#             print("\n\n--- ✅ FINAL REPORT GENERATED ---")
#             print(final_report)
#         except Exception as e:
#             print(f"\n\n--- ❌ AN ERROR OCCURRED --- \n{e}")
#     run_test()