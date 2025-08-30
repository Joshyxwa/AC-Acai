from first_model.database.Database import Database
from first_model.model.Law import Law
from first_model.model.Attacker import Attacker
from first_model.model.Auditor import Auditor

database = Database()
lawyer = Law()
attacker = Attacker()
auditor = Auditor()
def audit_project(project_id: int):
    doc_ids= database.load_document_ids(project_id=project_id)
    ent_ids = lawyer.audit(doc_ids=doc_ids)
    attack_scenarios = attacker.run_attack(ent_ids=ent_ids, max_n=3, prd_doc_id=doc_ids[0])
    audit_response = auditor.audit(doc_ids=doc_ids, ent_ids=ent_ids, threat_scenario=attack_scenarios)

    print(audit_response)
if __name__ == "__main__":
    audit_project(1)