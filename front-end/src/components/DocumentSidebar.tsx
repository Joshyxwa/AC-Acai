import { cn } from "@/lib/utils";
import { FileText, AlertTriangle, CheckCircle, Clock } from "lucide-react";

interface Document {
  id: string;
  title: string;
  type: string;
  status: "compliant" | "flagged" | "review";
}

interface DocumentSidebarProps {
  documents: Document[];
  selectedDocument: string;
  onSelectDocument: (documentId: string) => void;
}

export const DocumentSidebar = ({ documents, selectedDocument, onSelectDocument }: DocumentSidebarProps) => {
  const getStatusIcon = (status: string) => {
    switch (status) {
      case "compliant":
        return <CheckCircle className="h-4 w-4 text-green-500" />;
      case "flagged":
        return <AlertTriangle className="h-4 w-4 text-red-500" />;
      case "review":
        return <Clock className="h-4 w-4 text-yellow-500" />;
      default:
        return <FileText className="h-4 w-4 text-muted-foreground" />;
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case "compliant": return "border-l-green-500";
      case "flagged": return "border-l-red-500";
      case "review": return "border-l-yellow-500";
      default: return "border-l-muted";
    }
  };

  return (
    <div className="w-80 border-r bg-card/50">
      {/* Header */}
      <div className="p-4 border-b">
        <h2 className="font-medium text-foreground">Document Tabs</h2>
        <p className="text-sm text-muted-foreground">Select a document to review</p>
      </div>

      {/* Document List */}
      <div className="p-2">
        {documents.map((doc) => (
          <button
            key={doc.id}
            onClick={() => onSelectDocument(doc.id)}
            className={cn(
              "w-full text-left p-3 rounded-lg border-l-4 mb-2 transition-all hover:bg-accent/50",
              selectedDocument === doc.id 
                ? "bg-accent border-l-primary shadow-sm" 
                : `${getStatusColor(doc.status)} bg-background hover:bg-accent/30`
            )}
          >
            <div className="flex items-start justify-between gap-2">
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2 mb-1">
                  <FileText className="h-4 w-4 text-muted-foreground flex-shrink-0" />
                  <span className="text-sm font-medium text-foreground truncate">
                    {doc.title}
                  </span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-xs text-muted-foreground bg-muted px-2 py-1 rounded">
                    {doc.type}
                  </span>
                  {getStatusIcon(doc.status)}
                </div>
              </div>
            </div>
          </button>
        ))}
      </div>

      {/* Add Document Button */}
      <div className="p-4 border-t mt-auto">
        <button className="w-full p-3 border-2 border-dashed border-muted-foreground/30 rounded-lg text-sm text-muted-foreground hover:border-primary hover:text-primary transition-colors">
          + Add new document
        </button>
      </div>
    </div>
  );
};