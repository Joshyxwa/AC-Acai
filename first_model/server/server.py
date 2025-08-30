from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import List, Dict, Optional, Literal
from datetime import datetime, timezone
from ..database.Database import Database
from ..io.IO import IO
from fastapi import UploadFile, File, Depends, Request
from fastapi import BackgroundTasks

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

# ---------- Dummy Data Stores (commented out) ----------
'''
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
'''

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

class AuditRunIn(BaseModel):
    project_id: int
    max_scenarios: int = 3
    create_audit: Optional[bool] = False
    async_run: Optional[bool] = False

# ---------- Helpers ----------
def _now_hhmm() -> str:
    # "Just now" is requested for the dummy; we’ll still compute id from epoch ms
    return "Just now"

def _epoch_ms_str() -> str:
    return str(int(datetime.now(tz=timezone.utc).timestamp() * 1000))

def _get_project_or_404(project_id: str) -> Dict:
    io = getattr(app.state, "io", None)
    if not io:
        raise HTTPException(status_code=500, detail="IO not initialized")
    try:
        project_id_int = int(project_id)
        res = io.get_project_with_documents(project_id_int)
        if not res.get("ok"):
            raise HTTPException(status_code=404, detail=res.get("error") or "Project not found")
        if not res.get("data"):
            raise HTTPException(status_code=404, detail="Project not found")
        return res["data"]
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid project_id format")

def _get_document_or_404(project_id: str, document_id: str) -> Dict:
    io = getattr(app.state, "io", None)
    if not io:
        raise HTTPException(status_code=500, detail="IO not initialized")
    try:
        pid = int(project_id)
        did = int(document_id)
        res = io.load_document_with_highlighting(pid, did)
        if not res.get("ok"):
            raise HTTPException(status_code=404, detail=res.get("error") or "Document not found")
        if not res.get("data"):
            raise HTTPException(status_code=404, detail="Document not found")
        return res["data"]
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid project_id or document_id format")

def _find_highlight_or_404(doc: Dict, highlight_id: str) -> Dict:
    for h in doc.get("highlights", []):
        if str(h.get("id")) == str(highlight_id):
            return h
    raise HTTPException(status_code=404, detail="Highlight not found")

def audit_project(project_id: int):
    documents = Database.load_document(project_id=project_id)
    print(documents)
    pass    

# ---------- Endpoints ----------
@app.on_event("startup")
async def startup_event():
    # Single IO instance for the app lifetime
    app.state.io = IO()

def get_io(request: Request) -> IO:
    io = getattr(request.app.state, "io", None)
    if not io:
        raise HTTPException(status_code=500, detail="IO not initialized")
    return io

@app.get("/health")
def health():
    return {"ok": True}

@app.get("/status")
def status(io: IO = Depends(get_io)):
    return io.status()

@app.get("/check_projects", response_model=List[ProjectRow])
def check_projects(io: IO = Depends(get_io)):
    res = io.list_projects()
    if not res.get("ok"):
        raise HTTPException(status_code=500, detail=res.get("error") or "Failed to load projects")
    return res.get("data") or []

@app.get("/get_project", response_model=ProjectDetails)
def get_project(project_id: str):
    proj = _get_project_or_404(project_id)
    return proj

@app.get("/get_document", response_model=DocumentPayload)
def get_document(project_id: str, document_id: str):
    doc = _get_document_or_404(project_id, document_id)
    return doc

@app.post("/get_highlight_response", response_model=HighlightResponse)
def get_highlight_response(req: HighlightActionRequest):
    _ = _get_project_or_404(req.project_id)
    doc = _get_document_or_404(req.project_id, req.document_id)
    hl = _find_highlight_or_404(doc, req.highlight_id)

    # TODO: Append a system response (dummy) and also echo it back
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
    doc = _get_document_or_404(req.project_id, req.document_id)
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
def add_law(law: Law, io: IO = Depends(get_io)):
    """Accepts JSON payload for adding a law/recital/definition (used by frontend)."""
    if law.type == "definition" and not law.word:
        return {"ok": False, "message": "Word must be provided for definition type laws."}
    if law.type == "definition":
        res = io.save_law_definition(art_num=law.article_number, belongs_to=law.belongs_to, content=law.contents, word=law.word)  # type: ignore[arg-type]
    else:
        res = io.save_law_document(art_num=law.article_number, belongs_to=law.belongs_to, type=law.type, contents=law.contents, word=law.word)
    if not res.get("ok"):
        raise HTTPException(status_code=500, detail=res.get("error") or "Failed to save law")
    return {"ok": True, "message": "Law added successfully", "law": law.dict()}

@app.post("/add_law_file")
async def add_law_file(file: UploadFile = File(...)):
    """Optional file-upload endpoint for adding laws from a .txt file."""
    if file.content_type != "text/plain":
        return {"ok": False, "message": "Only .txt files are accepted."}
    try:
        contents = await file.read()
        text = contents.decode("utf-8")
        print(text)
        return {"ok": True, "message": "File uploaded and printed successfully."}
    except Exception as e:
        return {"ok": False, "message": f"Failed to process file: {str(e)}"}

