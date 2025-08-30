import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog";
import { Form, FormControl, FormField, FormItem, FormLabel, FormMessage } from "@/components/ui/form";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { addLaw } from "@/lib/api";
import { useToast } from "@/hooks/use-toast";
import { Plus } from "lucide-react";

const addLawSchema = z.object({
  article_number: z.string().min(1, "Article number is required"),
  type: z.enum(["recital", "law", "definition"], {
    required_error: "Please select a type",
  }),
  belongs_to: z.string().min(1, "Belongs to field is required"),
  contents: z.string().min(1, "Contents are required"),
  word: z.string().optional(),
}).refine((data) => {
  if (data.type === "definition" && (!data.word || data.word.trim() === "")) {
    return false;
  }
  return true;
}, {
  message: "Word must be provided for definition type laws",
  path: ["word"],
});

type AddLawFormData = z.infer<typeof addLawSchema>;

export const AddLawDialog = () => {
  const [open, setOpen] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const { toast } = useToast();

  const form = useForm<AddLawFormData>({
    resolver: zodResolver(addLawSchema),
    defaultValues: {
      article_number: "",
      type: undefined,
      belongs_to: "",
      contents: "",
      word: "",
    },
  });

  const watchedType = form.watch("type");

  const onSubmit = async (data: AddLawFormData) => {
    setIsSubmitting(true);
    
    try {
      const payload = {
        article_number: data.article_number,
        type: data.type,
        belongs_to: data.belongs_to,
        contents: data.contents,
        word: data.type === "definition" ? data.word || null : null,
      };

      const response = await addLaw(payload);
      
      if (response.ok) {
        toast({
          title: "Success",
          description: "Law added successfully",
        });
        form.reset();
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
        
        <Form {...form}>
          <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-4">
            <FormField
              control={form.control}
              name="article_number"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Article Number</FormLabel>
                  <FormControl>
                    <Input 
                      placeholder="e.g., 13-63-101(2)" 
                      {...field} 
                    />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />

            <FormField
              control={form.control}
              name="type"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Type</FormLabel>
                  <Select onValueChange={field.onChange} defaultValue={field.value}>
                    <FormControl>
                      <SelectTrigger>
                        <SelectValue placeholder="Select law type" />
                      </SelectTrigger>
                    </FormControl>
                    <SelectContent>
                      <SelectItem value="recital">Recital</SelectItem>
                      <SelectItem value="law">Law</SelectItem>
                      <SelectItem value="definition">Definition</SelectItem>
                    </SelectContent>
                  </Select>
                  <FormMessage />
                </FormItem>
              )}
            />

            <FormField
              control={form.control}
              name="belongs_to"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Belongs To</FormLabel>
                  <FormControl>
                    <Input 
                      placeholder="e.g., S.B. 152 (2023)" 
                      {...field} 
                    />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />

            {watchedType === "definition" && (
              <FormField
                control={form.control}
                name="word"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Word (Definition)</FormLabel>
                    <FormControl>
                      <Input 
                        placeholder="e.g., minor" 
                        {...field} 
                      />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />
            )}

            <FormField
              control={form.control}
              name="contents"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Contents</FormLabel>
                  <FormControl>
                    <Textarea 
                      placeholder="Enter the full content of the law article..."
                      className="min-h-[100px]"
                      {...field} 
                    />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />

            <DialogFooter>
              <Button 
                type="button" 
                variant="outline" 
                onClick={() => setOpen(false)}
                disabled={isSubmitting}
              >
                Cancel
              </Button>
              <Button 
                type="submit" 
                disabled={isSubmitting}
              >
                {isSubmitting ? "Adding..." : "Add Law"}
              </Button>
            </DialogFooter>
          </form>
        </Form>
      </DialogContent>
    </Dialog>
  );
};