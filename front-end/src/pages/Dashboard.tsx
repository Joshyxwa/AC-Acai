import { useState, useEffect } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Plus, FileText, Calendar, Users, RefreshCw } from "lucide-react";
import { useNavigate } from "react-router-dom";
import { checkProjects } from "@/lib/api";
import { AddLawDialog } from "@/components/AddLawDialog";
import { formatDistanceToNow, parseISO } from "date-fns";

interface Project {
  project_id: number;
  name: string;
  created_at: string;
  status: string;
  description: string;
}

const Dashboard = () => {
  const navigate = useNavigate();
  const [projects, setProjects] = useState<Project[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Fallback mock data
  const fallbackProjects: Project[] = [
    {
      project_id: 1,
      name: "Feature Authentication System",
      created_at: "2025-08-28 15:32:47.729288+00",
      status: "In Review",
      description: "Authentication system compliance review"
    },
    {
      project_id: 2, 
      name: "Payment Gateway Integration",
      created_at: "2025-08-28 15:32:47.729288+00",
      status: "Flagged",
      description: "Payment processing compliance assessment"
    },
    {
      project_id: 3,
      name: "User Data Analytics Feature",
      created_at: "2025-08-28 15:32:47.729288+00",
      status: "Compliant",
      description: "Data analytics compliance verification"
    },
    {
      project_id: 4,
      name: "Social Media Integration",
      created_at: "2025-08-28 15:32:47.729288+00",
      status: "In Review",
      description: "Social media integration review"
    }
  ];

  const fetchProjects = async () => {
    setIsLoading(true);
    setError(null);
    
    try {
      const data = await checkProjects();
      setProjects(data);
    } catch (err) {
      console.error('Error fetching projects:', err);
      setError(err instanceof Error ? err.message : 'Failed to fetch projects');
      // Use fallback data on error
      setProjects(fallbackProjects);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchProjects();
  }, []);

  const getStatusColor = (status: string) => {
    switch (status) {
      case "Completed": return "text-green-600";
      case "New": return "text-red-600";
      case "Ongoing": return "text-yellow-600";
      default: return "text-muted-foreground"; 
    }
  };

  return (
    <div className="min-h-screen bg-background">
      {/* Header */}
      <header className="border-b bg-card">
        <div className="container mx-auto px-6 py-4">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-2xl font-semibold text-foreground">Geo Compliance Hub</h1>
              <p className="text-muted-foreground">Manage your feature compliance projects</p>
            </div>
            <div className="flex items-center gap-2">
              <Button 
                variant="ghost" 
                size="sm" 
                onClick={fetchProjects}
                disabled={isLoading}
                className="gap-2"
              >
                <RefreshCw className={`h-4 w-4 ${isLoading ? 'animate-spin' : ''}`} />
                {isLoading ? 'Loading...' : 'Refresh'}
              </Button>
              <AddLawDialog />
              <Button onClick={() => navigate("/project/new")} className="gap-2">
                <Plus className="h-4 w-4" />
                New Project
              </Button>
            </div>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="container mx-auto px-6 py-8">
        <div className="mb-8">
          <div className="flex items-center justify-between mb-6">
            <h2 className="text-xl font-medium">Your Projects</h2>
            {error && (
              <div className="text-sm text-red-600 bg-red-50 px-3 py-1 rounded">
                {error} - Using offline data
              </div>
            )}
          </div>
          
          {/* Project Grid */}
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
            {/* Create New Project Card */}
            <Card 
              className="border-dashed border-2 cursor-pointer hover:bg-accent/50 transition-colors"
              onClick={() => navigate("/project/new")}
            >
              <CardContent className="flex flex-col items-center justify-center h-48 text-center">
                <Plus className="h-12 w-12 text-muted-foreground mb-4" />
                <h3 className="font-medium text-foreground">Create New Project</h3>
                <p className="text-sm text-muted-foreground">Start a new compliance review</p>
              </CardContent>
            </Card>

            {/* Existing Projects */}
            {projects.map((project) => (
              <Card 
                key={project.project_id}
                className="cursor-pointer hover:shadow-md transition-shadow"
                onClick={() => navigate(`/project/${project.project_id}`)}
              >
                <CardHeader className="pb-3">
                  <div className="flex items-start justify-between">
                    <FileText className="h-5 w-5 text-primary" />
                    <span className={`text-xs font-medium ${getStatusColor(project.status)}`}>
                      {project.status}
                    </span>
                  </div>
                  <CardTitle className="text-lg leading-tight">{project.name}</CardTitle>
                </CardHeader>
                <CardContent className="pt-0">
                  <div className="space-y-2 text-sm text-muted-foreground">
                    <div className="flex items-center gap-2">
                      <Calendar className="h-4 w-4" />
                      <span>
                        Created {formatDistanceToNow(
                          parseISO(project.created_at.replace(" ", "T").replace(/\.\d+/, "") + "Z"),
                          { addSuffix: true }
                        )}
                      </span>
                    </div>
                    <p className="text-sm">{project.description}</p>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        </div>

        {/* Recent Activity */}
        <div className="mt-12">
          <h2 className="text-xl font-medium mb-6">Recent Activity</h2>
          <Card>
            <CardContent className="p-6">
              <div className="space-y-4">
                <div className="flex items-center gap-3 p-3 rounded-lg bg-accent/30">
                  <div className="h-2 w-2 bg-red-500 rounded-full"></div>
                  <div className="flex-1">
                    <p className="text-sm font-medium">New compliance issue flagged in Payment Gateway Integration</p>
                    <p className="text-xs text-muted-foreground">2 hours ago</p>
                  </div>
                </div>
                <div className="flex items-center gap-3 p-3 rounded-lg bg-accent/30">
                  <div className="h-2 w-2 bg-green-500 rounded-full"></div>
                  <div className="flex-1">
                    <p className="text-sm font-medium">User Data Analytics Feature marked as compliant</p>
                    <p className="text-xs text-muted-foreground">1 day ago</p>
                  </div>
                </div>
                <div className="flex items-center gap-3 p-3 rounded-lg bg-accent/30">
                  <div className="h-2 w-2 bg-yellow-500 rounded-full"></div>
                  <div className="flex-1">
                    <p className="text-sm font-medium">Review started for Authentication System</p>
                    <p className="text-xs text-muted-foreground">3 days ago</p>
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>
      </main>
    </div>
  );
};

export default Dashboard;
