import { Box, Typography, Paper, Tooltip, LinearProgress } from "@mui/material";
import { Achievement } from "../../types/achievements";
import { useAchievementsStore } from "../../stores/achievementsStore";

interface AchievementBadgeProps {
  achievement: Achievement;
  size?: "small" | "medium" | "large";
  showProgress?: boolean;
}

const RARITY_COLORS = {
  common: "#9E9E9E",
  uncommon: "#4CAF50",
  rare: "#2196F3",
  epic: "#9C27B0",
  legendary: "#FF9800",
};

const SIZE_CONFIG = {
  small: { width: 80, height: 80, iconSize: 32 },
  medium: { width: 120, height: 120, iconSize: 48 },
  large: { width: 160, height: 160, iconSize: 64 },
};

export default function AchievementBadge({
  achievement,
  size = "medium",
  showProgress = true,
}: AchievementBadgeProps) {
  const { isUnlocked, getProgress } = useAchievementsStore();
  const unlocked = isUnlocked(achievement.id);
  const progress = getProgress(achievement.id);

  const config = SIZE_CONFIG[size];
  const rarityColor = RARITY_COLORS[achievement.rarity];

  return (
    <Tooltip
      title={
        <Box>
          <Typography variant="subtitle2" sx={{ fontWeight: "bold" }}>
            {achievement.name}
          </Typography>
          <Typography variant="body2">{achievement.description}</Typography>
          <Typography variant="caption" sx={{ display: "block", mt: 1 }}>
            Points: {achievement.points} | Rarity: {achievement.rarity}
          </Typography>
          {!unlocked && progress > 0 && (
            <Typography variant="caption" sx={{ display: "block" }}>
              Progress: {Math.round(progress)}%
            </Typography>
          )}
        </Box>
      }
      arrow
    >
      <Paper
        elevation={unlocked ? 3 : 1}
        sx={{
          width: config.width,
          height: config.height,
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          justifyContent: "center",
          position: "relative",
          border: `3px solid ${unlocked ? rarityColor : "#E0E0E0"}`,
          borderRadius: 2,
          background: unlocked
            ? `linear-gradient(135deg, ${rarityColor}22 0%, ${rarityColor}44 100%)`
            : "#F5F5F5",
          opacity: unlocked ? 1 : 0.5,
          transition: "all 0.3s ease",
          cursor: "pointer",
          "&:hover": {
            transform: "scale(1.05)",
            boxShadow: unlocked ? 6 : 2,
          },
        }}
      >
        {/* Icon */}
        <Typography
          sx={{
            fontSize: config.iconSize,
            filter: unlocked ? "none" : "grayscale(100%)",
            mb: 1,
          }}
        >
          {achievement.icon}
        </Typography>

        {/* Name */}
        <Typography
          variant={size === "small" ? "caption" : "body2"}

          sx={{
            px: 1,
            overflow: "hidden",
            textOverflow: "ellipsis",
            whiteSpace: "nowrap",
            width: "100%",
            fontWeight: "bold",
            textAlign: "center",
          }}
        >
          {achievement.name}
        </Typography>

        {/* Progress Bar */}
        {showProgress && !unlocked && progress > 0 && (
          <Box sx={{ width: "80%", mt: 1 }}>
            <LinearProgress
              variant="determinate"
              value={progress}
              sx={{
                height: 4,
                borderRadius: 2,
                backgroundColor: "#E0E0E0",
                "& .MuiLinearProgress-bar": {
                  backgroundColor: rarityColor,
                  borderRadius: 2,
                },
              }}
            />
          </Box>
        )}

        {/* Unlocked Badge */}
        {unlocked && (
          <Box
            sx={{
              position: "absolute",
              top: -8,
              right: -8,
              width: 24,
              height: 24,
              borderRadius: "50%",
              backgroundColor: rarityColor,
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              color: "white",
              fontSize: 14,
              fontWeight: "bold",
            }}
          >
            ✓
          </Box>
        )}
      </Paper>
    </Tooltip>
  );
}
