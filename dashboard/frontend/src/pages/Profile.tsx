import {
  Box,
  Card,
  CardContent,
  Typography,
  Avatar,
  Grid,
  Chip,
  Divider,
  LinearProgress,
} from '@mui/material';
import {
  Person as PersonIcon,
  EmojiEvents as TrophyIcon,
  Stars as StarsIcon,
} from '@mui/icons-material';
import AchievementsList from '../components/achievements/AchievementsList';
import { useAchievementsStore } from '../stores/achievementsStore';
import useAuthStore from '../stores/authStore';

export default function Profile() {
  const { user } = useAuthStore();
  const { getStats } = useAchievementsStore();
  const stats = getStats();

  const completionPercentage = (stats.unlockedCount / stats.totalCount) * 100;

  return (
    <Box>
      {/* Header */}
      <Typography variant="h4" gutterBottom sx={{ fontWeight: "bold" }}>
        Profile & Achievements
      </Typography>

      {/* User Info Card */}
      <Card sx={{ mb: 4, boxShadow: 3 }}>
        <CardContent>
          <Grid container spacing={3} sx={{ alignItems: "center" }}>
            <Grid >
              <Avatar
                sx={{
                  width: 100,
                  height: 100,
                  bgcolor: 'primary.main',
                  fontSize: 48,
                }}
              >
                <PersonIcon sx={{ fontSize: 60 }} />
              </Avatar>
            </Grid>
            <Grid  size={{ xs: "auto" }}>
              <Typography variant="h5" sx={{ fontWeight: "bold" }} gutterBottom>
                {user?.username || 'QA Tester'}
              </Typography>
              <Typography variant="body2" color="textSecondary" gutterBottom>
                {user?.email || 'qa@example.com'}
              </Typography>
              <Box sx={{ display: "flex", gap: 1, mt: 1 }}  >
                <Chip
                  icon={<TrophyIcon />}
                  label={`${stats.unlockedCount} Achievements`}
                  color="primary"
                  size="small"
                />
                <Chip
                  icon={<StarsIcon />}
                  label={`${stats.totalPoints} Points`}
                  color="secondary"
                  size="small"
                />
              </Box>
            </Grid>
          </Grid>

          <Divider sx={{ my: 3 }} />

          {/* Progress */}
          <Box>
            <Box sx={{ display: "flex", justifyContent: "space-between", mb: 1 }}  >
              <Typography variant="body2" sx={{ fontWeight: "bold" }}>
                Completion Progress
              </Typography>
              <Typography variant="body2" color="textSecondary">
                {stats.unlockedCount}/{stats.totalCount} (
                {Math.round(completionPercentage)}%)
              </Typography>
            </Box>
            <LinearProgress
              variant="determinate"
              value={completionPercentage}
              sx={{
                height: 10,
                borderRadius: 5,
                backgroundColor: '#E0E0E0',
                '& .MuiLinearProgress-bar': {
                  borderRadius: 5,
                  background: 'linear-gradient(90deg, #667eea 0%, #764ba2 100%)',
                },
              }}
            />
          </Box>
        </CardContent>
      </Card>

      {/* Achievements Section */}
      <Card sx={{ boxShadow: 3 }}>
        <CardContent>
          <AchievementsList />
        </CardContent>
      </Card>
    </Box>
  );
}
