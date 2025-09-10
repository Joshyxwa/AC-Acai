import os
import json
import re
import anthropic
from supabase import create_client, Client
from pydantic import BaseModel, Field, field_validator, ValidationError
from typing import List, Dict, Tuple, Optional
from dotenv import load_dotenv
from pathlib import Path

# ★ NEW: embedding/rerank deps
import numpy as np
import torch
import torch.nn.functional as F
from transformers import AutoTokenizer, AutoModel


try:
    import cohere
    HAS_COHERE = True
except Exception:
    HAS_COHERE = False


# Load environment variables from a .env file
load_dotenv(dotenv_path="../../secrets/.env.dev")

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

# ───────────────────────────────────────────────────────────────────────────────
# ATTACKER with integrated RAG
# ───────────────────────────────────────────────────────────────────────────────
class Attacker:
    """
    Generates attack scenarios by analyzing a PRD and augmenting Claude with
    retrieved case-study context (HyDE → dense + FTS → RRF → rerank).
    """
    _FENCE_RE = re.compile(r"^\s*```(?:json)?\s*|\s*```\s*$")

    # ★ NEW: constants for embeddings and RAG
    _EMBED_MODEL_ID = os.environ.get("EMBED_MODEL_ID", "Qwen/Qwen3-Embedding-8B")   # override via ENV if needed
    _TARGET_DIM = 4000                                                                 # halfvec(4000) in Supabase
    _DEVICE = "cuda" if torch.cuda.is_available() else ("mps" if torch.backends.mps.is_available() else "cpu")

    def __init__(self):
        print(">>> Using Attackerv2 implementation")  # Trace message

        # Anthropic
        anthropic_key = os.environ.get("ANTHROPIC_API_KEY")
        if not anthropic_key:
            raise ValueError("ANTHROPIC_API_KEY environment variable not set.")
        self.llm_client = anthropic.Anthropic(api_key=anthropic_key)

        # Supabase
        url: str = os.environ.get("SUPABASE_URL")
        key: str = os.environ.get("SUPABASE_KEY")
        if not url or not key:
            raise ValueError("Supabase URL or Key environment variables not set.")
        self.supabase: Client = create_client(url, key)

        # ★ NEW: Cohere (optional) for reranking
        self._co = None
        if HAS_COHERE and os.environ.get("COHERE_API_KEY"):
            print(">>> Cohere reranker enabled")
            self._co = cohere.Client(os.environ["COHERE_API_KEY"])

        # ★ NEW: load embedder once
        self._tok = AutoTokenizer.from_pretrained(self._EMBED_MODEL_ID, padding_side="left")
        torch_dtype = torch.float16 if self._DEVICE in ("cuda", "mps") else torch.float32
        self._mdl = AutoModel.from_pretrained(
            self._EMBED_MODEL_ID,
            torch_dtype=torch_dtype,
            low_cpu_mem_usage=True,
            trust_remote_code=True
        )
        self._mdl.to(self._DEVICE)
        self._mdl.eval()

    @staticmethod
    def _strip_md_fences(s: str) -> str:
        # Remove a single Markdown code-fence block if the model added one
        return Attacker._FENCE_RE.sub("", s).strip()

    @staticmethod
    def _load_json_or_explain(txt: str) -> dict:
        """
        Try to parse JSON. If it fails, try to grab the last {...} block.
        Raise RuntimeError with a short preview if still invalid.
        """
        clean = Attacker._strip_md_fences(txt)
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
    @staticmethod
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

    def get_law_context(self, ent_ids: List[int], table: str = "Article_Entry") -> str:
        """
        Fetch compact, traceable legal context from Supabase.
        Format: one bullet per row with ent_id, law, article/type/definition, and trimmed contents.
        """
        if not ent_ids:
            return "NO_CONTEXT"

        res = (
            self.supabase.table(table)
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
    @staticmethod
    def load_prompt_template(path: str = None) -> str:
        if path is None:
            # Always resolve relative to this file
            path = Path(__file__).parent / "prompt_template" / "attacker_promptv2.txt"
        else:
            path = Path(path)
        return Path(path).read_text(encoding="utf-8")

    # ────────────────────────────────────────────────────────────────────────
    # ★ NEW: Embedding + HyDE + Retrieval + RRF + Rerank
    # ────────────────────────────────────────────────────────────────────────
    @torch.no_grad()
    def _last_token_pool(self, last_hidden_states: torch.Tensor, attention_mask: torch.Tensor) -> torch.Tensor:
        left_pad = (attention_mask[:, -1].sum() == attention_mask.shape[0])
        if left_pad:
            return last_hidden_states[:, -1]
        seq_lens = attention_mask.sum(dim=1) - 1
        bsz = last_hidden_states.shape[0]
        return last_hidden_states[torch.arange(bsz, device=last_hidden_states.device), seq_lens]

    @torch.no_grad()
    def _embed_texts(self, texts: List[str], batch=8, max_length=1024) -> np.ndarray:
        vecs = []
        for i in range(0, len(texts), batch):
            chunk = texts[i:i+batch]
            toks = self._tok(chunk, padding=True, truncation=True, max_length=max_length, return_tensors="pt")
            dev = next(iter(self._mdl.state_dict().values())).device
            toks = {k: v.to(dev) for k, v in toks.items()}
            out = self._mdl(**toks)
            pooled = self._last_token_pool(out.last_hidden_state, toks["attention_mask"])
            pooled = F.normalize(pooled, p=2, dim=1)
            d = pooled.size(1)
            if d >= self._TARGET_DIM:
                pooled = pooled[:, :self._TARGET_DIM]
            else:
                pad = torch.zeros((pooled.size(0), self._TARGET_DIM - d), device=pooled.device, dtype=pooled.dtype)
                pooled = torch.cat([pooled, pad], dim=1)
            pooled = pooled.to(torch.float32)  # halfvec(4000)
            vecs.append(pooled.cpu().numpy())
        return np.vstack(vecs)

    def _hyde_expand(self, query: str, max_tokens=350) -> str:
        prompt = f"""
        You are a neutral safety/compliance analyst. Write one concise paragraph that hypothesizes the most likely risky behaviors, failure modes, or abuse patterns for the following PRD and TDD excerpt.

        EXCERPT:
        {query}

        Return only the paragraph."""
        resp = self.llm_client.messages.create(
            model="claude-opus-4-1-20250805",
            max_tokens=max_tokens,
            messages=[{"role": "user", "content": prompt}],
        )
        return (resp.content[0].text.strip() if resp.content else "") or query

    # RPC wrappers (SQL functions must already exist)
    def _dense_retrieve(self, vec: np.ndarray, k=50) -> List[Dict]:
        params = {"qvec": vec.tolist(), "top_k": k, "law_filter": None, "company_filter": None}
        return self.supabase.rpc("match_case_chunks_dense", params).execute().data or []

    def _fts_retrieve(self, q: str, k=50) -> List[Dict]:
        params = {"qtext": q, "top_k": k, "law_filter": None, "company_filter": None}
        return self.supabase.rpc("match_case_chunks_fts", params).execute().data or []

    def _rrf(self, lists: List[List[Dict]], k_rrf: int = 60, top_n: int = 60) -> List[Dict]:
        scored: Dict[Tuple[str, int], float] = {}
        meta: Dict[Tuple[str, int], Dict] = {}
        for lst in lists:
            for rank, item in enumerate(lst, 1):
                key = (item["doc_id"], item["chunk_id"])
                scored[key] = scored.get(key, 0.0) + 1.0 / (k_rrf + rank)
                if key not in meta:
                    meta[key] = item
        fused = [{**meta[k], "rrf_score": v} for k, v in scored.items()]
        fused.sort(key=lambda x: x["rrf_score"], reverse=True)
        return fused[:top_n]

    def _cohere_rerank(self, query: str, docs: List[Dict], top_k: int = 10) -> List[Dict]:
        if not self._co:
            return docs[:top_k]
        resp = self._co.rerank(
            model="rerank-v3.5",
            query=query,
            documents=[d["text"] for d in docs],
            top_n=min(top_k, len(docs)),
        )
        ranked = []
        for r in resp.results:
            d = dict(docs[r.index])
            d["rerank_score"] = float(r.relevance_score)
            ranked.append(d)
        ranked.sort(key=lambda x: x["rerank_score"], reverse=True)
        return ranked

    def _hybrid_retrieve_context(self, prd_snippet: str, final_top: int = 10) -> List[Dict]:
        """
        HyDE(prd_snippet) → embed(q + hyde) → dense + fts → RRF → rerank → top_k docs
        """
        qvec = self._embed_texts([prd_snippet])[0]
        hyp = self._hyde_expand(prd_snippet)
        hvec = self._embed_texts([hyp])[0]

        dense = self._dense_retrieve(qvec, k=60)
        dense_hyde = self._dense_retrieve(hvec, k=60)
        fts = self._fts_retrieve(prd_snippet, k=60)

        fused = self._rrf([dense, dense_hyde, fts], k_rrf=60, top_n=60)
        reranked = self._cohere_rerank(prd_snippet, fused, top_k=final_top)
        return reranked

    @staticmethod
    def _format_rag_context(docs: List[Dict], sep: str = "\n---\n") -> str:
        parts = []
        for d in docs:
            head = f"[doc_id={d.get('doc_id')}] [chunk={d.get('chunk_id')}]"
            src = f"law={d.get('law')}, company={d.get('company')}, link={d.get('link')}"
            txt = d.get("text", "")
            parts.append(f"{head}\n{src}\n{txt}")
        return sep.join(parts) if parts else "NO_EXTRA_CONTEXT"
    
    # ------------------- Attack Logic -------------------

    def run_attack(
        self,
        ent_ids: List[int],
        *,
        max_n: int = 3,
        prd_doc_id: int,
        tdd_doc_id: Optional[int] = None,   # ← change type + default
    ) -> dict:
        """
        Fetch PRD (+optional TDD), retrieve top case-study chunks via hybrid search,
        pass everything to Claude, then validate strict JSON → AuditBundle.
        Returns dict (AuditBundle.model_dump()).
        """
        # 1) Fetch PRD (with spans)
        doc_rows = (
            self.supabase.table("Document")
            .select("content, content_span")
            .eq("doc_id", prd_doc_id)
            .limit(1)
            .execute()
            .data
        )
        prd_text = (doc_rows[0].get("content") if doc_rows else "") or ""
        prd_span = (doc_rows[0].get("content_span") if doc_rows else "") or ""

        # 2) Fetch TDD (optional)
        tdd_text = ""
        if tdd_doc_id is not None:
            tdd_rows = (
                self.supabase.table("Document")
                .select("content")
                .eq("doc_id", tdd_doc_id)
                .limit(1)
                .execute()
                .data
            )
            tdd_text = (tdd_rows[0].get("content") if tdd_rows else "") or ""

        # 3) Legal context (ent_ids → compact law bullets)
        relevant_law = self.get_law_context(ent_ids)

        # 4) Retrieve external case-study context (Hybrid RAG)
        # Use a short combined snippet (PRD+TDD) to guide retrieval, but keep it small.
        prd_snippet = prd_text.strip()[:600]
        tdd_snippet = tdd_text.strip()[:400]
        query_snippet = (prd_snippet + ("\n" + tdd_snippet if tdd_snippet else "")).strip()
        rag_docs = self._hybrid_retrieve_context(query_snippet or prd_snippet, final_top=10)
        rag_context = self._format_rag_context(rag_docs)

        # 5) Build the prompt (template must include {rag_context} and {tdd_text}; if not, we append)
        template = self.load_prompt_template()
        final_prompt = template.format(
            max_n=max_n,
            prd_span=prd_span,
            prd_text=prd_text,
            tdd_text=tdd_text,          # ← TDD injected
            relevant_law=relevant_law,
            rag_context=rag_context,    # ← RAG injected
        )

        # Fallback: if template didn’t have {rag_context} or {tdd_text}, append them
        if "{rag_context}" not in template or "{tdd_text}" not in template:
            final_prompt += "\n\n"
            if "{tdd_text}" not in template:
                final_prompt += f"Additional Technical Design Details (TDD):\n{(tdd_text or 'N/A')}\n\n"
            if "{rag_context}" not in template:
                final_prompt += f"Additional Retrieved Case Studies (top-10, hybrid fused + reranked):\n{rag_context}\n"

        # 6) Call Claude
        resp = self.llm_client.messages.create(
            model="claude-opus-4-1-20250805",
            max_tokens=4000,
            messages=[{"role": "user", "content": final_prompt}],
        )
        if not resp.content or not getattr(resp.content[0], "text", "").strip():
            raise RuntimeError("Claude returned an empty response body.")

        # 7) Parse + validate strict JSON → AuditBundle
        raw_text = resp.content[0].text
        data = self._load_json_or_explain(raw_text)
        bundle = self._validate_bundle_or_explain(data, max_n)
        return bundle.model_dump()










if __name__ == "__main__":
    print("--- Running Attack ---")
    ent_ids = list(range(1, 11))
    attacker = Attacker()
    result = attacker.run_attack(ent_ids=ent_ids, max_n=3, prd_doc_id=1, tdd_doc_id=2)
    print(result)

