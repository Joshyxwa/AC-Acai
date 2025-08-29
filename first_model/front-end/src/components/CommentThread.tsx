import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { X, Send, AlertTriangle, User } from "lucide-react";

interface Comment {
  id: string;
  author: string;
  timestamp: string;
  content: string;
  type: "system" | "user";
}

interface CommentThreadProps {
  comments: Comment[];
  onClose: () => void;
  onAddComment: (content: string) => void;
}

export const CommentThread = ({ comments, onClose, onAddComment }: CommentThreadProps) => {
  const [newComment, setNewComment] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);

  const handleSubmit = async () => {
    if (!newComment.trim()) return;
    
    setIsSubmitting(true);
    // Simulate API call delay
    await new Promise(resolve => setTimeout(resolve, 500));
    onAddComment(newComment);
    setNewComment("");
    setIsSubmitting(false);
  };

  return (
    <div className="absolute top-8 right-0 w-80 bg-card border rounded-lg shadow-lg z-50 max-h-96 flex flex-col">
      {/* Header */}
      <div className="flex items-center justify-between p-3 border-b">
        <h3 className="font-medium text-sm">Comments</h3>
        <Button variant="ghost" size="sm" onClick={onClose}>
          <X className="h-4 w-4" />
        </Button>
      </div>

      {/* Comments List */}
      <div className="flex-1 overflow-y-auto p-3 space-y-3">
        {comments.map((comment) => (
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
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* Add Comment */}
      <div className="p-3 border-t space-y-2">
        <Textarea
          placeholder="Add a comment..."
          value={newComment}
          onChange={(e) => setNewComment(e.target.value)}
          className="min-h-[60px] text-sm resize-none"
        />
        <div className="flex justify-end">
          <Button 
            size="sm" 
            onClick={handleSubmit}
            disabled={!newComment.trim() || isSubmitting}
            className="gap-1"
          >
            <Send className="h-3 w-3" />
            {isSubmitting ? "Sending..." : "Comment"}
          </Button>
        </div>
      </div>
    </div>
  );
};