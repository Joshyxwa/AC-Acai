Here you go — a complete API_Documentation.md file you can save directly in your repo:

# GeoCompliance Mock Server – API Documentation

This document outlines the available API endpoints, expected inputs, and outputs for the FastAPI mock server.

---

## Base URL

http://localhost:8000

---

### **GET** `/health`
Check if the server is running.

- **Input:** None  
- **Output:**
```json
{ "ok": true }
```
Curl Example:
```bash
curl -X GET "http://localhost:8000/health"
```
JavaScript Example:
```js
fetch("http://localhost:8000/health")
  .then(res => res.json())
  .then(data => console.log(data));
```

⸻

### **GET** /check_projects

Retrieve a list of all available projects.
	•	Input: None
	•	Output:
Array of project summaries:
```json
[
  {
    "id": "1",
    "title": "Feature Authentication System",
    "lastModified": "2 hours ago",
    "documents": 3,
    "collaborators": 5,
    "status": "In Review"
  }
]
```
Curl Example:
```bash
curl -X GET "http://localhost:8000/check_projects"
```
JavaScript Example:
```js
fetch("http://localhost:8000/check_projects")
  .then(res => res.json())
  .then(projects => console.log(projects));
```

⸻

### **GET** /get_project

Retrieve details about a specific project.
	•	Input (query param):
```
project_id=<string>
```
Example: /get_project?project_id=1

	•	Output:
```json
{
  "id": "1",
  "title": "Feature Authentication System",
  "documents": [
    { "id": "tdd-1", "title": "Technical Design Document", "type": "TDD", "status": "flagged" }
  ]
}
```
Curl Example:
```bash
curl -X GET "http://localhost:8000/get_project?project_id=1"
```
JavaScript Example:
```js
fetch("http://localhost:8000/get_project?project_id=1")
  .then(res => res.json())
  .then(project => console.log(project));
```

⸻

### **GET** /get_document

Retrieve the content and highlights of a document.
	•	Input (query params):
```
project_id=<string>
document_id=<string>
```
Example: /get_document?project_id=1&document_id=tdd-1

	•	Output:
```json
{
  "title": "Technical Design Document (TDD): Creator Connect",
  "content": "... full document text ...",
  "highlights": [
    {
      "id": "highlight-1",
      "start": 658,
      "end": 784,
      "text": "The service validates mentor eligibility...",
      "comments": [
        {
          "id": "comment-1",
          "author": "GeoCompliance AI",
          "timestamp": "2 hours ago",
          "content": "The proposed Creator Connect feature lacks safeguards...",
          "type": "system"
        }
      ]
    }
  ]
}
```
Curl Example:
```bash
curl -X GET "http://localhost:8000/get_document?project_id=1&document_id=tdd-1"
```
JavaScript Example:
```js
fetch("http://localhost:8000/get_document?project_id=1&document_id=tdd-1")
  .then(res => res.json())
  .then(document => console.log(document));
```

⸻

### **POST** /get_highlight_response

Submit a user response to a highlight. The server generates an automated compliance/system reply.
	•	Input (JSON body):
```json
{
  "highlight-id": "highlight-2",
  "document-id": "tdd-1",
  "project-id": "1",
  "user_response": "Let's ensure we have explicit consent screens for EU users."
}
```
	•	Output (system reply):
```json
{
  "id": "response-1735604822000",
  "author": "GeoCompliance AI",
  "timestamp": "Just now",
  "content": "Thank you for your input. Based on your comment \"Let's ensure...\", I recommend reviewing the latest GDPR guidelines section 4.2...",
  "type": "system"
}
```
Curl Example:
```bash
curl -X POST "http://localhost:8000/get_highlight_response" \
  -H "Content-Type: application/json" \
  -d '{
        "highlight-id": "highlight-2",
        "document-id": "tdd-1",
        "project-id": "1",
        "user_response": "Let'\''s ensure we have explicit consent screens for EU users."
      }'
```
JavaScript Example:
```js
fetch("http://localhost:8000/get_highlight_response", {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({
    "highlight-id": "highlight-2",
    "document-id": "tdd-1",
    "project-id": "1",
    "user_response": "Let's ensure we have explicit consent screens for EU users."
  })
})
.then(res => res.json())
.then(reply => console.log(reply));
```

⸻

### **POST** /add_comment

Submit a user comment to a highlight. (No automated system reply is generated.)
	•	Input (JSON body):
```json
{
  "highlight-id": "highlight-1",
  "document-id": "tdd-1",
  "project-id": "1",
  "user_response": "We will add age verification and parental consent for minors.",
  "author": "Sarah Kim"
}
```
Output (confirmation only):
```json
{
  "ok": true,
  "message": "Comment added"
}
```
Curl Example:
```bash
curl -X POST "http://localhost:8000/add_comment" \
  -H "Content-Type: application/json" \
  -d '{
        "highlight-id": "highlight-1",
        "document-id": "tdd-1",
        "project-id": "1",
        "user_response": "We will add age verification and parental consent for minors.",
        "author": "Sarah Kim"
      }'
```
JavaScript Example:
```js
fetch("http://localhost:8000/add_comment", {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({
    "highlight-id": "highlight-1",
    "document-id": "tdd-1",
    "project-id": "1",
    "user_response": "We will add age verification and parental consent for minors.",
    "author": "Sarah Kim"
  })
})
.then(res => res.json())
.then(result => console.log(result));
```

⸻

Notes
	•	All responses are currently dummy data stored in memory.
	•	Data resets when the server restarts.
	•	In production, you would connect to a persistent database.

