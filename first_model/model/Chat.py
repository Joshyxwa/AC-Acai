import os
import json
import torch
from typing import List, Optional, Dict, Union
from anthropic import Anthropic
from supabase import create_client, Client
from dotenv import load_dotenv
import vecs
import re
load_dotenv("./secrets/.env.dev")

class Chat():
    def __init__(self):
        # --- LLM and Embedding Model Setup ---
        anthropic_key = os.environ.get("ANTHROPIC_API_KEY")
        self.llm_client = Anthropic(api_key=anthropic_key)

        # --- Database Client Setup ---
        url: str = os.environ.get("SUPABASE_URL")
        key: str = os.environ.get("SUPABASE_KEY")
        self.supabase: Client = create_client(url, key)

    ### --- UPDATED ADJUDICATOR ORCHESTRATOR --- ###
    def adjudicate(self, issue_id: int) -> Dict:
        """
        Orchestrates the re-evaluation of a flagged issue by gathering all context
        and calling the LLM for a final judgment.
        """
        # 1. Fetch all necessary data from the database using the correct sequence
        print(f"--- Fetching data for Issue ID: {issue_id} ---")
        
        # Step 1.1: Get the issue details
        issue = self.__retrieve_issue(issue_id)
        
        # Step 1.2: Use the issue_id to get the conversation ID
        conv_id_data = self.__retrieve_conversation_id(issue_id)
        if not conv_id_data:
            # Handle case where no conversation has started for this issue yet
            conversation = [] 
        else:
            # Assuming one conversation per issue, get the first conv_id
            conv_id = conv_id_data[0]['conv_id']
            # Step 1.3: Now get the actual messages using the conv_id
            conversation = self.__retrieve_conversation(conv_id)
        
        # Step 1.4: Fetch the related law and evidence
        law_entry_list = self.__fetch_article_entry_content(issue['ent_id_list'])
        evidence_quotes = self.__preprocess_evidence_spans(issue['evidence'])

        # 2. Format the comprehensive prompt
        prompt = self.__format_adjudicator_prompt(
            law_content=law_entry_list,
            evidence_quotes=evidence_quotes,
            conversation_history=conversation
        )
        
        # 3. Call the LLM for adjudication
        print("\n--- Adjudicating with LLM ---")
        adjudication_response = self.__llm_audit(prompt)

        print("\n--- Updating database with adjudication results ---")
        
        # Step 4.1: Upload the agent's response to the conversation thread
        agent_message = adjudication_response.get("agent_response_message")
        if agent_message:
            self.__upload_agent_message(conv_id, agent_message)
        
        # Step 4.2: Conditionally update the issue status if it's resolved
        new_status = adjudication_response.get("new_status")
        if new_status and new_status.lower() == 'document':
            # Use lowercase 'resolved' as is common for database enums
            self.__edit_issue_status(issue_id, "document")
            
        return agent_message

    def __retrieve_issue(self, issue_id: int) -> Dict:
        """Fetches the issue context from the database."""
        response = self.supabase.table("Issue").select("*").eq("issue_id", issue_id).single().execute()
        if response.data:
            return response.data
        else:
            raise ValueError(f"Issue with ID {issue_id} not found.")
        
    def __retrieve_conversation_id(self, issue_id: int) -> List[Dict]:
        """Fetches the conversation ID(s) associated with an issue."""
        response = self.supabase.table("Conversation").select("conv_id").eq("issue_id", issue_id).order("created_at", desc=False).execute()
        if response.data:
            return response.data
        else:
            return [] # Return empty list if no conversation yet
        
    def __retrieve_conversation(self, conv_id: int) -> List[Dict]:
        """Fetches the message history for a given conversation ID."""
        response = self.supabase.table("Message").select("type", "content").eq("conv_id", conv_id).order("created_at", desc=False).execute()
        if response.data:
            return response.data
        else:
            return [] # Return empty list if no messages yet
    
    def __fetch_article_entry_content(self, ent_id_list: int) -> Dict:
        """Fetches the content of a single legal article."""
        ent_list = []
        for ent_id in ent_id_list:
            response = self.supabase.table("Article_Entry").select("contents").eq("ent_id", ent_id).single().execute()
            if response.data:
                ent_list.append({"ent_id": ent_id, "content": response.data["contents"]})
            else:
                raise ValueError(f"Article with ID {ent_id} not found.")
        return ent_list

    def __preprocess_evidence_spans(self, evidence_input: Union[str, Dict]) -> Dict[int, List[str]]:
        """
        Parses the evidence input (either a JSON string or a dict) and retrieves 
        the actual text for each span.
        """
        if not evidence_input:
            return {}

        evidence_map = {}
        # --- START OF MODIFICATION ---
        # Check if the input is a string that needs to be parsed, or if it's already a dictionary.
        if isinstance(evidence_input, str):
            evidence_map = json.loads(evidence_input)
        elif isinstance(evidence_input, dict):
            evidence_map = evidence_input
        else:
            # Handle unexpected types if necessary
            raise TypeError(f"Evidence input must be a JSON string or a dictionary, not {type(evidence_input)}")
        # --- END OF MODIFICATION ---
        print(evidence_map)
        processed_evidence = {}
        for doc_id_str, span_ids in evidence_map.items():
            doc_id = int(doc_id_str)
            # This is the full string: <span0>...</span0><span1>...</span1>
            full_span_content_string = self.__retrieve_span_content_document(doc_id)
            
            quotes = []
            for span_id in span_ids:
                # Use a regular expression to find the content between the tags
                pattern = f"<{span_id}>(.*?)</{span_id}>"
                match = re.search(pattern, full_span_content_string)
                
                if match:
                    # The first group (1) is the content inside the parentheses (.*?)
                    quotes.append(match.group(1))
            
            processed_evidence[doc_id] = quotes
        return processed_evidence

    def __retrieve_span_content_document(self, doc_id: int) -> Dict[str, str]:
        """Fetches the content_span JSON object for a single document."""
        response = self.supabase.table("Document").select("content_span").eq("doc_id", doc_id).single().execute()
        if response.data and response.data["content_span"]:
            return response.data["content_span"]
        else:
            raise ValueError(f"Document or content_span for ID {doc_id} not found.")
            
    def __format_adjudicator_prompt(self, law_content: str, evidence_quotes: Dict, conversation_history: List[Dict]) -> str:
        """Formats the follow-up prompt for the Adjudicator agent."""
        with open("first_model/model/prompt_template/adjudicator_prompt.txt", "r") as file:
            prompt_template = file.read()

        evidence_str = json.dumps(evidence_quotes, indent=2)
        convo_str = "\n".join([f"{msg['type']}: {msg['content']}" for msg in conversation_history])

        final_prompt = prompt_template.format(
            RELEVANT_LAW=law_content,
            EVIDENCE_QUOTES=evidence_str,
            CONVERSATION_HISTORY=convo_str
        )
        return final_prompt
    
    def __llm_audit(self, prompt: str) -> Dict:
        """Reusable method to call the LLM and parse the JSON response."""
        response = self.llm_client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=4000,
            messages=[{"role": "user", "content": prompt}]
        )
        print("--- LLM Response Received ---")
        response_text = response.content[0].text
        print(response_text)
        return json.loads(response_text)

    def __edit_issue_status(self, issue_id: int, new_status: str) -> None:
        """Updates the status of an issue in the database."""

        response = self.supabase.table("Issue").update({"status": new_status}).eq("issue_id", issue_id).execute()
        print(f"Issue ID {issue_id} status updated to '{new_status}'.")

    def __upload_agent_message(self, conv_id: int, message: str) -> None:
        """Uploads a new message from the agent into the conversation."""
        response = self.supabase.table("Message").insert({
            "conv_id": conv_id,
            "type": "ai",
            "content": message
        }).execute()
        print(f"Agent message uploaded to conversation ID {conv_id}.")
        
# # Example usage for the new Adjudicator orchestrator
if __name__ == "__main__":
    
    print("--- Initializing Adjudicator Test Case ---")
    chat_agent = Chat()

    issue_id_to_test = 100

    try:
        print(f"\n--- Starting adjudication run for Issue ID: {issue_id_to_test} ---")
        adjudication_result = chat_agent.adjudicate(issue_id=issue_id_to_test)
        
        print("\n\n--- ✅ FINAL ADJUDICATION RESULT ---")
        print(json.dumps(adjudication_result, indent=2))
        
    except Exception as e:
        print(f"\n\n--- ❌ AN ERROR OCCURRED ---")
        print(f"Error Type: {type(e).__name__}")
        print(f"Error Details: {e}")