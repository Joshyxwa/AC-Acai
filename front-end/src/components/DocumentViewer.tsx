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
  highlighting: Array<{ start: number; end: number }>;
  reason?: string;
  clarification_qn?: string;
  text?: string;
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
        highlighting: [
          { start: 658, end: 784 },
          { start: 850, end: 890 }
        ],
        reason: "The service validates mentor eligibility against the Spanner rule engine",
        clarification_qn: "The PRD mentions 'robust safeguards to prevent bad actors from exploiting this feature to contact minors inappropriately' but doesn't specify how the system will detect and prevent malicious actors from creating multiple fake verified accounts or engaging in systematic targeting of young creators. What specific technical controls are planned to address coordinated predatory behavior across multiple mentor accounts?",
        comments: [
          {
            id: "comment-1",
            author: "GeoCompliance AI",
            timestamp: "2 hours ago",
            content: "The proposed Creator Connect feature lacks critical safeguards to prevent predatory interactions with minors. Specifically, there are no explicit age verification mechanisms, parental consent requirements, or robust off-platform communication prevention strategies that would block a malicious actor from exploiting the mentorship feature to groom a vulnerable minor.",
            type: "system" as const
          }
        ]
      },
      {
        id: "highlight-2", 
        highlighting: [
          { start: 1015, end: 1108 }
        ],
        reason: "Privacy concerns with user profile data access",
        clarification_qn: "What specific consent mechanisms will be implemented to comply with GDPR and CCPA requirements when accessing user profile data for mentorship eligibility?",
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
      },
      {
        id: "highlight-3",
        highlighting: [
          { start: 1050, end: 1150 }
        ],
        reason: "Security audit requirement for data access patterns",
        clarification_qn: "How will the system log and audit access to sensitive user profile data to comply with SOX and security audit requirements?",
        comments: [
          {
            id: "comment-4",
            author: "Security Team",
            timestamp: "45 minutes ago",
            content: "This data access pattern needs comprehensive audit logging. We should implement detailed access logs including timestamp, requesting service, user ID, and data fields accessed.",
            type: "system" as const
          }
        ]
      }
    ]
  }
};

