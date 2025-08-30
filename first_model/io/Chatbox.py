class Chatbox:
    def __init__(self, database, conv_id):
        self.database = database
        self.conv_id = self.database.get_conversation(conv_id)

    def send_message(self, message):
        self.database.save_message(message, self.conv_id)

    def receive_message(self, msg_id):
        return self.database.load_message(msg_id, self.conv_id)
