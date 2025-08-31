
import os
import json
import csv
import time
from pathlib import Path
from typing import Optional, Tuple

from dotenv import load_dotenv
from supabase import create_client, Client

# your existing modules
from first_model.model.Law import Law
from first_model.model.Attackerv2 import Attacker
from first_model.model.Auditor import Auditor

# Database is referenced in your main.py; import it if available.
try:
    from first_model.database.Database import Database
except Exception:
    Database = None  # we'll gracefully handle if missing

ROOT = Path(__file__).resolve().parent
load_dotenv(ROOT / "./secrets/.env.dev")

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")
if not SUPABASE_URL or not SUPABASE_KEY:
    raise SystemExit("Missing SUPABASE_URL or SUPABASE_KEY in ./secrets/.env.dev")

# output
OUT_CSV = ROOT / "eval_results.csv"

# -----------------------------------------------------------------------------
# Helpers to create temp rows in your existing schema
# -----------------------------------------------------------------------------
def sb() -> Client:
    return create_client(SUPABASE_URL, SUPABASE_KEY)

def create_temp_document(client: Client, *, doc_type: str, content: str) -> int:
    """
    Insert a row into Document with both 'content' and 'content_span'.
    content_span mirrors content so your Attacker/Auditor can read it.
    Returns the new doc_id (int).
    """
    data = {
        "type": doc_type,          # expected values: "PRD" or "TDD"
        "content": content or "",
        "content_span": content or "",
    }
    res = client.table("Document").insert(data).select("doc_id").execute()
    if not res.data:
        raise RuntimeError(f"Failed to insert {doc_type} Document")
    return int(res.data[0]["doc_id"])

def create_temp_project_for_docs(client: Client, prd_id: int, tdd_id: int) -> Optional[int]:
    """
    If your schema includes a Project table and a join that Database.project_audit expects,
    create a lightweight Project to obtain a valid project_id. This is best-effort:
    if the insert fails (unknown schema), we return None and still proceed with the run.
    """
    try:
        # Insert a project row; adjust fields if your schema differs.
        title = f"eval_{int(time.time()*1000)}_{prd_id}_{tdd_id}"
        pres = client.table("Project").insert({"title": title}).select("project_id").execute()
        if not pres.data:
            return None
        project_id = int(pres.data[0]["project_id"])

        # If you have a join table like Project_Document, add links (best guess names).
        # Adjust to match your actual schema if different.
        try:
            client.table("Project_Document").insert([
                {"project_id": project_id, "doc_id": prd_id},
                {"project_id": project_id, "doc_id": tdd_id},
            ]).execute()
        except Exception:
            # If there's no join table or different schema, ignore.
            pass

        return project_id
    except Exception:
        return None

# -----------------------------------------------------------------------------
# Main eval loop
# -----------------------------------------------------------------------------
def main(bill: str = "All", max_scenarios: int = 3):
    client = sb()

    # Load test_set rows
    q = client.table("test_set").select("id, feature_name, feature_description").execute()
    rows = q.data or []
    if not rows:
        print("No rows found in test_set.")
        return

    # Instantiate your stacks
    lawyer = Law()
    attacker = Attacker()
    auditor = Auditor()
    database = Database() if Database else None

    # Prepare CSV
    headers = [
        "test_id",
        "prd_doc_id",
        "tdd_doc_id",
        "ent_ids",
        "scenario_count",
        "scenarios_json",
        "audit_id",
        "error",
    ]
    with open(OUT_CSV, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=headers)
        w.writeheader()

        for r in rows:
            tid = r.get("id")
            fname = r.get("feature_name") or ""
            fdesc = r.get("feature_description") or ""
            prd_text = (str(fname).strip() + "\n\n" + str(fdesc).strip()).strip()
            tdd_text = ""  # intentionally empty per your request

            prd_id = None
            tdd_id = None
            project_id = None
            ent_ids = []
            scenarios = {}
            audit_id = None
            err = ""

            try:
                # 1) create temp PRD/TDD Document rows
                prd_id = create_temp_document(client, doc_type="PRD", content=prd_text)
                tdd_id = create_temp_document(client, doc_type="TDD", content=tdd_text)
                doc_ids = [prd_id, tdd_id]

                # 2) (optional) create a temp Project so we can call database.project_audit(...)
                project_id = create_temp_project_for_docs(client, prd_id, tdd_id)

                # 3) EXACT CALLS as requested
                ent_ids = lawyer.audit(doc_ids=doc_ids, bill=bill)
                attack_scenarios = attacker.run_attack(
                    ent_ids=ent_ids,
                    max_n=max_scenarios,
                    prd_doc_id=doc_ids[0],
                    tdd_doc_id=doc_ids[1],
                )
                # NB: You didn't ask to use `auditor` here, so we only keep it instantiated.

                if database and project_id is not None:
                    audit_id = database.project_audit(project_id=project_id)
                else:
                    audit_id = None  # still produce column, but it's ok if Database/project is unavailable

                scenarios = attack_scenarios

            except Exception as e:
                err = str(e)

            # Flatten a few bits for the CSV
            scenario_list = (scenarios or {}).get("scenarios", [])
            scenario_count = len(scenario_list)

            w.writerow({
                "test_id": tid,
                "prd_doc_id": prd_id,
                "tdd_doc_id": tdd_id,
                "ent_ids": json.dumps(ent_ids, ensure_ascii=False),
                "scenario_count": scenario_count,
                "scenarios_json": json.dumps(scenarios, ensure_ascii=False),
                "audit_id": audit_id if audit_id is not None else "",
                "error": err,
            })

    print(f"✅ eval complete. wrote: {OUT_CSV}")

if __name__ == "__main__":
    main()