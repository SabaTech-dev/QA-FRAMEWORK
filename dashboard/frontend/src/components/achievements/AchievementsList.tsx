import { Box, Typography, Grid, Tabs, Tab, Chip } from '@mui/material';
import { useState } from 'react';
import AchievementBadge from './AchievementBadge';
import { ACHIEVEMENTS } from '../../data/achievements';
import { useAchievementsStore } from '../../stores/achievementsStore';
import { AchievementCategory } from '../../types/achievements';

const CATEGORIES: { value: AchievementCategory | 'all'; label: string }[] = [
  { value: 'all', label: 'All' },
  { value: 'testing', label: 'Testing' },
  { value: 'automation', label: 'Automation' },
  { value: 'quality', label: 'Quality' },
  { value: 'speed', label: 'Speed' },
  { value: 'dedication', label: 'Dedication' },
  { value: 'special', label: 'Special' },
];

export default function AchievementsList() {
  const [category, setCategory] = useState<AchievementCategory | 'all'>('all');
  const { getStats } = useAchievementsStore();
  const stats = getStats();

  const filteredAchievements =
    category === 'all'
      ? ACHIEVEMENTS
      : ACHIEVEMENTS.filter((a) => a.category === category);

  return (
    <Box>
      {/* Stats Header */}
      <Box sx={{ mb: 3 }}>
        <Typography variant="h6" gutterBottom sx={{ fontWeight: "bold" }}>
          Your Achievements
        </Typography>
        <Box sx={{ display: "flex", gap: 2, alignItems: "center" }}  >
          <Chip
            label={`${stats.unlockedCount}/${stats.totalCount} Unlocked`}
            color="primary"
            variant="outlined"
          />
          <Chip
            label={`${stats.totalPoints} Points`}
            color="secondary"
            variant="outlined"
          />
        </Box>
      </Box>

      {/* Category Tabs */}
      <Tabs
        value={category}
        onChange={(e, newValue) => setCategory(newValue)}
        variant="scrollable"
        scrollButtons="auto"
        sx={{ mb: 3, borderBottom: 1, borderColor: 'divider' }}
      >
        {CATEGORIES.map((cat) => (
          <Tab key={cat.value} label={cat.label} value={cat.value} />
        ))}
      </Tabs>

      {/* Achievements Grid */}
      <Grid container spacing={2}>
        {filteredAchievements.map((achievement) => (
          <Grid size={{ xs: "auto" }} key={achievement.id}>
            <AchievementBadge achievement={achievement} size="medium" />
          </Grid>
        ))}
      </Grid>

      {/* Empty State */}
      {filteredAchievements.length === 0 && (
        <Box sx={{ py: 4, textAlign: "center" }} >
          <Typography color="textSecondary">
            No achievements in this category yet
          </Typography>
        </Box>
      )}
    </Box>
  );
}
