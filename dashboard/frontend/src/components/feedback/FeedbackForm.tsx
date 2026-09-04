import { useState } from "react";
import {
  Box,
  Card,
  CardContent,
  TextField,
  Button,
  Typography,
  Alert,
  MenuItem,
  Rating,
  Chip,
  IconButton,
  Collapse,
} from "@mui/material";
import {
  Send as SendIcon,
  BugReport as BugIcon,
  Lightbulb as FeatureIcon,
  Feedback as GeneralIcon,
  TrendingUp as ImprovementIcon,
  ExpandMore as ExpandIcon,
  ExpandLess as CollapseIcon,
} from "@mui/icons-material";
import { useMutation } from "react-query";
import { feedbackAPI } from "../../api/client";
import toast from "react-hot-toast";

type FeedbackType = "bug" | "feature" | "general" | "improvement";
type Priority = "low" | "medium" | "high" | "critical";

interface FeedbackFormData {
  feedback_type: FeedbackType;
  category: string;
  title: string;
  description: string;
  priority: Priority;
  rating: number | null;
  tags: string[];
}

const FEEDBACK_TYPES = [
  { value: "bug", label: "Bug Report", icon: <BugIcon /> },
  { value: "feature", label: "Feature Request", icon: <FeatureIcon /> },
  { value: "general", label: "General Feedback", icon: <GeneralIcon /> },
  { value: "improvement", label: "Improvement", icon: <ImprovementIcon /> },
];

const CATEGORIES = [
  "UI/UX",
  "Performance",
  "Documentation",
  "API",
  "Authentication",
  "Dashboard",
  "Testing",
  "Other",
];

const PRIORITIES = [
  { value: "low", label: "Low", color: "#4caf50" },
  { value: "medium", label: "Medium", color: "#ff9800" },
  { value: "high", label: "High", color: "#f44336" },
  { value: "critical", label: "Critical", color: "#9c27b0" },
];

const SUGGESTED_TAGS = [
  "ui",
  "ux",
  "performance",
  "bug",
  "feature",
  "documentation",
  "api",
  "authentication",
  "dashboard",
  "mobile",
  "desktop",
];

interface FeedbackFormProps {
  onSuccess?: () => void;
  compact?: boolean;
}

