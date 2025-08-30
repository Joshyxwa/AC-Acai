import os, json, re
import anthropic
from supabase import create_client, Client
from pydantic import BaseModel, Field, field_validator, ValidationError
from typing import List, Literal
from dotenv import load_dotenv
from pathlib import Path

# ------------------- ENV + CLIENTS -------------------

load_dotenv(dotenv_path="../../secrets/.env.dev")

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
anthropic_client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

# ------------------- DATA MODELS -------------------
PAREN_RE = re.compile(r"\(Attack vector:\s*.+\s*\)$")
PLACEHOLDER_PAREN = "(Attack vector: unspecified)"

class AttackScenario(BaseModel):
    description: str  # must end with "(Attack vector: … | Potential harm: …)"
    potential_violations: List[str]
    jurisdictions: List[str] = Field(description="Law names, e.g., 'EU Digital Services Act'")
    law_citations: List[int] = Field(description="ent_id values relied on")
    rationale: str
    prd_spans: List[int] = Field(
        default_factory=list,
        description="0-based PRD line indices (matching <span0>, <span1>, … from content_span)"
    )

    @field_validator("description", mode="before")
    @classmethod
    def ensure_parenthetical(cls, v: str):
        if not isinstance(v, str):
            return v
        s = v.strip()
        if not PAREN_RE.search(s):
            sep = "" if (len(s) == 0 or s.endswith((" ", "(", "—", "-", "–"))) else " "
            s = f"{s}{sep}{PLACEHOLDER_PAREN}"
        return s

    #AFTER: assert format is now correct (paranoia check)@field_validator("description")
    @classmethod
    def must_have_parenthetical(cls, v: str):
        if not PAREN_RE.search(v.strip()):
            raise ValueError("description must end with '(Attack vector: …)'.")
        return v
    
class AuditBundle(BaseModel):
    scenarios: List[AttackScenario]

# ------------------- JSON Helpers -------------------

_FENCE_RE = re.compile(r"^\s*```(?:json)?\s*|\s*```\s*$")

def _strip_md_fences(s: str) -> str:
    # Remove a single Markdown code-fence block if the model added one
    return _FENCE_RE.sub("", s).strip()

def _load_json_or_explain(txt: str) -> dict:
    """
    Try to parse JSON. If it fails, try to grab the last {...} block.
    Raise RuntimeError with a short preview if still invalid.
    """
    clean = _strip_md_fences(txt)
    try:
        return json.loads(clean)
    except json.JSONDecodeError as e:
        m = re.search(r"\{.*\}\s*$", clean, flags=re.DOTALL)
        if m:
            try:
                return json.loads(m.group(0))
            except Exception:
                pass
        preview = clean[:800]
        raise RuntimeError(
            f"Claude did not return valid JSON. JSON error: {e}. "
            f"Preview (first 800 chars):\n{preview}"
        ) from e

def _validate_bundle_or_explain(data: dict, max_n: int) -> AuditBundle:
    try:
        bundle = AuditBundle.model_validate(data)
    except ValidationError as ve:
        keys = list(data.keys()) if isinstance(data, dict) else type(data).__name__
        raw_preview = json.dumps(data, ensure_ascii=False)[:800]
        raise RuntimeError(
            "Claude output failed schema validation.\n"
            f"- Top-level keys: {keys}\n"
            f"- Pydantic errors:\n{ve}\n"
            f"- Raw preview (first 800 chars):\n{raw_preview}"
        ) from ve

    n = len(bundle.scenarios)
    if n != max_n:
        raise RuntimeError(f"Expected exactly {max_n} scenarios, got {n}.")
    return bundle

# ------------------- Supabase Helpers -------------------

def get_law_context(ent_ids: List[int], table: str = "Article_Entry") -> str:
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

    rows = res.data or []
    if not rows:
        return "NO_CONTEXT"

    out: List[str] = []
    for r in rows:
        header = f"- ent_id={r.get('ent_id')} | law={r.get('belongs_to') or 'N/A'}"
        if r.get("art_num"):
            header += f" | article={r.get('art_num')}"
        if r.get("type"):
            header += f" | type={r.get('type')}"
        if (r.get("type") or "").lower() == "definition" and r.get("word"):
            header += f" | defines={r.get('word')}"
        contents = (r.get("contents") or "").strip().replace("\n", " ")
        if len(contents) > 800:  # safety trim to keep prompt size under control
            contents = contents[:800] + "…"
        out.append(header + "\n  " + contents)

    return "\n".join(out)

# ------------------- Prompt Helpers -------------------
def load_prompt_template(path: str = "prompt_template/attacker_prompt.txt") -> str:
    return Path(path).read_text(encoding="utf-8")

# ------------------- Attack Logic -------------------

def run_attack(
    ent_ids: List[int],
    *, #Everything after the * (max_n, prd_doc_id) must be passed as keyword arguments.
    max_n: int = 3,
    prd_doc_id: int,
) -> AuditBundle:
    """
    Run an attack analysis: fetch PRD doc, call Claude, parse+validate JSON.
    Returns an AuditBundle Pydantic model.
    """
    # 1. Fetch PRD doc with spans
    doc_rows = (
        supabase.table("Document")
        .select("content, content_span")
        .eq("doc_id", prd_doc_id)
        .limit(1)
        .execute()
        .data
    )
    prd_text = (doc_rows[0].get("content") if doc_rows else "") or ""
    prd_span = (doc_rows[0].get("content_span") if doc_rows else "") or ""

    # 2. Build law context from ent_ids
    relevant_law = get_law_context(ent_ids)

    # 3. Build prompt
    template = load_prompt_template()
    final_prompt = template.format(
        max_n=max_n,
        prd_span=prd_span,
        prd_text=prd_text,
        relevant_law=relevant_law,
    )

    # 4. Call Claude
    resp = anthropic_client.messages.create(
        model="claude-opus-4-1-20250805",
        max_tokens=4000,
        messages=[{"role": "user", "content": final_prompt}],
    )

    if not resp.content or not getattr(resp.content[0], "text", "").strip():
        raise RuntimeError("Claude returned an empty response body.")

    # 4. Parse + validate
    raw_text = resp.content[0].text
    data = _load_json_or_explain(raw_text)
    bundle = _validate_bundle_or_explain(data, max_n)
    return bundle

# if __name__ == "__main__":
#     print("--- Running Attack ---")
#     ent_ids = [1, 2, 3]
#     result = run_attack(ent_ids, max_n=3, prd_doc_id=1)
#     print(result.model_dump_json(indent=2))

