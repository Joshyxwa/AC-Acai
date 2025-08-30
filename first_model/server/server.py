from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import List, Dict, Optional, Literal
from datetime import datetime, timezone
from database.Database import Database

app = FastAPI(title="GeoCompliance Mock Server", version="0.1.0")
dc = Database()

# --- CORS (adjust origins as needed) ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],           # replace with your frontend origin(s) for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------- Dummy Data Stores ----------
projects = [
    {
        "id": "1",
        "title": "Feature Authentication System TEST",
        "lastModified": "2 hours ago",
        "documents": 3,
        "collaborators": 5,
        "status": "In Review",
    },
    {
        "id": "2",
        "title": "Payment Gateway Integration TEST",
        "lastModified": "1 day ago",
        "documents": 5,
        "collaborators": 3,
        "status": "Flagged",
    },
    {
        "id": "3",
        "title": "User Data Analytics Feature TEST",
        "lastModified": "3 days ago",
        "documents": 2,
        "collaborators": 4,
        "status": "Compliant",
    },
    {
        "id": "4",
        "title": "Social Media Integration TEST",
        "lastModified": "1 week ago",
        "documents": 4,
        "collaborators": 2,
        "status": "In Review",
    },
]

# projectId -> project details
project_details: Dict[str, Dict] = {
    "1": {
        "id": "1",
        "title": "Feature Authentication System TEST",
        "documents": [
            {"id": "tdd-1", "title": "Technical Design Document", "type": "TDD", "status": "flagged"},
            {"id": "prd-1", "title": "Product Requirements", "type": "PRD", "status": "review"},
            {"id": "security-1", "title": "Security Assessment", "type": "Security", "status": "compliant"},
            {"id": "tdd-2", "title": "Technical Design Document", "type": "TDD", "status": "flagged"},
            {"id": "prd-2", "title": "Product Requirements", "type": "PRD", "status": "review"},
            {"id": "security-2", "title": "Security Assessment", "type": "Security", "status": "compliant"},
        ],
    }
    # add more projects here as needed
}

# documentId content (scoped within project "1" for demo)
document_content: Dict[str, Dict] = {
    "tdd-1": {
        "title": "Technical Design Document (TDD): Creator Connect",
        "content": """
Document ID: TDD-2025-61C Title: TDD: Creator Connect Service (V1) Author: Kenji
Tanaka (Senior Software Engineer) Reviewers: Engineering Team, Security Team Related
PRD: PRD-2025-48B

1. Overview & Architecture

This document details the backend implementation for the Creator Connect feature. We will
introduce a new microservice, creator-connect-service, to orchestrate the business
logic of mentorship connections, acting as an intermediary between the user-facing client
and existing platform services. The flow is as follows: A request from an established
creator's client hits the new service. The service validates mentor eligibility against the
Spanner rule engine, checks for existing connections, and then calls the
direct-messaging-service to create the initial request message.

2. Service Dependencies

• user-profile-service: To fetch follower counts, account age, and verification
status.
• direct-messaging-service: To create and manage the communication channel.
• Spanner (Rule Engine): To host and execute the mentor eligibility rules.
• CDS (Compliance Detection System): For logging and retroactive analysis of
interactions.

3. New Service: creator-connect-service

Language: Go
Responsibilities:
◦ Expose endpoints for creating, accepting, and declining mentorship requests.
◦ Contain all business logic for eligibility and connection state management.
◦ Log all state changes and interactions to the CDS for analysis.

4. API Endpoints

Endpoint: POST /v1/mentorship/request

Description: Initiates a mentorship request from an established creator to an
aspiring creator.

Request Body:
JSON
{
  "mentor_id": "string",
}
        """,
        "highlights": [
            {
                "id": "highlight-1",
                "start": 658,
                "end": 784,
                "text": "The service validates mentor eligibility against the Spanner rule engine",
                "comments": [
                    {
                        "id": "comment-1",
                        "author": "GeoCompliance AI",
                        "timestamp": "2 hours ago",
                        "content": (
                            "The proposed Creator Connect feature lacks critical safeguards to prevent predatory interactions with minors. "
                            "Specifically, there are no explicit age verification mechanisms, parental consent requirements, or robust off-platform "
                            "communication prevention strategies that would block a malicious actor from exploiting the mentorship feature to groom a vulnerable minor."
                        ),
                        "type": "system",
                    }
                ],
            },
            {
                "id": "highlight-2",
                "start": 1015,
                "end": 1108,
                "text": "user-profile-service: To fetch follower counts, account age, and verification status",
                "comments": [
                    {
                        "id": "comment-2",
                        "author": "GeoCompliance AI",
                        "timestamp": "1 hour ago",
                        "content": (
                            "🚨 Privacy Law Alert: Accessing user profile data for mentorship eligibility may require explicit consent under GDPR (EU) "
                            "and CCPA (California). Recommend implementing consent flow before profile access."
                        ),
                        "type": "system",
                    },
                    {
                        "id": "comment-3",
                        "author": "Sarah Kim",
                        "timestamp": "30 minutes ago",
                        "content": "Good catch! We should add a consent checkbox in the mentorship request flow. @john can you update the UX flow?",
                        "type": "user",
                    },
                ],
            },
        ],
    }
}

laws = [] # temporary storage

# ---------- Pydantic Models ----------
class ProjectRow(BaseModel):
    project_id: int
    created_at: str
    status: str
    description: str
    name: str

