from first_model.database.Database import Database
from first_model.model.Law import Law
from first_model.model.Attacker import Attacker
from first_model.model.Auditor import Auditor
import json
# database = Database()
lawyer = Law()
attacker = Attacker()
auditor = Auditor()

def audit_project(project_id: int, database):
    doc_ids= database.load_document_ids(project_id=project_id)
    ent_ids = lawyer.audit(doc_ids=doc_ids)
    attack_scenarios = attacker.run_attack(ent_ids=ent_ids, max_n=3, prd_doc_id=doc_ids[0], tdd_doc_id=doc_ids[1])
    audit_id = database.project_audit(project_id=project_id)
    for scenario in attack_scenarios["scenarios"]:
        law_used = scenario["law_citations"]
        audit_response = auditor.audit(doc_ids=doc_ids, ent_ids=ent_ids, threat_scenario=scenario)

        evidence_dict = json.loads(audit_response[0]["evidence"])
        clean_evidence_dict = {f"{doc_ids[0]}": evidence_dict["prd"], f"{doc_ids[1]}": evidence_dict["tdd"]}

        issue_id = database.create_issue(audit_id=audit_id, issue_description=audit_response[0]["reasoning"], ent_id=int(law_used[0]) if law_used else -1, status="open", evidence=clean_evidence_dict, qn=audit_response[0]["clarification_question"])
        conv_id = database.create_conversation(audit_id=audit_id, issue_id=issue_id)
        start_convo = database.send_first_message(conv_id=conv_id, role="ai", content=audit_response[0]["clarification_question"])
# if __name__ == "__main__":
#     audit_project(2)