# ---------- Chatbox / Conversation API ----------
class ChatboxCreateIn(BaseModel):
    conv_id: Optional[int] = None
    preload: bool = True

class MessageIn(BaseModel):
    conv_id: int
    content: str
    run_inference: bool = True

@app.post("/chatbox/create")
def chatbox_create(payload: ChatboxCreateIn, io: IO = Depends(get_io)):
    res = io.get_or_create_chatbox(conv_id=payload.conv_id, preload=payload.preload)
    if not res["ok"]:
        raise HTTPException(status_code=500, detail=res["error"])
    return res["data"]

@app.get("/chatbox/{conv_id}/history")
def chatbox_history(conv_id: int, reload: bool = False, io: IO = Depends(get_io)):
    res = io.get_history(conv_id, reload=reload)
    if not res["ok"]:
        raise HTTPException(status_code=404 if res["error"] == "chatbox not found; call get_or_create_chatbox first" else 500, detail=res["error"])
    return res["data"]

@app.post("/chatbox/message")
def chatbox_message(payload: MessageIn, io: IO = Depends(get_io)):
    # Ensure chatbox exists
    ensure = io.get_or_create_chatbox(conv_id=payload.conv_id, preload=False)
    if not ensure["ok"]:
        raise HTTPException(status_code=500, detail=ensure["error"])

    res = io.handle_incoming(payload.conv_id, payload.content, run_inference=payload.run_inference)
    if not res["ok"]:
        raise HTTPException(status_code=500, detail=res["error"])
    return res["data"]

# Optional root
@app.get("/")
def root():
    return {"service": "GeoCompliance Mock Server", "endpoints": [
        "/check_projects",
        "/get_project?project_id=1",
        "/get_document?project_id=1&document_id=tdd-1",
        "/get_highlight_response",
        "/add_comment",
    "/add_law",
    "/add_law_file",
        "/health",
        "/status",
        "/chatbox/create",
        "/chatbox/{conv_id}/history",
        "/chatbox/message",
        "/audit/run",
    ]}

@app.post("/audit/run")
def audit_run(payload: AuditRunIn, io: IO = Depends(get_io), background_tasks: BackgroundTasks = None):
    # If requested, create an Audit row first and run with status updates
    if payload.create_audit:
        created = io.create_audit(project_id=payload.project_id, status="pending")
        if not created.get("ok"):
            raise HTTPException(status_code=500, detail=created.get("error") or "Failed to create audit")
        audit_obj = created.get("data") or {}
        audit_id = audit_obj.get("audit_id") if isinstance(audit_obj, dict) else None
        if audit_id is None:
            # Try to look up the most recent audit for project as a fallback
            try:
                rows = io.database.supabase.table("Audit").select("audit_id").eq("project_id", payload.project_id).order("created_at", desc=True).limit(1).execute().data
                audit_id = (rows[0]["audit_id"] if rows else None)
            except Exception:
                pass
        if audit_id is None:
            raise HTTPException(status_code=500, detail="Failed to determine audit_id")
        if payload.async_run:
            # Queue background execution and return immediately
            if background_tasks is None:
                raise HTTPException(status_code=500, detail="Background tasks not available")
            background_tasks.add_task(io.run_audit_pipeline_for_audit_and_update, audit_id=audit_id, project_id=payload.project_id, max_scenarios=payload.max_scenarios)
            return {"started": True, "audit_id": audit_id, "status": "in_progress"}
        res = io.run_audit_pipeline_for_audit_and_update(audit_id=audit_id, project_id=payload.project_id, max_scenarios=payload.max_scenarios)
    else:
        if payload.async_run:
            # Ensure an audit exists to track status, then run in background
            created = io.create_audit(project_id=payload.project_id, status="pending")
            if not created.get("ok"):
                raise HTTPException(status_code=500, detail=created.get("error") or "Failed to create audit")
            audit_obj = created.get("data") or {}
            audit_id = audit_obj.get("audit_id") if isinstance(audit_obj, dict) else None
            if audit_id is None:
                # Fallback: lookup most recent audit for project
                try:
                    rows = io.database.supabase.table("Audit").select("audit_id").eq("project_id", payload.project_id).order("created_at", desc=True).limit(1).execute().data
                    audit_id = (rows[0]["audit_id"] if rows else None)
                except Exception:
                    pass
            if audit_id is None:
                raise HTTPException(status_code=500, detail="Failed to determine audit_id for async run")
            if background_tasks is None:
                raise HTTPException(status_code=500, detail="Background tasks not available")
            background_tasks.add_task(io.run_audit_pipeline_for_audit_and_update, audit_id=audit_id, project_id=payload.project_id, max_scenarios=payload.max_scenarios)
            return {"started": True, "audit_id": audit_id, "status": "in_progress"}
        res = io.run_audit_pipeline(project_id=payload.project_id, max_scenarios=payload.max_scenarios)
    if not res.get("ok"):
        raise HTTPException(status_code=500, detail=res.get("error") or "Audit pipeline failed")
    return res.get("data")