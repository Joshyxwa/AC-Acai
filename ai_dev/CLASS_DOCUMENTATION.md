# Python Class Documentation: ai_dev Directory

This document provides an overview of the main Python classes found in the `ai_dev` directory of this project. Each class is briefly described, including its purpose, key methods, and relationships to other classes.

---

## 1. `Database` (ai_dev/database/Database.py)
**Purpose:**
Handles all interactions with the Supabase database, including saving and loading data and messages.

**Key Methods:**
- `__init__`: Initializes the Supabase client using environment variables.
- `save_data(table, data)`: Inserts data into a specified table.
- `load_data(table, query)`: Loads data from a table by ID.
- `save_message(message)`: Saves a message to the "Message" table.
- `get_next_id(table, id)`: Gets the next available ID for a table.
- `get_current_timestamp()`: Returns the current timestamp.

---

## 2. `Model` (ai_dev/model/Model.py)
**Purpose:**
Abstract base class for AI models. Handles model initialization, API key management, and client setup for different LLM providers (Anthropic, Gemini).

**Key Methods:**
- `__init__(database, model)`: Initializes the model, loads API keys, and sets up the client.
- `init_logger()`: Sets up logging for the class.

---

## 3. `Auditor` (ai_dev/model/Auditor.py)
**Purpose:**
Inherits from `Model`. Represents an AI agent that audits messages.

**Key Methods:**
- `__init__(database)`: Initializes the auditor with a database.
- `audit(message)`: Placeholder for audit logic.

---

## 4. `Attacker` (ai_dev/model/Attacker.py)
**Purpose:**
Inherits from `Model`. Represents an AI agent that attacks messages.

**Key Methods:**
- `__init__(database)`: Initializes the attacker with a database.
- `attack(message)`: Placeholder for attack logic.

---

## 5. `IO` (ai_dev/io/IO.py)
**Purpose:**
Handles user input/output, coordinates between the database, auditor, and attacker classes.

**Key Methods:**
- `__init__`: Initializes the database, auditor, and attacker.
- `input(message)`: Saves the message, passes it to auditor and attacker, displays responses.
- `display(audit_response, attack_response)`: Prints responses to the console.

---

## Class Relationships
- `IO` creates and manages instances of `Database`, `Auditor`, and `Attacker`.
- `Auditor` and `Attacker` both inherit from `Model` and require a `Database` instance.
- `Model` handles the setup for LLM clients and logging.

---

*This documentation was auto-generated. For more details, see the source code in each file.*
