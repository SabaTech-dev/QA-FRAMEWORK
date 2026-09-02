import {
  Dialog,
  DialogTitle,
  DialogContent,
  Typography,
  Box,
  Chip,
  IconButton,
} from '@mui/material';
import { Close as CloseIcon } from '@mui/icons-material';
import { DEFAULT_SHORTCUTS } from '../../hooks/useKeyboardShortcuts';

interface KeyboardShortcutsDialogProps {
  open: boolean;
  onClose: () => void;
}

export default function KeyboardShortcutsDialog({
  open,
  onClose,
}: KeyboardShortcutsDialogProps) {
  // Group shortcuts by category
  const groupedShortcuts = DEFAULT_SHORTCUTS.reduce((acc, shortcut) => {
    if (!acc[shortcut.category]) {
      acc[shortcut.category] = [];
    }
    acc[shortcut.category].push(shortcut);
    return acc;
  }, {} as Record<string, typeof DEFAULT_SHORTCUTS>);

  return (
    <Dialog open={open} onClose={onClose} maxWidth="sm" fullWidth>
      <DialogTitle>
        <Box sx={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}  >
          <Typography variant="h6" sx={{ fontWeight: "bold" }}>
            Keyboard Shortcuts
          </Typography>
          <IconButton size="small" onClick={onClose}>
            <CloseIcon />
          </IconButton>
        </Box>
      </DialogTitle>
      <DialogContent>
        {Object.entries(groupedShortcuts).map(([category, shortcuts]) => (
          <Box key={category} sx={{ mb: 3 }}>
            <Typography
              variant="subtitle2"
              color="textSecondary"
              gutterBottom
              sx={{ fontWeight: 'bold', mb: 1 }}
            >
              {category}
            </Typography>
            {shortcuts.map((shortcut, index) => (
              <Box
                key={index}
                
                
                
                
                sx={{ borderBottom: '1px solid',
                  borderColor: 'divider',
                  '&:last-child': {
                    borderBottom: 'none',
                  }, display: "flex", justifyContent: "space-between", alignItems: "center", py: 1 }}
              >
                <Typography variant="body2">{shortcut.description}</Typography>
                <Chip
                  label={shortcut.key.toUpperCase()}
                  size="small"
                  variant="outlined"
                  sx={{
                    fontFamily: 'monospace',
                    fontWeight: 'bold',
                    minWidth: '40px',
                  }}
                />
              </Box>
            ))}
          </Box>
        ))}
      </DialogContent>
    </Dialog>
  );
}
