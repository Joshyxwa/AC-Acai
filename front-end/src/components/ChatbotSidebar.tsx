import { useState, useRef, useEffect } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { X, Send, Bot, User, Loader2 } from "lucide-react";

interface Message {
  id: string;
  content: string;
  sender: "user" | "bot";
  timestamp: Date;
}

interface ChatbotSidebarProps {
  projectId?: string;
  documentId: string;
  onClose: () => void;
}

export const ChatbotSidebar = ({ projectId, documentId, onClose }: ChatbotSidebarProps) => {
  const [messages, setMessages] = useState<Message[]>([
    {
      id: "1",
      content: "Hello! I'm your AI compliance assistant. I've analyzed your Technical Design Document and found 2 geographic regulation concerns. How can I help you address them?",
      sender: "bot",
      timestamp: new Date()
    }
  ]);
  const [inputValue, setInputValue] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const handleSendMessage = async () => {
    if (!inputValue.trim() || isLoading) return;

    const userMessage: Message = {
      id: Date.now().toString(),
      content: inputValue,
      sender: "user",
      timestamp: new Date()
    };

    setMessages(prev => [...prev, userMessage]);
    setInputValue("");
    setIsLoading(true);

    // Simulate API call
    setTimeout(() => {
      const botResponse: Message = {
        id: (Date.now() + 1).toString(),
        content: getBotResponse(inputValue),
        sender: "bot",
        timestamp: new Date()
      };
      setMessages(prev => [...prev, botResponse]);
      setIsLoading(false);
    }, 1500);
  };

  const getBotResponse = (userInput: string): string => {
    const input = userInput.toLowerCase();
    
    if (input.includes("gdpr") || input.includes("privacy")) {
      return "Regarding GDPR compliance: The user profile data access in your TDD requires explicit consent. I recommend implementing a consent flow before accessing follower counts and verification status. Would you like me to suggest specific implementation steps?";
    }
    
    if (input.includes("fix") || input.includes("resolve")) {
      return "Here are the recommended fixes:\n\n1. **EU Mentorship Regulations**: Implement region-specific validation in your Spanner rules\n2. **Privacy Consent**: Add consent checkbox in mentorship request flow\n\nShall I generate the specific code changes needed?";
    }
    
    if (input.includes("regions") || input.includes("countries")) {
      return "Based on your service, these regions have specific requirements:\n\n🇪🇺 **European Union**: Digital Services Act compliance\n🇺🇸 **California**: CCPA privacy requirements\n🇬🇧 **United Kingdom**: UK-GDPR considerations\n\nWould you like detailed requirements for any specific region?";
    }
    
    return "I understand you're asking about compliance issues. The main concerns in your document are around data privacy and regional mentorship regulations. Can you be more specific about what aspect you'd like help with?";
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSendMessage();
    }
  };

  return (
    <div className="w-96 border-l bg-card flex flex-col">
      {/* Header */}
      <div className="p-4 border-b flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Avatar className="h-8 w-8">
            <AvatarFallback>
              <Bot className="h-4 w-4" />
            </AvatarFallback>
          </Avatar>
          <div>
            <h3 className="font-medium text-sm">Compliance Assistant</h3>
            <p className="text-xs text-muted-foreground">AI Legal Intern</p>
          </div>
        </div>
        <Button variant="ghost" size="sm" onClick={onClose}>
          <X className="h-4 w-4" />
        </Button>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {messages.map((message) => (
          <div 
            key={message.id}
            className={`flex gap-3 ${message.sender === "user" ? "justify-end" : "justify-start"}`}
          >
            {message.sender === "bot" && (
              <Avatar className="h-7 w-7 mt-1">
                <AvatarFallback>
                  <Bot className="h-3 w-3" />
                </AvatarFallback>
              </Avatar>
            )}
            
            <div className={`max-w-[85%] ${message.sender === "user" ? "order-first" : ""}`}>
              <div className={`p-3 rounded-lg text-sm ${
                message.sender === "user" 
                  ? "bg-primary text-primary-foreground" 
                  : "bg-muted text-foreground"
              }`}>
                <p className="whitespace-pre-wrap">{message.content}</p>
              </div>
              <p className="text-xs text-muted-foreground mt-1">
                {message.timestamp.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
              </p>
            </div>

            {message.sender === "user" && (
              <Avatar className="h-7 w-7 mt-1">
                <AvatarFallback>
                  <User className="h-3 w-3" />
                </AvatarFallback>
              </Avatar>
            )}
          </div>
        ))}
        
        {isLoading && (
          <div className="flex gap-3">
            <Avatar className="h-7 w-7 mt-1">
              <AvatarFallback>
                <Bot className="h-3 w-3" />
              </AvatarFallback>
            </Avatar>
            <div className="bg-muted p-3 rounded-lg">
              <Loader2 className="h-4 w-4 animate-spin" />
            </div>
          </div>
        )}
        
        <div ref={messagesEndRef} />
      </div>

      {/* Input */}
      <div className="p-4 border-t">
        <div className="flex gap-2">
          <Input
            placeholder="Ask about compliance issues..."
            value={inputValue}
            onChange={(e) => setInputValue(e.target.value)}
            onKeyPress={handleKeyPress}
            disabled={isLoading}
            className="flex-1"
          />
          <Button 
            size="sm" 
            onClick={handleSendMessage}
            disabled={!inputValue.trim() || isLoading}
          >
            <Send className="h-4 w-4" />
          </Button>
        </div>
        <p className="text-xs text-muted-foreground mt-2">
          Press Enter to send, Shift+Enter for new line
        </p>
      </div>
    </div>
  );
};