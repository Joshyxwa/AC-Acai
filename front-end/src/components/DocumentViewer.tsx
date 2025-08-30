import { useState, useEffect } from "react";
import { SideComments } from "@/components/SideComments";
import { RefreshCw } from "lucide-react";
import { getDocument, addComment as apiAddComment } from "@/lib/api";

interface DocumentViewerProps {
  documentId: string;
  projectId: string;
}

interface Comment {
  id: string;
  author: string;
  timestamp: string;
  content: string;
  type: "system" | "user";
}

interface Highlight {
  id: string;
  start: number;
  end: number;
  text: string;
  comments: Comment[];
}

interface DocumentData {
  title: string;
  content: string;
  highlights: Highlight[];
}

// Mock document content with highlighted regions
const documentContent = {
  "tdd-1": {
    title: "Technical Design Document (TDD): Creator Connect",
    content: `
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
    `,
    highlights: [
      {
        id: "highlight-1",
        start: 658,
        end: 784,
        text: "The service validates mentor eligibility against the Spanner rule engine",
        comments: [
          {
            id: "comment-1",
            author: "GeoCompliance AI",
            timestamp: "2 hours ago",
            // content: "⚠️ Geographic Compliance Issue: This eligibility validation may need to comply with regional mentorship regulations in the EU under Digital Services Act. Consider implementing region-specific validation rules.",
            content: "The proposed Creator Connect feature lacks critical safeguards to prevent predatory interactions with minors. Specifically, there are no explicit age verification mechanisms, parental consent requirements, or robust off-platform communication prevention strategies that would block a malicious actor from exploiting the mentorship feature to groom a vulnerable minor.",
            type: "system" as const
          }
        ]
      },
      {
        id: "highlight-2", 
        start: 1015,
        end: 1108,
        text: "user-profile-service: To fetch follower counts, account age, and verification status",
        comments: [
          {
            id: "comment-2",
            author: "GeoCompliance AI",
            timestamp: "1 hour ago", 
            content: "🚨 Privacy Law Alert: Accessing user profile data for mentorship eligibility may require explicit consent under GDPR (EU) and CCPA (California). Recommend implementing consent flow before profile access.",
            type: "system" as const
          },
          {
            id: "comment-3",
            author: "Sarah Kim",
            timestamp: "30 minutes ago",
            content: "Good catch! We should add a consent checkbox in the mentorship request flow. @john can you update the UX flow?",
            type: "user" as const
          }
        ]
      }
    ]
  }
};

