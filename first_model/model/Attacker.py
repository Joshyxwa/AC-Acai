from Model import Model
import os
import logging
import sys
import anthropic
import supabase
from pydantic import BaseModel, Field, field_validator
from typing import List, Literal
from dotenv import load_dotenv
import html
import re
load_dotenv(dotenv_path="../../secrets/.env.dev")

PAREN_RE = re.compile(r"\(Attack vector:\s*.+\s*\)$")
PLACEHOLDER_PAREN = "(Attack vector: unspecified)"
max_n = 3

class AttackScenario(BaseModel):
    description: str  # must end with "(Attack vector: … | Potential harm: …)"
    potential_violations: List[str]
    jurisdictions: List[str] = Field(description="Law names, e.g., 'EU Digital Services Act'")
    law_citations: List[str] = Field(description="ent_id values relied on")
    rationale: str
    prd_spans: List[int] = Field(
        default_factory=list,
        description="0-based PRD line indices (matching <span id='L0'>, <span id='L1'> …)"
    )

    @field_validator("description", mode="before")
    @classmethod
    def ensure_parenthetical(cls, v: str):
        if not isinstance(v, str):
            return v
        s = v.strip()
        if not PAREN_RE.search(s):
            # add a space if needed before appending
            sep = "" if (len(s) == 0 or s.endswith((" ", "(", "—", "-", "–"))) else " "
            s = f"{s}{sep}{PLACEHOLDER_PAREN}"
        return s

    # 2) AFTER: assert format is now correct (paranoia check)
    @field_validator("description")
    @classmethod
    def must_have_parenthetical(cls, v: str):
        if not PAREN_RE.search(v.strip()):
            # extremely unlikely now, but keeps the contract tight
            raise ValueError(
                "description must end with '(Attack vector: … | Potential harm: …)'."
            )
        return v
    
class AuditBundle(BaseModel):
    scenarios: List[AttackScenario] = Field(min_items=max_n, max_items=max_n)

class Attacker(Model):
    def __init__(self, database):
        super().__init__(database)
        self.anthropic_key = os.environ.get("ANTHROPIC_API_KEY")
        self.client = anthropic.Anthropic(
            api_key=self.anthropic_key,
        )
    def attack(self, relevant_law):
        prd_text = supabase.table("Document").select("content").eq("doc_id", 1).execute().data[0]["content"]
        span_wrapped_prd = self.__prd_to_spans(prd_text)
        final_prompt = f"""
        You are the Adversarial Strategist Agent.
        Generate diverse, realistic attack scenarios that stress-test safety & legal compliance.
        Return ONLY JSON. No prose outside JSON.
                   
        Task — Attack scenarios
        - Produce exactly {max_n} distinct scenarios (no fewer), each schema-compliant.
        - Each AttackScenario MUST include ONLY these keys:
        - "description": string (clear, concrete attack story; ONE paragraph max); END with: (Attack vector: <short phrase>)
        - "potential_violations": string[]
        - "jurisdictions": string[] (law names, e.g., "EU Digital Services Act")
        - "law_citations": string[] (ent_id values relied on)
        - "rationale": string (why this matters for THIS PRD)
        - "prd_spans": int[] (0-based PRD line indices, matching <span id='L0'>, <span id='L1'> …)
        - Ground each scenario in the PRD lines you cite in "prd_spans".
        - Make scenarios DISTINCT (no near-duplicates).

        Self-check before returning:
        - "scenarios" has exactly {max_n} items.
        - Every scenario has non-empty "prd_spans" with valid line indices.
        - Each scenario cites at least one ent_id in "law_citations".

        Output shape (ONLY this JSON object, no comments):
        {{
        "scenarios": [... exactly {max_n} items ...]
        }}

        PRD (span-wrapped; 0-based indices via id='L{{i}}'):
        <<<PRD_SPANS>>>
        {span_wrapped_prd}
        <<<END PRD_SPANS>>>

        PRD:
        <<<PRD>>>json.dumps(relevant_articles, indent=2)
        {prd_text}
        <<<END PRD>>>

        Legal/Definition Context (each item has ent_id for citation):
        {relevant_law}

        Generate exactly {max_n} DISTINCT attack scenarios tied to this PRD, each citing >= 1 ent_id and include valid prd_spans.
        Output:
        Return an object with field "scenarios": AttackScenario[]
        """
        message = self.client.messages.create(
            model="claude-opus-4-1-20250805",json.dumps(relevant_articles, indent=2)
            max_tokens=1024,
            messages=[
                {"role": "user", "content": final_prompt}
            ]
        )
        return message.content[0].text


    def __prd_to_spans(self, prd_text: str) -> str:
        lines = prd_text.splitlines()
        return "\n".join(
            f"<span id='L{i}'>{html.escape(line)}</span>"
            for i, line in enumerate(lines)
        )

    def get_law_context(self, ent_ids: list[str], table: str = "Article_Entry") -> str:
        """
        Fetch compact, traceable legal context from Supabase.
        Format: one bullet per row with ent_id, law, article/type/definition, and trimmed contents.
        """
        if not ent_ids:
            return "NO_CONTEXT"

        res = (
            supabase.table(table)
            .select("ent_id, art_num, type, belongs_to, contents, word")
            .in_("ent_id", ent_ids)
            .execute()
        )

        out = []
        for r in res.data or []:
            header = f"- ent_id={r.get('ent_id')} | law={r.get('belongs_to') or 'N/A'}"
            if r.get("art_num"):
                header += f" | article={r.get('art_num')}"
            if r.get("type"):
                header += f" | type={r.get('type')}"
            if (r.get("type") or "").lower() == "definition" and r.get("word"):
                header += f" | defines={r.get('word')}"
            contents = (r.get("contents") or "").strip().replace("\n", " ")
            if len(contents) > 800:  # safety trim
                contents = contents[:800] + "…"
            out.append(header + "\n  " + contents)

        return "\n".join(out) if out else "NO_CONTEXT"