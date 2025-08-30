import { useState, useEffect } from "react";
import { Button } from "@/components/ui/button";
import { ArrowLeft, MessageCircle, Users, Settings, RefreshCw } from "lucide-react";
import { useNavigate, useParams } from "react-router-dom";
import { DocumentSidebar } from "@/components/DocumentSidebar";
import { DocumentViewer } from "@/components/DocumentViewer";
import { ChatbotSidebar } from "@/components/ChatbotSidebar";
import { getProject } from "@/lib/api";

interface DocumentRow {
  doc_id: number;
  created_at: string;
  type: string;
  content: string;
  version: number;
  project_id: number;
  content_span?: string | null;
}

interface Project {
  id: string;
  title: string;
  documents: DocumentRow[];
}

const DocumentEditor = () => {
  const navigate = useNavigate();
  const { projectId } = useParams();
  const [selectedDocument, setSelectedDocument] = useState<number | null>(null);
  const [isChatOpen, setIsChatOpen] = useState(false);
  const [project, setProject] = useState<Project | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Fallback project data
  const fallbackProject: Project = {
    id: projectId || "1",
    title: "Feature Authentication System",
    documents: [
      { 
        doc_id: 1, 
        created_at: "2025-08-30T10:00:00Z", 
        type: "TDD", 
        content: "Technical Design Document content...", 
        version: 1, 
        project_id: parseInt(projectId || "1"),
        content_span: null 
      },
      { 
        doc_id: 2, 
        created_at: "2025-08-30T11:00:00Z", 
        type: "PRD", 
        content: "Product Requirements Document content...", 
        version: 1, 
        project_id: parseInt(projectId || "1"),
        content_span: null 
      },
      { 
        doc_id: 3, 
        created_at: "2025-08-30T12:00:00Z", 
        type: "Security", 
        content: "Security Assessment Document content...", 
        version: 1, 
        project_id: parseInt(projectId || "1"),
        content_span: null 
      }
    ]
  };

  const fetchProject = async () => {
    if (!projectId) {
      setProject(fallbackProject);
      setSelectedDocument(1);
      setIsLoading(false);
      return;
    }

    setIsLoading(true);
    setError(null);
    
    try {
      const data = await getProject(projectId);
      setProject(data);
      // Auto-select first document if available
      if (data.documents && data.documents.length > 0) {
        setSelectedDocument(data.documents[0].doc_id);
      }
    } catch (err) {
      console.error('Error fetching project:', err);
      setError(err instanceof Error ? err.message : 'Failed to fetch project');
      // Use fallback data on error
      setProject(fallbackProject);
      setSelectedDocument(1);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchProject();
  }, [projectId]);

  if (isLoading) {
    return (
      <div className="h-screen flex items-center justify-center bg-background">
        <div className="text-center">
          <RefreshCw className="h-8 w-8 animate-spin mx-auto mb-4 text-primary" />
          <p className="text-muted-foreground">Loading project...</p>
        </div>
      </div>
    );
  }

  if (!project) {
    return (
      <div className="h-screen flex items-center justify-center bg-background">
        <div className="text-center">
          <h2 className="text-lg font-medium text-foreground mb-2">Project not found</h2>
          <p className="text-muted-foreground mb-4">The requested project could not be loaded.</p>
          <Button onClick={() => navigate("/")} variant="outline">
            Back to Dashboard
          </Button>
        </div>
      </div>
    );
  }

  return (
    <div className="h-screen flex flex-col bg-background">
      {/* Header */}
      <header className="border-b bg-card px-4 py-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-4">
            <Button 
              variant="ghost" 
              size="sm" 
              onClick={() => navigate("/")}
              className="gap-2"
            >
              <ArrowLeft className="h-4 w-4" />
              Back to Projects
            </Button>
            <div>
              <h1 className="font-semibold text-foreground">{project.title}</h1>
              <p className="text-sm text-muted-foreground">
                Compliance Review
                {error && <span className="text-red-600"> • Using offline data</span>}
              </p>
            </div>
          </div>
          
          <div className="flex items-center gap-2">
            <Button variant="ghost" size="sm">
              <Users className="h-4 w-4" />
            </Button>
            <Button variant="ghost" size="sm">
              <Settings className="h-4 w-4" />
            </Button>
            <Button 
              variant="ghost" 
              size="sm"
              onClick={() => setIsChatOpen(!isChatOpen)}
              className={isChatOpen ? "bg-accent" : ""}
            >
              <MessageCircle className="h-4 w-4" />
            </Button>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <div className="flex flex-1 overflow-hidden">
        {/* Left Sidebar - Document Navigation */}
        <DocumentSidebar 
          documents={project.documents}
          selectedDocument={selectedDocument}
          onSelectDocument={setSelectedDocument}
        />

        {/* Center - Document Viewer */}
        <div className="flex-1 overflow-hidden">
          {selectedDocument ? (
            <DocumentViewer 
              documentId={selectedDocument.toString()} 
              projectId={projectId || "1"}
            />
          ) : (
            <div className="flex-1 p-8 flex items-center justify-center">
              <div className="text-center">
                <h2 className="text-lg font-medium text-foreground mb-2">Select a document</h2>
                <p className="text-muted-foreground">Choose a document from the sidebar to view its contents.</p>
              </div>
            </div>
          )}
        </div>

        {/* Right Sidebar - Chatbot */}
        {isChatOpen && (
          <ChatbotSidebar 
            projectId={project.id}
            documentId={selectedDocument?.toString() || null}
            onClose={() => setIsChatOpen(false)}
          />
        )}
      </div>
    </div>
  );
};

export default DocumentEditor;