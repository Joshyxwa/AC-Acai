# GeoCompliance Mock Server

A FastAPI-based backend server that integrates with **Supabase** for storage of
projects, documents, audits, issues, conversations, and messages.  
It exposes REST endpoints for project management, compliance auditing, and threaded
commenting with system/user/AI responses.

---

## 📦 Requirements

- Python 3.10+
- [Supabase](https://supabase.com/) project with the following tables ([ref schema](./database/schema.md)):
  - `Project`
  - `Document`
  - `Audit`
  - `Issue`
  - `Conversation`
  - `Message`
  - `Article_Entry`
- A `.env.dev` file (stored in the main folder under a folder `secrets/`) with:

```env
# AI APIs
ANTHROPIC_API_KEY="..."
GEMINI_API_KEY="..."

# SUPABASE
SUPABASE_PASSWORD="..."
SUPABASE_REF="..."
SUPABASE_URL="..."
SUPABASE_KEY="..."
```

---

## ▶️ Running the Server
1. Clone this repo:

```bash
git clone https://github.com/Joshyxwa/AC-Acai.git
cd AC-Acai
```

2. Create and activate a virtual environment:
```bash
python -m venv .venv
source .venv/bin/activate   # Linux / macOS
.venv\Scripts\activate      # Windows
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Run the server:
```bash
python -m uvicorn first_model.server.server:app 
```

The server will be available at:
👉 http://127.0.0.1:8000

---

## 📖 API Endpoints

#### Health Check

`**GET** /health
- Returns simple health status.

Response:
```bash
{ "ok": true }
```

#### Projects

**GET** /check_projects
- List all projects.

Response:
```json
[
  {
    "project_id": 1,
    "created_at": "2025-08-30T10:00:00Z",
    "status": "In Review",
    "description": "Feature Authentication System",
    "name": "Auth Project"
  }
]
```

**GET** /get_project?project_id={id}: Fetch project details including documents.


#### Documents

**GET** /get_document?project_id={id}&document_id={doc_id}
- Fetch a document, including highlights, comments, and conversation threads.

Response:
```json
{
  "title": "Technical Design Document (TDD): Creator Connect",
  "content": "...",
  "highlights": [
    {
      "id": 12,
      "highlighting": [{ "start": 120, "end": 200 }],
      "reason": "Potential GDPR violation",
      "clarification_qn": "What safeguards exist?",
      "comments": [
        {
          "id": 1,
          "author": "GeoCompliance AI",
          "timestamp": "2025-08-30 12:00:00",
          "content": "This feature may lack safeguards...",
          "type": "system"
        }
      ]
    }
  ]
}
```

#### Comments / Highlights

**POST** /add_comment
- Add a new user comment for a highlight.

Body:
```json
{
  "highlight-id": 12,
  "document-id": 3,
  "project-id": 1,
  "user_response": "We should add consent flow",
  "author": "User"
}
```

Response:
```json
{ "ok": true, "message": "Comment added" }
```

**POST** /get_highlight_response
- Add a reply to a highlight. Will store a message in Supabase and return it.

Body:
```json
{
  "highlight-id": 12,
  "document-id": 3,
  "project-id": 1,
  "user_response": "Can this be flagged?"
}
```
Response:
```json
{
  "id": 55,
  "author": "GeoCompliance AI",
  "timestamp": "2025-08-30 12:01:00",
  "content": "Please review GDPR guidelines section 4.2",
  "type": "system"
}
```

#### Laws

**POST** /add_law
- Upload a .txt file containing law text. (Accepts only plain text files.)

Response:
```
{ "ok": true, "message": "File uploaded and printed successfully." }
```

#### New Audit

**POST** /new_audit
- Kick off a new project audit. Generates issues, evidence, conversations, and first messages.

Body:
```json
{ "project_id": "1" }
```
Response:
```json
{ "ok": true, "message": "Audit created" }
```

#### Synthesise Report

**POST** /generate_report
- Generate a full report for the project based on the latest audit. 

Body:
```json
{ "project_id": "1" }
```
Response:
```json
{ "ok": true, "report": "..." }
```

---

🛠 Development Notes
	•	Default dev server runs at http://127.0.0.1:8000.
    •	Front-End React App at http://127.0.0.1:8080.

