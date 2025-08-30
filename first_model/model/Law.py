from Model import Model
import os
import supabase
from supabase import create_client, Client
from dotenv import load_dotenv 
from llama_index.llms.gemini import Gemini
from llama_index.core import Document
from llama_index.core import VectorStoreIndex
from llama_index.embeddings.google_genai import GoogleGenAIEmbedding
import json
from llama_index.core.indices.query.query_transform import HyDEQueryTransform
from llama_index.core.query_engine import TransformQueryEngine

load_dotenv("../../../secrets/.env.dev")

class Auditor(Model):
    def __init__(self, database):
        self.GEMINI_API_KEY= os.environ.get("GEMINI_API_KEY")
        self.gemini = Gemini(models="models/gemini-pro", api_key=self.GEMINI_API_KEY)
        self.emb_model = GoogleGenAIEmbedding(
            model="models/embedding-004", 
            api_key=os.environ["GEMINI_API_KEY"]
        )
        super().__init__(database)

    def audit(self):
        articles = self.__fetch_articleDocs()
        emb_model = GoogleGenAIEmbedding(
            model="models/embedding-004", 
            api_key=os.environ["GEMINI_API_KEY"]
        )
        index = VectorStoreIndex.from_documents(articles, embed_model=emb_model)
        query_engine = index.as_query_engine(
            llm=self.gemini,
            similarity_top_k=3,
            )
        hyde = HyDEQueryTransform(include_original=True, llm=self.gemini)
        self.hyde_query_engine = TransformQueryEngine(query_engine, hyde)
        relevant_articles = self.__find_articles(self.__fetch_document(4))
        return relevant_articles

    def __fetch_articleDocs(self):
        response = supabase.table("Article_Entry").select("*").execute()
        docs = [
            Document(
                text=article["contents"],
                metadata={
                    "id": article["ent_id"],
                    "art_num": article["art_num"],
                    "belongs_to": article["belongs_to"]
                }
            )
            for article in response.data
        ]
        return docs

    def __fetch_document(self, doc_id):
        response = supabase.table("Document").select("*").eq("doc_id", doc_id).execute()
        return response.data[0]["content"]

    def __find_articles(self, document, index):
        query = (
            f"Are any of the legal articles relevant to the feature desribed in the following document. {document}"
            "If so, which articles."
        )

        response = self.hyde_query_engine.retrieve(query)
        articles = [{"article_id": node.node.metadata.get("id"),
                "art_num": node.node.metadata.get("art_num"),
                "belongs_to": node.node.metadata.get("belongs_to"),
                "score": node.score } for node in response]
        
        return json.dumps(articles)