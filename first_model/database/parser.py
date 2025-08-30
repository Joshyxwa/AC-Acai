import os
import re
from dotenv import load_dotenv
from typing import List, Dict, Tuple
from supabase import create_client
from Database import Database
from pathlib import Path

class Parser():
    def __init__(self):
        load_dotenv("./secrets/.env.dev")
        self.__URL = os.environ.get("SUPABASE_URL")
        self.__KEY = os.environ.get("SUPABASE_KEY")
        self.supabase = create_client(self.__URL, self.__KEY)

        self.title = ""
        self.definitions: List[Dict[str, str]] = []
        self.articles: List[Dict[str, str]] = []
        self.wd= Path(__file__).parent


    def parse(self, file_path: str):
        with open(self.wd/file_path, "r", encoding="utf-8") as f:
            content = f.read()

        # Extract the title (first non-empty line)
        lines = content.splitlines()
        self.title = next((line.strip() for line in lines if line.strip()), "")

        # Extract definitions block (between Definitions and first Article)
        definitions_block = re.search(r'Definitions(.*?)Article\s+1', content, re.DOTALL | re.IGNORECASE)
        if definitions_block:
            self._parse_definitions(definitions_block.group(1))

        # Extract articles block (from first Article onwards)
        articles_block = re.split(r'(Article\s+\d+\s*—)', content)
        if len(articles_block) > 1:
            self._parse_articles(articles_block)

    def _parse_articles(self, split_articles: List[str]):
        """
        Articles are split like:
        ["before", "Article 1 —", "content1", "Article 2 —", "content2", ...]
        """
        for i in range(1, len(split_articles), 2):
            article_header = split_articles[i].strip()
            article_text = split_articles[i + 1].strip() if i + 1 < len(split_articles) else ""

            # Extract article number and title
            article_match = re.match(r'(Article\s+\d+)\s*—\s*(.*)', article_header)
            if article_match:
                art_num = article_match.group(1)
                title = article_match.group(2)

                # Combine title and text into one "contents" field
                contents = f"{title} — {article_text}" if title else article_text

                self.articles.append({
                    "art_num": art_num,
                    "contents": contents.strip()
                })


    def _parse_definitions(self, definitions_text: str):
        """
        Match lines like:
        1.1 "User" — refers to ...
        1.2 "Content" — refers to ...
        """
        definition_pattern = r'(\d+\.\d+)\s+"([^"]+)"\s*—\s*(.+)'
        matches = re.findall(definition_pattern, definitions_text)
        for art_num, term, definition in matches:
            self.definitions.append({
                "word": term.strip(),
                "def_content": definition.strip(),
                "art_num": art_num.strip()
            })

    def get_next_id(self, minimum_value = 1):
        resp = self.supabase.table("Article_Entry").select("ent_id").order("ent_id", desc=True).limit(1).execute()
        try:
            if resp and getattr(resp, "data", None):
                latest = resp.data[0].get("ent_id")
                if isinstance(latest, int):
                    return latest + 1
        except Exception:
            pass
        return minimum_value

    def save_to_db(self):
        for definition in self.definitions:
            self.supabase.table("Article_Entry").insert({
                "ent_id": self.get_next_id(),
                "art_num": definition["art_num"],
                "type": "Definition",
                "belongs_to": self.title,
                "contents": definition["def_content"],
                "word": definition["word"],
                "embedding": None
            }).execute()

        for article in self.articles:
            self.supabase.table("Article_Entry").insert({
                "ent_id": self.get_next_id(),
                "art_num": article["art_num"],
                "type": "Law",
                "belongs_to": self.title,
                "contents": article["contents"],
                "word": None,
                "embedding": None
            }).execute()

    def print_stuff(self):
        print(f"\n=== Bill Title ===\n{self.title}\n")

        print("=== Definitions ===")
        if not self.definitions:
            print("No definitions found.")
        else:
            for definition in self.definitions:
                print(f"{definition['art_num']}: \"{definition['word']}\" — {definition['def_content']}")

        print("\n=== Articles ===")
        if not self.articles:
            print("No articles found.")
        else:
            for article in self.articles:
                print(f"{article['art_num']}: {article['contents']}\n")


if __name__ == "__main__":
    parser = Parser()
    parser.parse(file_path="bills/dtsa.txt")
    parser.save_to_db()
    parser.print_stuff()

