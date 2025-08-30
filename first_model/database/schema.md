# Database Schema

## Project

Represents a project being audited.
	•	project_id (PK) – Unique identifier
	•	created_at – Timestamp when project was created
	•	status – Current status (In Review, Compliant, Flagged, etc.)
	•	description – Optional description of the project
	•	name – Name of the project

⸻

## Document

Stores documents (PRD, TDD, Security, etc.) under a project.
	•	doc_id (PK) – Unique identifier
	•	created_at – Timestamp when document was added
	•	type – Document type (PRD, TDD, Security)
	•	content – Full document text
	•	version – Document version number
	•	project_id (FK → Project.project_id) – Which project this document belongs to
	•	content_span – Annotated text with <spanX> markers for highlighting

⸻

## Audit

Represents an audit session for a project.
	•	audit_id (PK) – Unique identifier
	•	created_at – When the audit was started
	•	project_id (FK → Project.project_id) – Project being audited
	•	status – Status of the audit (in_progress, completed)

⸻

## Issue

Represents a compliance issue found during an audit.
	•	issue_id (PK) – Unique identifier
	•	created_at – When the issue was logged
	•	audit_id (FK → Audit.audit_id) – Audit this issue belongs to
	•	issue_description – Description of the compliance gap
	•	ent_id (FK → Article_Entry.ent_id) – Related law or article entry
	•	status – Status (open, resolved)
	•	evidence – JSON mapping { "doc_id": ["span19", "span20"] }
	•	clarification_qn – A clarifying question for users/AI

⸻

## Conversation

Links an issue to its conversation thread.
	•	conv_id (PK) – Unique identifier
	•	created_at – When conversation started
	•	audit_id (FK → Audit.audit_id) – Audit context
	•	issue_id (FK → Issue.issue_id) – Issue being discussed

⸻

## Message

Stores messages within a conversation.
	•	msg_id (PK) – Unique identifier
	•	created_at – When the message was posted
	•	type – "user" or "ai"
	•	content – Text of the message
	•	conv_id (FK → Conversation.conv_id) – Conversation this message belongs to

⸻

## Article_Entry

Stores laws, recitals, and definitions.
	•	ent_id (PK) – Unique identifier
	•	art_num – Article number (e.g. 13-63-101(2))
	•	type – "recital", "law", "definition"
	•	belongs_to – Bill or statute (e.g. S.B. 152 (2023))
	•	contents – The full legal text
	•	word – Only for definitions: which word it defines
	•	embedding – Optional vector field for semantic search
	•	created_at – Timestamp

⸻

## 🔗 Relationships
	•	Project → Document (1-to-many)
	•	Project → Audit (1-to-many)
	•	Audit → Issue (1-to-many)
	•	Issue → Conversation (1-to-1, typically)
	•	Conversation → Message (1-to-many)
	•	Issue.ent_id → Article_Entry.ent_id (links issues to legal references)