// API Configuration
const API_CONFIG = {
  development: 'http://127.0.0.1:8000',
  production: 'https://your-production-url.com' // Replace with your actual production URL
};

// Automatically detects environment or can be manually overridden
// To force production mode in development, set VITE_API_MODE=production in .env
const isDevelopment = import.meta.env.VITE_API_MODE === 'production' 
  ? false 
  : (import.meta.env.DEV || window.location.hostname === 'localhost');

export const API_BASE_URL = isDevelopment ? API_CONFIG.development : API_CONFIG.production;

// API helper functions
export const apiCall = async (endpoint: string, options: RequestInit = {}) => {
  const url = `${API_BASE_URL}${endpoint}`;
  
  const defaultOptions: RequestInit = {
    headers: {
      'Content-Type': 'application/json',
      ...options.headers,
    },
    ...options,
  };

  try {
    const response = await fetch(url, defaultOptions);
    if (!response.ok) {
      throw new Error(`API call failed: ${response.status} ${response.statusText}`);
    }
    return await response.json();
  } catch (error) {
    console.error(`API Error for ${endpoint}:`, error);
    throw error;
  }
};

// Specific API functions
export const checkProjects = () => apiCall('/check_projects');

export const getProject = (projectId: string) => 
  apiCall(`/get_project?project_id=${projectId}`);

export const getDocument = (projectId: string, documentId: string) => 
  apiCall(`/get_document?project_id=${projectId}&document_id=${documentId}`);

export const getHighlightResponse = (data: {
  'highlight-id': string;
  'document-id': string;
  'project-id': string;
  user_response: string;
}) => apiCall('/get_highlight_response', {
  method: 'POST',
  body: JSON.stringify(data),
});

export const addComment = (data: {
  'highlight-id': string;
  'document-id': string;
  'project-id': string;
  user_response: string;
  author: string;
}) => apiCall('/add_comment', {
  method: 'POST',
  body: JSON.stringify(data),
});

export const addLaw = async (file: File) => {
  const formData = new FormData();
  formData.append('file', file);
  
  const url = `${API_BASE_URL}/add_law`;
  
  try {
    const response = await fetch(url, {
      method: 'POST',
      body: formData,
    });
    
    if (!response.ok) {
      const errorText = await response.text();
      return { ok: false, message: errorText || `Upload failed: ${response.status}` };
    }
    
    const result = await response.json();
    return { ok: true, data: result };
  } catch (error) {
    console.error('Upload error:', error);
    return { ok: false, message: 'Upload failed. Please try again.' };
  }
};

export const newAudit = (projectId: string) => 
  apiCall('/new_audit', {
    method: 'POST',
    body: JSON.stringify({ project_id: projectId }),
  });

export const generateReport = (projectId: string) => 
  apiCall('/generate_report', {
    method: 'POST',
    body: JSON.stringify({ project_id: projectId }),
  });