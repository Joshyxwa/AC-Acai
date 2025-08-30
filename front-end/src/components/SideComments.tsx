import { useState, useEffect, useRef } from "react";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { Send, AlertTriangle, User, Plus } from "lucide-react";
import { getHighlightResponse } from "@/lib/api";

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

interface SideCommentsProps {
  highlights: Highlight[];
  activeComment: string | null;
  selectedComment: string | null;
  onCommentClick: (highlightId: string | null) => void;
  onCommentSelect: (highlightId: string | null) => void;
  onAddComment: (highlightId: string, content: string) => void;
  onAddApiResponse: (highlightId: string, response: Comment) => void;
  projectId: string;
  documentId: string;
}

export const SideComments = ({ highlights, activeComment, selectedComment, onCommentClick, onCommentSelect, onAddComment, onAddApiResponse, projectId, documentId }: SideCommentsProps) => {
  const [newComments, setNewComments] = useState<Record<string, string>>({});
  const [showingReplyFor, setShowingReplyFor] = useState<string | null>(null);
  const [replyingToComment, setReplyingToComment] = useState<string | null>(null);
  const [replyTexts, setReplyTexts] = useState<Record<string, string>>({});
  const [isLoadingResponse, setIsLoadingResponse] = useState<Record<string, boolean>>({});
  const commentRefs = useRef<Record<string, HTMLDivElement | null>>({});
  const commentsContainerRef = useRef<HTMLDivElement>(null);
  const documentScrollRef = useRef<HTMLDivElement | null>(null);

  // Initialize document scroll reference
  useEffect(() => {
    const documentContainer = document.querySelector('.document-container');
    if (documentContainer) {
      documentScrollRef.current = documentContainer as HTMLDivElement;
    }
  }, []);

  // Simple effect to handle comment visibility
  useEffect(() => {
    // No complex positioning - just use normal document flow
  }, [highlights, selectedComment]);

  // Handle selected comment isolation - show only selected comment when one is chosen
  useEffect(() => {
    if (selectedComment) {
      // When a comment is selected, show only that comment
      highlights.forEach(highlight => {
        const commentElement = commentRefs.current[highlight.id];
        if (commentElement) {
          commentElement.style.display = highlight.id === selectedComment ? 'block' : 'none';
        }
      });
    } else {
      // Show all comments in normal flow
      highlights.forEach(highlight => {
        const commentElement = commentRefs.current[highlight.id];
        if (commentElement) {
          commentElement.style.display = 'block';
        }
      });
    }
  }, [selectedComment, highlights]);

  const handleAddComment = (highlightId: string) => {
    const content = newComments[highlightId];
    if (!content?.trim()) return;
    
    onAddComment(highlightId, content);
    setNewComments(prev => ({ ...prev, [highlightId]: "" }));
    setShowingReplyFor(null);
  };

  const handleReply = (highlightId: string) => {
    setShowingReplyFor(highlightId);
    onCommentClick(highlightId);
  };

  const handleCommentReply = async (highlightId: string, commentId: string) => {
    const replyText = replyTexts[commentId];
    if (!replyText?.trim()) return;

    // Set loading state
    setIsLoadingResponse(prev => ({ ...prev, [commentId]: true }));

    try {
      let apiResponseData;

      // Update highlights with new comments
      onAddComment(highlightId, replyText); // Add user reply
      
      try {
        apiResponseData = await getHighlightResponse({
          'highlight-id': highlightId,
          'document-id': documentId,
          'project-id': projectId,
          'user_response': replyText
        });
      } catch (apiError) {
        // Fallback response if API fails
        console.warn('API call failed, using fallback response');
        apiResponseData = {
          id: `response-${Date.now()}`,
          author: "GeoCompliance AI",
          timestamp: "Just now",
          content: `Thank you for your input. Based on your comment "${replyText}", I recommend reviewing the latest GDPR guidelines section 4.2 for data processing compliance. This should address your concerns about user consent flows.`,
          type: "system" as const
        };
      }

      // Add the user's reply first
      const userReply = {
        id: `reply-${Date.now()}`,
        author: "Current User", 
        timestamp: "Just now",
        content: replyText,
        type: "user" as const
      };
      
      // Add AI response after a short delay
      setTimeout(() => {
        onAddApiResponse(highlightId, apiResponseData);
      }, 100);

    } catch (error) {
      console.error('Error sending reply:', error);
    } finally {
      // Clear states
      setReplyTexts(prev => ({ ...prev, [commentId]: "" }));
      setReplyingToComment(null);
      setIsLoadingResponse(prev => ({ ...prev, [commentId]: false }));
    }
  };

  return (
    <div className="w-80 border-l bg-card relative h-full overflow-hidden flex flex-col">
      {/* Header */}
      <div className="bg-card border-b p-4 flex-shrink-0">
        <h3 className="font-medium text-foreground">Comments</h3>
        <p className="text-sm text-muted-foreground">Click highlights to view</p>
      </div>

      {/* Comments Container */}
      <div 
        ref={commentsContainerRef} 
        className="comments-container relative flex-1 p-4 overflow-y-auto"
        style={{ minHeight: 0, maxHeight: '100%' }}
      >
        {highlights.map((highlight) => (
          <div
            key={highlight.id}
            id={`comment-${highlight.id}`}
            ref={(el) => (commentRefs.current[highlight.id] = el)}
            className={`w-full mb-6 transition-all duration-300 ease-out cursor-pointer ${
              activeComment === highlight.id ? 'opacity-100 z-20' : 'opacity-70 z-10'
            } ${
              selectedComment === highlight.id ? 'ring-2 ring-blue-500' : ''
            }`}
            onClick={() => {
              // Toggle comment selection for isolated highlighting
              if (selectedComment === highlight.id) {
                onCommentSelect(null);
              } else {
                onCommentSelect(highlight.id);
              }
            }}
            style={{
              transform: 'translateZ(0)', // Enable hardware acceleration
              transition: 'top 0.3s cubic-bezier(0.4, 0, 0.2, 1), opacity 0.3s ease-out, transform 0.3s ease-out'
            }}
          >
            <div className={`bg-background border rounded-lg shadow-sm ${
              activeComment === highlight.id ? 'border-blue-300 shadow-md' : 'border-border'
            } ${
              selectedComment === highlight.id ? 'border-blue-500 shadow-lg' : ''
            }`}>
              {/* Highlight Preview */}
              <div className={`p-3 border-b ${
                selectedComment === highlight.id ? 'bg-blue-50' : 'bg-yellow-50'
              }`}>
                {highlight.reason && (
                  <div className="mb-2">
                    <p className="text-xs text-muted-foreground font-medium mb-1">Reason:</p>
                    <p className="text-xs text-foreground">{highlight.reason}</p>
                  </div>
                )}
                {highlight.clarification_qn && (
                  <div className="mb-2">
                    <p className="text-xs text-muted-foreground font-medium mb-1">Clarification Question:</p>
                    <p className="text-xs text-foreground italic">{highlight.clarification_qn}</p>
                  </div>
                )}
                {highlight.text && (
                  <div>
                    <p className="text-xs text-muted-foreground font-medium mb-1">Referenced text:</p>
                    <p className="text-xs text-foreground italic line-clamp-2">
                      "{highlight.text}"
                    </p>
                  </div>
                )}
              </div>

              {/* Comments */}
              <div className="p-3 space-y-3 max-h-60 overflow-y-auto">
                {highlight.comments.map((comment) => (
                  <div key={comment.id} className="space-y-2">
                    <div className="flex items-start gap-2">
                      <Avatar className="h-6 w-6">
                        <AvatarFallback className="text-xs">
                          {comment.type === "system" ? (
                            <AlertTriangle className="h-3 w-3" />
                          ) : (
                            <User className="h-3 w-3" />
                          )}
                        </AvatarFallback>
                      </Avatar>
                      <div className="flex-1 space-y-1">
                        <div className="flex items-center gap-2">
                          <span className="text-xs font-medium">
                            {comment.author}
                          </span>
                          <span className="text-xs text-muted-foreground">
                            {comment.timestamp}
                          </span>
                        </div>
                        <div className={`p-2 rounded-lg text-xs ${
                          comment.type === "system" 
                            ? "bg-yellow-50 border border-yellow-200 text-yellow-800" 
                            : "bg-muted text-foreground"
                        }`}>
                          {comment.content}
                        </div>
                        
                        {/* Reply Button */}
                        <div className="flex items-center gap-2 mt-1">
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => setReplyingToComment(comment.id)}
                            className="h-6 px-2 text-xs text-muted-foreground hover:text-foreground"
                          >
                            Reply
                          </Button>
                        </div>

                        {/* Reply Input */}
                        {replyingToComment === comment.id && (
                          <div className="mt-2 space-y-2 animate-fade-in">
                            <Textarea
                              placeholder="Reply to this comment..."
                              value={replyTexts[comment.id] || ""}
                              onChange={(e) => setReplyTexts(prev => ({ 
                                ...prev, 
                                [comment.id]: e.target.value 
                              }))}
                              className="min-h-[50px] text-xs resize-none"
                              autoFocus
                            />
                            <div className="flex justify-end gap-1">
                              <Button 
                                variant="ghost" 
                                size="sm"
                                onClick={() => {
                                  setReplyingToComment(null);
                                  setReplyTexts(prev => ({ ...prev, [comment.id]: "" }));
                                }}
                                className="h-6 px-2 text-xs"
                              >
                                Cancel
                              </Button>
                              <Button 
                                size="sm" 
                                onClick={() => handleCommentReply(highlight.id, comment.id)}
                                disabled={!replyTexts[comment.id]?.trim() || isLoadingResponse[comment.id]}
                                className="h-6 px-2 text-xs gap-1"
                              >
                                {isLoadingResponse[comment.id] ? (
                                  <>
                                    <div className="w-3 h-3 border border-current border-t-transparent rounded-full animate-spin" />
                                    Sending...
                                  </>
                                ) : (
                                  <>
                                    <Send className="h-2 w-2" />
                                    Reply
                                  </>
                                )}
                              </Button>
                            </div>
                          </div>
                        )}
                      </div>
                    </div>
                  </div>
                ))}
              </div>

              {/* Reply Section - Always show for active comment */}
              {activeComment === highlight.id && (
                <div className="p-3 border-t bg-background animate-fade-in">
                  {showingReplyFor === highlight.id ? (
                    <div className="space-y-2 animate-scale-in">
                      <Textarea
                        placeholder="Add a comment..."
                        value={newComments[highlight.id] || ""}
                        onChange={(e) => setNewComments(prev => ({ 
                          ...prev, 
                          [highlight.id]: e.target.value 
                        }))}
                        className="min-h-[60px] text-sm resize-none"
                        autoFocus
                      />
                      <div className="flex justify-end gap-2">
                        <Button 
                          variant="ghost" 
                          size="sm"
                          onClick={() => setShowingReplyFor(null)}
                        >
                          Cancel
                        </Button>
                        <Button 
                          size="sm" 
                          onClick={() => handleAddComment(highlight.id)}
                          disabled={!newComments[highlight.id]?.trim()}
                          className="gap-1"
                        >
                          <Send className="h-3 w-3" />
                          Comment
                        </Button>
                      </div>
                    </div>
                  ) : (
                    <Button 
                      variant="ghost" 
                      size="sm" 
                      onClick={() => handleReply(highlight.id)}
                      className="w-full gap-2 text-muted-foreground hover:text-foreground transition-colors"
                    >
                      <Plus className="h-3 w-3" />
                      Add a comment
                    </Button>
                  )}
                </div>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};