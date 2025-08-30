import { useState, useEffect } from "react";
import { Button } from "@/components/ui/button";
import { ArrowLeft, MessageCircle, Users, Settings, RefreshCw, Play, FileText } from "lucide-react";
import { useNavigate, useParams } from "react-router-dom";
import { DocumentSidebar } from "@/components/DocumentSidebar";
import { DocumentViewer } from "@/components/DocumentViewer";
import { ChatbotSidebar } from "@/components/ChatbotSidebar";
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog";
import { ScrollArea } from "@/components/ui/scroll-area";
import { getProject, newAudit, generateReport } from "@/lib/api";
import ReactMarkdown from "react-markdown";

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
  const [isAuditLoading, setIsAuditLoading] = useState(false);
  const [isReportLoading, setIsReportLoading] = useState(false);
  const [report, setReport] = useState<string | null>(null);
  const [isReportDialogOpen, setIsReportDialogOpen] = useState(false);

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

  const handleNewAudit = async () => {
    if (!projectId) return;
    
    setIsAuditLoading(true);
    try {
      await newAudit(projectId);
      // Refresh the page to get new data
      window.location.reload();
    } catch (error) {
      console.error('Audit failed:', error);
      setIsAuditLoading(false);
    }
  };

  const handleGenerateReport = async () => {
    if (!projectId) return;
    
    setIsReportLoading(true);
    try {
      const response = await generateReport(projectId);
      setReport(response.report);
      setIsReportDialogOpen(true);
    } catch (error) {
      console.error('Report generation failed:', error);
    } finally {
      setIsReportLoading(false);
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
            <Button 
              variant="default" 
              size="sm"
              onClick={handleNewAudit}
              disabled={isAuditLoading}
              className="gap-2"
            >
              {isAuditLoading ? (
                <RefreshCw className="h-4 w-4 animate-spin" />
              ) : (
                <Play className="h-4 w-4" />
              )}
              {isAuditLoading ? "Running..." : "New Audit"}
            </Button>
            
            <Dialog open={isReportDialogOpen} onOpenChange={setIsReportDialogOpen}>
              <DialogTrigger asChild>
                <Button 
                  variant="outline" 
                  size="sm"
                  onClick={handleGenerateReport}
                  disabled={isReportLoading}
                  className="gap-2"
                >
                  {isReportLoading ? (
                    <RefreshCw className="h-4 w-4 animate-spin" />
                  ) : (
                    <FileText className="h-4 w-4" />
                  )}
                  {isReportLoading ? "Generating..." : "Synthesis Report"}
                </Button>
              </DialogTrigger>
              <DialogContent className="max-w-4xl max-h-[80vh]">
                <DialogHeader>
                  <DialogTitle>Synthesis Report</DialogTitle>
                  <DialogDescription>
                    Generated report for {project?.title}
                  </DialogDescription>
                </DialogHeader>
                <ScrollArea className="h-[60vh] w-full">
                  <div className="prose prose-base max-w-none p-6 bg-muted rounded-md dark:prose-invert prose-headings:font-semibold prose-headings:text-foreground prose-p:text-muted-foreground prose-p:leading-relaxed prose-strong:text-foreground prose-li:text-muted-foreground prose-h1:text-xl prose-h2:text-lg prose-h3:text-base prose-h4:text-sm">
                    <ReactMarkdown
                      components={{
                        h1: ({ children }) => <h1 className="text-xl font-bold mb-4 mt-6 text-foreground border-b pb-2">{children}</h1>,
                        h2: ({ children }) => <h2 className="text-lg font-semibold mb-3 mt-5 text-foreground">{children}</h2>,
                        h3: ({ children }) => <h3 className="text-base font-medium mb-2 mt-4 text-foreground">{children}</h3>,
                        h4: ({ children }) => <h4 className="text-sm font-medium mb-2 mt-3 text-foreground">{children}</h4>,
                        p: ({ children }) => {
                          // Handle special formatted lines like "**Label:** content"
                          const content = String(children);
                          if (content.includes('**') && content.includes(':')) {
                            const parts = content.split(':');
                            if (parts.length >= 2) {
                              const label = parts[0].replace(/\*\*/g, '');
                              const value = parts.slice(1).join(':').trim();
                              return (
                                <div className="mb-2 pl-4 border-l-2 border-muted-foreground/20">
                                  <span className="font-medium text-foreground text-sm">{label}:</span>
                                  <span className="ml-2 text-sm text-muted-foreground">{value}</span>
                                </div>
                              );
                            }
                          }
                          return <p className="mb-3 text-sm leading-relaxed text-muted-foreground">{children}</p>;
                        },
                        strong: ({ children }) => <strong className="font-semibold text-foreground">{children}</strong>,
                        ul: ({ children }) => <ul className="mb-4 ml-4 space-y-1">{children}</ul>,
                        ol: ({ children }) => <ol className="mb-4 ml-4 space-y-1">{children}</ol>,
                        li: ({ children }) => <li className="text-sm text-muted-foreground mb-1">{children}</li>,
                        hr: () => <hr className="my-6 border-border" />,
                        blockquote: ({ children }) => <blockquote className="border-l-4 border-primary pl-4 italic my-4">{children}</blockquote>,
                      }}
                    >
                      {report || "No report generated"}
                    </ReactMarkdown>
                  </div>
                </ScrollArea>
              </DialogContent>
            </Dialog>
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