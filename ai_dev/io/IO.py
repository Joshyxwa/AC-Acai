import database.Database as Database
import model.Auditor as Auditor
import model.Attacker as Attacker

class IO:
    def __init__(self):
        self.database = Database.Database()
        
        self.auditor = Auditor.Auditor(self.database)
        self.attacker = Attacker.Attacker(self.database)
        
    def __input(self, message: str):
        self.database.save_message(message)
        audit_response = self.auditor.audit(message)
        attack_response = self.attacker.attack(message)
        
        self.display(audit_response, attack_response)

        return audit_response, attack_response

    def display(self, audit_response, attack_response):
        print("Audit Response:", audit_response)
        print("Attack Response:", attack_response)

    def input_raw(self, message: str):
        return self.__input(message)
    
    def input_amendment(self, message: str):
        amended_message = f"""Please amend the following message 
                                for clarity and correctness: {message}"""
        return self.__input(amended_message)
    
    def input_file(self, file: str):
        with open(file, 'r') as f:
            content = f.read()
        return self.__input(content)