class DocumentRow(BaseModel):
    doc_id: int
    created_at: str
    type: str          # e.g., "TDD", "PRD", "Security"
    content: str
    version: int
    project_id: int
    content_span: Optional[str] = None  # JSON/string span index if you need it

class Comment(BaseModel):
    id: int
    author: str
    timestamp: str
    content: str
    type: Literal["system", "user"]

class HighlightSpans(BaseModel):
    start: int
    end: int

class Highlight(BaseModel):
    id: int
    highlighting: List[HighlightSpans]
    reason: str
    clarification_qn: str
    comments: Optional[List[Comment]]

class DocumentPayload(BaseModel):
    title: str
    content: str
    highlights: List[Highlight]

class ProjectDetails(BaseModel):
    id: str
    title: str
    documents: List[DocumentRow]

class HighlightActionRequest(BaseModel):
    highlight_id: str = Field(..., alias="highlight-id")
    document_id: str = Field(..., alias="document-id")
    project_id: str = Field(..., alias="project-id")
    user_response: str
    author: Optional[str] = "User"

class HighlightResponse(Comment):
    pass

class Law(BaseModel):
    article_number: str
    type: Literal["recital", "law", "definition"]
    belongs_to: str
    contents: str
    word: Optional[str] = None  # only required if type=definition

# ---------- Helpers ----------
def _now_hhmm() -> str:
    # "Just now" is requested for the dummy; we’ll still compute id from epoch ms
    return "Just now"

def _epoch_ms_str() -> str:
    return str(int(datetime.now(tz=timezone.utc).timestamp() * 1000))

def _get_project_or_404(project_id: str) -> Dict:
    try:
        project_id_int = int(project_id)
        result = dc.get_project_with_documents(project_id=project_id_int)
        if result is None:
            raise HTTPException(status_code=404, detail="Project not found")
        return result
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid project_id format")
    except Exception:
        raise HTTPException(status_code=404, detail="Project not found")

def _get_document_or_404(project_id, document_id: str) -> Dict:
    result = dc.load_document_with_highlighting(int(project_id), int(document_id))

    try:
        result = dc.load_document_with_highlighting(int(project_id), int(document_id))
        # print(result)
        if result is None:
            raise HTTPException(status_code=404, detail="Document not found")
        return result
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid project_id or document_id format")
    except Exception:
        raise HTTPException(status_code=404, detail="Document not found")

def _find_highlight_or_404(doc: Dict, highlight_id: str) -> Dict:
    for h in doc.get("highlights", []):
        if h.get("id") == highlight_id:
            return h
    raise HTTPException(status_code=404, detail="Highlight not found")

# ---------- Endpoints ----------
@app.get("/health")
def health():
    return {"ok": True}

@app.get("/check_projects", response_model=List[ProjectRow])
def check_projects():
    return dc.load_all_projects()

@app.get("/get_project", response_model=ProjectDetails)
def get_project(project_id: str):
    proj = _get_project_or_404(project_id)
    return proj

@app.get("/get_document", response_model=DocumentPayload)
def get_document(project_id: str, document_id: str):
    # for demo we don't cross-validate that document belongs to project,
    # but you can enforce that if you store per-project docs
    doc = _get_document_or_404(project_id, document_id)
    return doc

@app.post("/get_highlight_response", response_model=HighlightResponse)
def get_highlight_response(req: HighlightActionRequest):
    _ = _get_project_or_404(req.project_id)
    doc = _get_document_or_404(req.document_id)
    hl = _find_highlight_or_404(doc, req.highlight_id)

    # Append a system response (dummy) and also echo it back
    generated_id = f"response-{_epoch_ms_str()}"
    response = {
        "id": generated_id,
        "author": "GeoCompliance AI",
        "timestamp": _now_hhmm(),
        "content": (
            f'Thank you for your input. Based on your comment "{req.user_response}", '
            "I recommend reviewing the latest GDPR guidelines section 4.2 for data processing compliance. "
            "This should address your concerns about user consent flows."
        ),
        "type": "system",
    }
    hl.setdefault("comments", []).append(response)
    return response

@app.post("/add_comment")
def add_comment(req: HighlightActionRequest):
    _ = _get_project_or_404(req.project_id)
    doc = _get_document_or_404(req.document_id)
    hl = _find_highlight_or_404(doc, req.highlight_id)

    comment = {
        "id": f"comment-{_epoch_ms_str()}",
        "author": req.author or "User",
        "timestamp": _now_hhmm(),
        "content": req.user_response,
        "type": "user",
    }
    hl.setdefault("comments", []).append(comment)
    return {"ok": True, "message": "Comment added"}

@app.post("/add_law")
def add_law(law: Law):
    # Validation: if type=definition, word must be provided
    if law.type == "definition" and not law.word:
        return {"ok": False, "message": "Word must be provided for definition type laws."}

    print(f"Adding law: {law.dict()}")
    # Add to "DB"
    laws.append(law.dict())
    return {"ok": True, "message": "Law added successfully", "law": law.dict()}

# Optional root
@app.get("/")
def root():
    return {"service": "GeoCompliance Mock Server", "endpoints": [
        "/check_projects",
        "/get_project?project_id=1",
        "/get_document?project_id=1&document_id=tdd-1",
        "/get_highlight_response",
        "/add_comment",
        "/health",
    ]}