import { cn } from "@/lib/utils";
import { FileText, AlertTriangle, CheckCircle, Clock } from "lucide-react";

interface DocumentRow {
  doc_id: number;
  created_at: string;
  type: string;
  content: string;
  version: number;
  project_id: number;
  content_span?: string | null;
}

interface DocumentSidebarProps {
  documents: DocumentRow[];
  selectedDocument: number | null;
  onSelectDocument: (documentId: number) => void;
}

export const DocumentSidebar = ({ documents, selectedDocument, onSelectDocument }: DocumentSidebarProps) => {
  const getDocumentTitle = (doc: DocumentRow) => {
    return `${doc.type} Document v${doc.version}`;
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
            key={doc.doc_id}
            onClick={() => onSelectDocument(doc.doc_id)}
            className={cn(
              "w-full text-left p-3 rounded-lg border-l-4 mb-2 transition-all hover:bg-accent/50",
              selectedDocument === doc.doc_id 
                ? "bg-accent border-l-primary shadow-sm" 
                : "border-l-muted bg-background hover:bg-accent/30"
            )}
          >
            <div className="flex items-start justify-between gap-2">
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2 mb-1">
                  <FileText className="h-4 w-4 text-muted-foreground flex-shrink-0" />
                  <span className="text-sm font-medium text-foreground truncate">
                    {getDocumentTitle(doc)}
                  </span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-xs text-muted-foreground bg-muted px-2 py-1 rounded">
                    {doc.type}
                  </span>
                  <span className="text-xs text-muted-foreground">
                    v{doc.version}
                  </span>
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