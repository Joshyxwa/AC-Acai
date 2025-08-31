import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { addLaw } from "@/lib/api";
import { useToast } from "@/hooks/use-toast";
import { Plus, Upload } from "lucide-react";


export const AddLawDialog = () => {
  const [open, setOpen] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const { toast } = useToast();

  const handleFileChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (file && file.type === "text/plain") {
      setSelectedFile(file);
    } else {
      toast({
        title: "Invalid file type",
        description: "Please select a .txt file",
        variant: "destructive",
      });
      event.target.value = "";
    }
  };

  const onSubmit = async () => {
    if (!selectedFile) {
      toast({
        title: "No file selected",
        description: "Please select a .txt file to upload",
        variant: "destructive",
      });
      return;
    }

    setIsSubmitting(true);
    
    try {
      const response = await addLaw(selectedFile);
      
      if (response.ok) {
        toast({
          title: "Success",
          description: "Law added successfully",
        });
        setSelectedFile(null);
        setOpen(false);
      } else {
        toast({
          title: "Error",
          description: response.message || "Failed to add law",
          variant: "destructive",
        });
      }
    } catch (error) {
      console.error('Error adding law:', error);
      toast({
        title: "Error",
        description: "Failed to add law. Please try again.",
        variant: "destructive",
      });
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <Button className="gap-2">
          <Plus className="h-4 w-4" />
          Add New Law
        </Button>
      </DialogTrigger>
      <DialogContent className="sm:max-w-[500px] max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>Add New Law</DialogTitle>
          <DialogDescription>
            Add a new law article to the system. Fill in all required information below.
          </DialogDescription>
        </DialogHeader>
        
        <div className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="law-file">Upload Law File</Label>
            <div className="flex items-center gap-3">
              <Input
                id="law-file"
                type="file"
                accept=".txt"
                onChange={handleFileChange}
                disabled={isSubmitting}
                className="file:mr-2 file:rounded-md file:border-0 file:bg-primary file:px-2 file:py-1 file:text-sm file:text-primary-foreground"
              />
              <Upload className="h-4 w-4 text-muted-foreground" />
            </div>
            {selectedFile && (
              <p className="text-sm text-muted-foreground">
                Selected: {selectedFile.name}
              </p>
            )}
          </div>

          <DialogFooter>
            <Button 
              type="button" 
              variant="outline" 
              onClick={() => {
                setOpen(false);
                setSelectedFile(null);
              }}
              disabled={isSubmitting}
            >
              Cancel
            </Button>
            <Button 
              onClick={onSubmit}
              disabled={isSubmitting || !selectedFile}
            >
              {isSubmitting ? "Uploading..." : "Upload Law"}
            </Button>
          </DialogFooter>
        </div>
      </DialogContent>
    </Dialog>
  );
};