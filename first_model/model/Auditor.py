from Model import Model

class Auditor(Model):
    def __init__(self, database):
        super().__init__(database)

    def audit(self, threat_scenario, issues_broken):
        with open("prompt.txt", "r") as file:
            prompt_template = file.read()
            
        with open("threat1.txt", "r") as file:
            threat_scenario = file.read()

        with open("issues1.txt", "r") as file:
            issues_broken = file.read()