export const DocumentViewer = ({ documentId, projectId }: DocumentViewerProps) => {
  const [activeComment, setActiveComment] = useState<string | null>(null);
  const [selectedComment, setSelectedComment] = useState<string | null>(null);
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

  const scrollToComment = (highlightId: string) => {
    // Use requestAnimationFrame to ensure DOM has updated after state change
    requestAnimationFrame(() => {
      const commentElement = globalThis.document.getElementById(`comment-${highlightId}`);
      const commentsContainer = globalThis.document.querySelector('.comments-container');
      
      if (commentElement && commentsContainer) {
        const containerRect = commentsContainer.getBoundingClientRect();
        const elementRect = commentElement.getBoundingClientRect();
        
        // Calculate scroll position to show comment near the top with some padding
        // Add 20px padding from the top of the scrollable area
        const offsetFromTop = 20;
        const scrollTop = commentsContainer.scrollTop + (elementRect.top - containerRect.top) - offsetFromTop;
        
        commentsContainer.scrollTo({
          top: Math.max(0, scrollTop), // Ensure we don't scroll to negative values
          behavior: 'smooth'
        });
      }
    });
  };

  const renderContentWithHighlights = () => {
    const { content } = doc;
    const elements: JSX.Element[] = [];
    let elementKey = 0;

    // Filter highlights based on selected comment
    const visibleHighlights = selectedComment 
      ? highlights.filter(h => h.id === selectedComment)
      : highlights;

    // Create a list of all highlight ranges with their IDs
    const ranges: Array<{ start: number; end: number; highlightId: string; rangeIndex: number }> = [];
    
    visibleHighlights.forEach((highlight) => {
      highlight.highlighting.forEach((range, rangeIndex) => {
        ranges.push({
          start: range.start,
          end: range.end,
          highlightId: highlight.id,
          rangeIndex
        });
      });
    });

    // Sort ranges by start position
    ranges.sort((a, b) => a.start - b.start);

    // Merge overlapping ranges to handle multiple comments on same text
    const mergedRanges: Array<{ 
      start: number; 
      end: number; 
      highlightIds: string[]; 
      isFirst: Record<string, boolean>;
    }> = [];

    ranges.forEach((range) => {
      // Check if this range overlaps with any existing merged range
      let merged = false;
      for (const mergedRange of mergedRanges) {
        if (range.start < mergedRange.end && range.end > mergedRange.start) {
          // Overlapping - merge them
          mergedRange.start = Math.min(mergedRange.start, range.start);
          mergedRange.end = Math.max(mergedRange.end, range.end);
          if (!mergedRange.highlightIds.includes(range.highlightId)) {
            mergedRange.highlightIds.push(range.highlightId);
            mergedRange.isFirst[range.highlightId] = range.rangeIndex === 0;
          }
          merged = true;
          break;
        }
      }
      
      if (!merged) {
        // No overlap - create new merged range
        mergedRanges.push({
          start: range.start,
          end: range.end,
          highlightIds: [range.highlightId],
          isFirst: { [range.highlightId]: range.rangeIndex === 0 }
        });
      }
    });

    // Sort merged ranges by start position
    mergedRanges.sort((a, b) => a.start - b.start);

    let lastIndex = 0;

    mergedRanges.forEach((mergedRange) => {
      // Add text before highlight range
      if (lastIndex < mergedRange.start) {
        const beforeText = content.slice(lastIndex, mergedRange.start);
        elements.push(
          <span key={elementKey++} className="whitespace-pre-wrap">
            {beforeText}
          </span>
        );
      }

      // Add highlighted text range
      const highlightText = content.slice(mergedRange.start, mergedRange.end);
      const hasMultipleComments = mergedRange.highlightIds.length > 1;
      const isActive = mergedRange.highlightIds.some(id => activeComment === id);
      const primaryHighlightId = mergedRange.highlightIds[0];
      const firstHighlightId = mergedRange.highlightIds.find(id => mergedRange.isFirst[id]) || primaryHighlightId;

      elements.push(
        <span
          key={`merged-${mergedRange.highlightIds.join('-')}-${mergedRange.start}`}
          id={`highlight-${firstHighlightId}`}
          className={`cursor-pointer px-1 rounded transition-colors border-l-2 ${
            hasMultipleComments 
              ? `bg-orange-200 hover:bg-orange-300 ${isActive ? 'border-l-blue-500 bg-orange-300' : 'border-l-orange-400'}` 
              : `bg-yellow-200 hover:bg-yellow-300 ${isActive ? 'border-l-blue-500 bg-yellow-300' : 'border-l-transparent'}`
          }`}
          title={hasMultipleComments ? `${mergedRange.highlightIds.length} comments on this text` : undefined}
          onClick={() => {
            let targetHighlightId = primaryHighlightId;
            
            if (hasMultipleComments) {
              // Cycle through highlights if multiple comments tag the same text
              const currentIndex = mergedRange.highlightIds.findIndex(id => id === activeComment);
              const nextIndex = (currentIndex + 1) % mergedRange.highlightIds.length;
              const nextHighlightId = mergedRange.highlightIds[nextIndex];
              setActiveComment(activeComment === nextHighlightId ? null : nextHighlightId);
              targetHighlightId = nextHighlightId;
            } else {
              setActiveComment(activeComment === primaryHighlightId ? null : primaryHighlightId);
              targetHighlightId = primaryHighlightId;
            }
            
            // Scroll to the currently active comment
            scrollToComment(targetHighlightId);
          }}
        >
          {highlightText}
          {hasMultipleComments && (
            <span className="ml-1 text-xs bg-orange-400 text-white rounded-full px-1 leading-none">
              {mergedRange.highlightIds.length}
            </span>
          )}
        </span>
      );

      lastIndex = mergedRange.end;
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
            {selectedComment && (
              <div className="mt-3 flex items-center gap-2 text-sm bg-blue-50 border border-blue-200 rounded-lg px-3 py-2">
                <span className="text-blue-700">
                  Showing highlights for selected comment only
                </span>
                <button
                  onClick={() => setSelectedComment(null)}
                  className="text-blue-600 hover:text-blue-800 underline"
                >
                  Clear selection
                </button>
              </div>
            )}
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
        selectedComment={selectedComment}
        onCommentClick={setActiveComment}
        onCommentSelect={setSelectedComment}
        onAddComment={addComment}
        onAddApiResponse={addApiResponse}
        projectId={projectId}
        documentId={documentId}
      />
    </div>
  );
};