export default function FeedbackForm({
  onSuccess,
  compact = false,
}: FeedbackFormProps) {
  const [expanded, setExpanded] = useState(!compact);
  const [formData, setFormData] = useState<FeedbackFormData>({
    feedback_type: "general",
    category: "",
    title: "",
    description: "",
    priority: "medium",
    rating: null,
    tags: [],
  });
  const [newTag, setNewTag] = useState("");

  const submitMutation = useMutation(
    () =>
      feedbackAPI.submit({
        ...formData,
        page_url: window.location.href,
        browser_info: {
          userAgent: navigator.userAgent,
          language: navigator.language,
          screenWidth: window.screen.width,
          screenHeight: window.screen.height,
        },
      }),
    {
      onSuccess: () => {
        toast.success("Thank you for your feedback!");
        setFormData({
          feedback_type: "general",
          category: "",
          title: "",
          description: "",
          priority: "medium",
          rating: null,
          tags: [],
        });
        onSuccess?.();
      },
      onError: (error: any) => {
        toast.error(
          error.response?.data?.detail || "Failed to submit feedback",
        );
      },
    },
  );

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!formData.title || !formData.description) {
      toast.error("Please fill in all required fields");
      return;
    }
    submitMutation.mutate();
  };

  const handleAddTag = (tag: string) => {
    if (tag && !formData.tags.includes(tag)) {
      setFormData({ ...formData, tags: [...formData.tags, tag] });
    }
    setNewTag("");
  };

  const handleRemoveTag = (tag: string) => {
    setFormData({ ...formData, tags: formData.tags.filter((t) => t !== tag) });
  };

  return (
    <Card sx={{ width: "100%" }}>
      {compact && (
        <Box
          sx={{
            p: 2,
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            cursor: "pointer",
          }}
          onClick={() => setExpanded(!expanded)}
        >
          <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
            <GeneralIcon color="primary" />
            <Typography variant="h6">Submit Feedback</Typography>
          </Box>
          <IconButton size="small">
            {expanded ? <CollapseIcon /> : <ExpandIcon />}
          </IconButton>
        </Box>
      )}

      <Collapse in={expanded}>
        <CardContent sx={compact ? { pt: 0 } : {}}>
          {!compact && (
            <Typography variant="h6" gutterBottom>
              Share Your Feedback
            </Typography>
          )}

          <form onSubmit={handleSubmit}>
            <Box sx={{ display: "flex", flexDirection: "column", gap: 2 }}>
              {/* Feedback Type */}
              <TextField
                select
                fullWidth
                label="Feedback Type"
                value={formData.feedback_type}
                onChange={(e) =>
                  setFormData({
                    ...formData,
                    feedback_type: e.target.value as FeedbackType,
                  })
                }
              >
                {FEEDBACK_TYPES.map((type) => (
                  <MenuItem key={type.value} value={type.value}>
                    <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
                      {type.icon}
                      {type.label}
                    </Box>
                  </MenuItem>
                ))}
              </TextField>

              {/* Title */}
              <TextField
                fullWidth
                required
                label="Title"
                placeholder="Brief summary of your feedback"
                value={formData.title}
                onChange={(e) =>
                  setFormData({ ...formData, title: e.target.value })
                }
                slotProps={{ htmlInput: { maxLength: 200 } }}
              />

              {/* Description */}
              <TextField
                fullWidth
                required
                multiline
                rows={4}
                label="Description"
                placeholder="Please describe your feedback in detail..."
                value={formData.description}
                onChange={(e) =>
                  setFormData({ ...formData, description: e.target.value })
                }
              />

              {/* Category and Priority Row */}
              <Box sx={{ display: "flex", gap: 2 }}>
                <TextField
                  select
                  fullWidth
                  label="Category"
                  value={formData.category}
                  onChange={(e) =>
                    setFormData({ ...formData, category: e.target.value })
                  }
                >
                  {CATEGORIES.map((cat) => (
                    <MenuItem key={cat} value={cat}>
                      {cat}
                    </MenuItem>
                  ))}
                </TextField>

                <TextField
                  select
                  fullWidth
                  label="Priority"
                  value={formData.priority}
                  onChange={(e) =>
                    setFormData({
                      ...formData,
                      priority: e.target.value as Priority,
                    })
                  }
                >
                  {PRIORITIES.map((pri) => (
                    <MenuItem key={pri.value} value={pri.value}>
                      <Box
                        sx={{ display: "flex", alignItems: "center", gap: 1 }}
                      >
                        <Box
                          sx={{
                            width: 8,
                            height: 8,
                            borderRadius: "50%",
                            bgcolor: pri.color,
                          }}
                        />
                        {pri.label}
                      </Box>
                    </MenuItem>
                  ))}
                </TextField>
              </Box>

              {/* Rating */}
              <Box>
                <Typography
                  component="legend"
                  variant="body2"
                  color="textSecondary"
                >
                  Overall Rating (Optional)
                </Typography>
                <Rating
                  value={formData.rating}
                  onChange={(_, value) =>
                    setFormData({ ...formData, rating: value })
                  }
                  size="large"
                />
              </Box>

              {/* Tags */}
              <Box>
                <Typography variant="body2" color="textSecondary" gutterBottom>
                  Tags
                </Typography>
                <Box
                  sx={{ display: "flex", flexWrap: "wrap", gap: 0.5, mb: 1 }}
                >
                  {formData.tags.map((tag) => (
                    <Chip
                      key={tag}
                      label={tag}
                      onDelete={() => handleRemoveTag(tag)}
                      size="small"
                      color="primary"
                      variant="outlined"
                    />
                  ))}
                </Box>
                <Box sx={{ display: "flex", gap: 1 }}>
                  <TextField
                    size="small"
                    placeholder="Add tag"
                    value={newTag}
                    onChange={(e) => setNewTag(e.target.value)}
                    onKeyPress={(e) => {
                      if (e.key === "Enter") {
                        e.preventDefault();
                        handleAddTag(newTag);
                      }
                    }}
                  />
                  <Button
                    variant="outlined"
                    size="small"
                    onClick={() => handleAddTag(newTag)}
                  >
                    Add
                  </Button>
                </Box>
                <Box
                  sx={{ display: "flex", flexWrap: "wrap", gap: 0.5, mt: 1 }}
                >
                  {SUGGESTED_TAGS.filter((t) => !formData.tags.includes(t))
                    .slice(0, 6)
                    .map((tag) => (
                      <Chip
                        key={tag}
                        label={tag}
                        onClick={() => handleAddTag(tag)}
                        size="small"
                        variant="outlined"
                        sx={{ cursor: "pointer" }}
                      />
                    ))}
                </Box>
              </Box>

              {/* Submit Button */}
              <Button
                type="submit"
                variant="contained"
                color="primary"
                size="large"
                disabled={submitMutation.isLoading}
                startIcon={<SendIcon />}
                sx={{ mt: 2 }}
              >
                {submitMutation.isLoading ? "Submitting..." : "Submit Feedback"}
              </Button>
            </Box>
          </form>
        </CardContent>
      </Collapse>
    </Card>
  );
}
