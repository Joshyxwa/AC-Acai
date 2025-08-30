from database.Database import Database
from model.Auditor import Auditor
from model.Attacker import Attacker
from enum import Enum

class IO:
    
    def __init__(self):
        self.database = Database()
        
        self.auditor = Auditor(self.database)
        self.attacker = Attacker(self.database)

        # AI models to process the message
        # audit_response = self.auditor.audit(message)
        # attack_response = self.attacker.attack(message)

        # Output for AI responses
        # self.display(audit_response, attack_response)

        # return audit_response, attack_response

    def display(self, audit_response, attack_response):
        print("Audit Response:", audit_response)
        print("Attack Response:", attack_response)

    def input_message(self, message: str):
        self.database.save_message(message)

        # PROCESS MESSAGE HERE

        return message

    def output_chatbox(self, message):
        return message
    
    def input_file(self, file: str):
        with open(file, 'r') as f:
            content = f.read()
        return self.input_message(content)