export const DocumentViewer = ({ documentId, projectId }: DocumentViewerProps) => {
  const [activeComment, setActiveComment] = useState<string | null>(null);
  const [highlights, setHighlights] = useState<Highlight[]>([]);
  const [document, setDocument] = useState<DocumentData | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Fallback document data
  const fallbackDoc = documentContent[documentId as keyof typeof documentContent];

  const fetchDocument = async () => {
    setIsLoading(true);
    setError(null);
    
    try {
      const data = await getDocument(projectId, documentId);
      setDocument(data);
      setHighlights(data.highlights || []);
    } catch (err) {
      console.error('Error fetching document:', err);
      setError(err instanceof Error ? err.message : 'Failed to fetch document');
      // Use fallback data on error
      if (fallbackDoc) {
        setDocument(fallbackDoc);
        setHighlights(fallbackDoc.highlights || []);
      }
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchDocument();
  }, [documentId, projectId]);

  if (isLoading) {
    return (
      <div className="flex-1 p-8 flex items-center justify-center">
        <div className="text-center">
          <RefreshCw className="h-8 w-8 animate-spin mx-auto mb-4 text-primary" />
          <p className="text-muted-foreground">Loading document...</p>
        </div>
      </div>
    );
  }

  const doc = document;

  if (!doc) {
    return (
      <div className="flex-1 p-8 flex items-center justify-center">
        <div className="text-center">
          <h2 className="text-lg font-medium text-foreground mb-2">Document not found</h2>
          <p className="text-muted-foreground">The selected document could not be loaded.</p>
        </div>
      </div>
    );
  }

  const addComment = async (highlightId: string, content: string) => {
    const tempComment = {
      id: `temp-${Date.now()}`,
      author: "Current User",
      timestamp: "Just now",
      content: content,
      type: "user" as const
    };

    // Optimistically update UI
    setHighlights(prev => prev.map(highlight => {
      if (highlight.id === highlightId) {
        return {
          ...highlight,
          comments: [...highlight.comments, tempComment]
        };
      }
      return highlight;
    }));

    try {
      await apiAddComment({
        'highlight-id': highlightId,
        'document-id': documentId,
        'project-id': projectId,
        'user_response': content,
        'author': 'Current User'
      });

      // Comment was successfully added to server
      console.log('Comment added successfully');
    } catch (err) {
      console.error('Error adding comment:', err);
      // Comment will remain in UI even if server call fails
    }
  };

  const addApiResponse = (highlightId: string, response: any) => {
    setHighlights(prev => prev.map(highlight => {
      if (highlight.id === highlightId) {
        return {
          ...highlight,
          comments: [...highlight.comments, response]
        };
      }
      return highlight;
    }));
  };

  const renderContentWithHighlights = () => {
    const { content } = doc;
    let lastIndex = 0;
    const elements: JSX.Element[] = [];
    let elementKey = 0;

    // Sort highlights by start position
    const sortedHighlights = [...highlights].sort((a, b) => a.start - b.start);

    sortedHighlights.forEach((highlight) => {
      // Add text before highlight
      if (lastIndex < highlight.start) {
        const beforeText = content.slice(lastIndex, highlight.start);
        elements.push(
          <span key={elementKey++} className="whitespace-pre-wrap">
            {beforeText}
          </span>
        );
      }

      // Add highlighted text
      elements.push(
        <span
          key={highlight.id}
          id={`highlight-${highlight.id}`}
          className={`bg-yellow-200 hover:bg-yellow-300 cursor-pointer px-1 rounded transition-colors border-l-2 ${
            activeComment === highlight.id ? 'border-l-blue-500 bg-yellow-300' : 'border-l-transparent'
          }`}
          onClick={() => setActiveComment(activeComment === highlight.id ? null : highlight.id)}
        >
          {highlight.text}
        </span>
      );

      lastIndex = highlight.end;
    });

    // Add remaining text
    if (lastIndex < content.length) {
      const remainingText = content.slice(lastIndex);
      elements.push(
        <span key={elementKey++} className="whitespace-pre-wrap">
          {remainingText}
        </span>
      );
    }

    return elements;
  };

  return (
    <div className="flex-1 flex h-full overflow-hidden">
      {/* Document Content */}
      <div className="flex-1 overflow-y-auto h-full document-container">
        <div className="max-w-4xl mx-auto p-8 pr-4">
          {/* Document Header */}
          <div className="mb-8 pb-4 border-b">
            <h1 className="text-2xl font-bold text-foreground mb-2">{doc.title}</h1>
            <div className="flex items-center gap-4 text-sm text-muted-foreground">
              <span>Last modified: 2 hours ago</span>
              <span>•</span>
              <span>{highlights.length} flagged issues</span>
              <span>•</span>
              <span>In Review</span>
              {error && (
                <>
                  <span>•</span>
                  <span className="text-red-600">Using offline data</span>
                </>
              )}
            </div>
          </div>

          {/* Document Content */}
          <div className="prose prose-neutral max-w-none">
            <div className="text-foreground leading-relaxed font-mono text-sm">
              {renderContentWithHighlights()}
            </div>
          </div>
        </div>
      </div>

      {/* Side Comments */}
      <SideComments 
        highlights={highlights}
        activeComment={activeComment}
        onCommentClick={setActiveComment}
        onAddComment={addComment}
        onAddApiResponse={addApiResponse}
        projectId={projectId}
        documentId={documentId}
      />
    </div>
  );
};