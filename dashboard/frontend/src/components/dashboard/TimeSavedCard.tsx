import { Card, CardContent, Typography, Box, LinearProgress } from '@mui/material';
import { AccessTime as TimeIcon, TrendingUp as TrendingUpIcon } from '@mui/icons-material';
import { useMemo } from 'react';
import {
  calculateCumulativeTimeSaved,
  formatTimeSaved,
  calculateTimeSavedPercentage,
} from '../../utils/timeCalculations';

interface TimeSavedCardProps {
  executions: any[];
  totalTests?: number;
}

export default function TimeSavedCard({ executions, totalTests }: TimeSavedCardProps) {
  const timeSaved = useMemo(() => {
    return calculateCumulativeTimeSaved(executions || []);
  }, [executions]);

  const formattedTime = formatTimeSaved(timeSaved);

  const percentage = useMemo(() => {
    const tests = totalTests || executions?.length || 0;
    return calculateTimeSavedPercentage(timeSaved, tests);
  }, [timeSaved, totalTests, executions]);

  return (
    <Card
      sx={{
        height: '100%',
        background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
        color: 'white',
        position: 'relative',
        overflow: 'hidden',
      }}
    >
      <CardContent>
        <Box sx={{ display: "flex", alignItems: "center", mb: 2 }}  >
          <TimeIcon sx={{ fontSize: 40, mr: 2, opacity: 0.9 }} />
          <Box>
            <Typography variant="h6" gutterBottom sx={{ fontWeight: "bold" }}>
              Time Saved
            </Typography>
            <Typography variant="body2" sx={{ opacity: 0.9 }}>
              By automating tests
            </Typography>
          </Box>
        </Box>

        <Box sx={{ mb: 3 }}>
          <Typography variant="h3" sx={{ fontWeight: "bold" }} gutterBottom>
            {formattedTime}
          </Typography>
          <Box sx={{ display: "flex", alignItems: "center" }} >
            <TrendingUpIcon sx={{ fontSize: 20, mr: 1 }} />
            <Typography variant="body2">
              {percentage}% faster than manual testing
            </Typography>
          </Box>
        </Box>

        <Box>
          <Box sx={{ display: "flex", justifyContent: "space-between", mb: 1 }}  >
            <Typography variant="body2">Efficiency</Typography>
            <Typography variant="body2" sx={{ fontWeight: "bold" }}>
              {percentage}%
            </Typography>
          </Box>
          <LinearProgress
            variant="determinate"
            value={percentage}
            sx={{
              height: 8,
              borderRadius: 4,
              backgroundColor: 'rgba(255, 255, 255, 0.3)',
              '& .MuiLinearProgress-bar': {
                backgroundColor: 'white',
                borderRadius: 4,
              },
            }}
          />
        </Box>

        {/* Decorative elements */}
        <Box
          sx={{
            position: 'absolute',
            top: -20,
            right: -20,
            width: 120,
            height: 120,
            borderRadius: '50%',
            backgroundColor: 'rgba(255, 255, 255, 0.1)',
          }}
        />
        <Box
          sx={{
            position: 'absolute',
            bottom: -30,
            left: -30,
            width: 100,
            height: 100,
            borderRadius: '50%',
            backgroundColor: 'rgba(255, 255, 255, 0.05)',
          }}
        />
      </CardContent>
    </Card>
  );
}
