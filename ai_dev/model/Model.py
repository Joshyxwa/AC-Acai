import logging
from google import genai
from dotenv import load_dotenv
import os

class Model:
    def __init__(self, database, model = "Claude Sonnet 4"):
        self.init_logger()
        
        self.logger.info(f"Initializing Model with {model}")

        self.database = database

        self.model = model
        load_dotenv("./secrets/.env.dev")
        self.logger.debug("Environment variables loaded")
        
        match self.model:
            case model if model.lower().startswith("claude"):
                self.key = os.environ.get("ANTHROPIC_API_KEY")
                self.logger.debug("Using Anthropic API key")
            case model if model.lower().startswith("gemini"):
                self.key = os.environ.get("GEMINI_API_KEY")
                self.logger.debug("Using Gemini API key")
            case _:
                self.logger.error(f"Unsupported model: {self.model}")
                raise ValueError(f"Unsupported model: {self.model}")

        self.logger.info("Initializing client")
        if self.model.lower().startswith("gemini"):
            self.client = genai.GenerativeModel(self.model, api_key=self.key)
        elif self.model.lower().startswith("claude"):
            # Placeholder for Anthropic client initialization, replace with actual Anthropic API usage
            import anthropic
            self.client = anthropic.Anthropic(api_key=self.key)
        else:
            self.client = None
        self.logger.info("Model initialization complete")

    def init_logger(self):
        # Initialize logger
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.INFO)
        
        # Create handler if not already set up
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)

    def create_message(self, content, token = 1024):
            response = self.client.messages.create(
                model=self.model,
                max_tokens=token,
                messages=[
                    {"role": "user", "content": content}
                ]
            )
            return response
        
    
