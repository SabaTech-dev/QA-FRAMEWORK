import React from "react";
import {
  Skeleton,
  Box,
  Card,
  CardContent,
  Grid,
  Table,
  TableRow,
  TableCell,
  LinearProgress,
} from "@mui/material";

interface SkeletonLoaderProps {
  variant?: "card" | "table" | "list" | "text" | "chart";
  count?: number;
  height?: number;
}

const SkeletonLoader: React.FC<SkeletonLoaderProps> = ({
  variant = "card",
  count = 1,
  height = 200,
}) => {
  const renderCard = () => (
    <Card>
      <CardContent>
        <Skeleton variant="text" width="40%" height={30} />
        <Skeleton variant="text" width="80%" />
        <Skeleton variant="rectangular" height={height - 80} sx={{ mt: 2 }} />
      </CardContent>
    </Card>
  );

  const renderTable = () => (
    <Table>
      {[...Array(count)].map((_, i) => (
        <TableRow key={i}>
          <TableCell>
            <Skeleton variant="text" />
          </TableCell>
          <TableCell>
            <Skeleton variant="text" />
          </TableCell>
          <TableCell>
            <Skeleton variant="text" />
          </TableCell>
          <TableCell>
            <Skeleton variant="text" />
          </TableCell>
        </TableRow>
      ))}
    </Table>
  );

  const renderList = () => (
    <Box>
      {[...Array(count)].map((_, i) => (
        <Box key={i} sx={{ mb: 2, display: "flex", alignItems: "center" }}>
          <Skeleton variant="circular" width={40} height={40} sx={{ mr: 2 }} />
          <Box sx={{ flex: 1 }}>
            <Skeleton variant="text" width="60%" />
            <Skeleton variant="text" width="40%" />
          </Box>
        </Box>
      ))}
    </Box>
  );

  const renderText = () => (
    <Box>
      <Skeleton variant="text" width="100%" height={height} />
    </Box>
  );

  const renderChart = () => (
    <Card>
      <CardContent>
        <Skeleton variant="text" width="30%" height={30} />
        <Skeleton variant="rectangular" height={height - 60} sx={{ mt: 2 }} />
      </CardContent>
    </Card>
  );

  if (variant === "table") {
    return renderTable();
  }

  if (variant === "list") {
    return renderList();
  }

  if (variant === "text") {
    return renderText();
  }

  if (variant === "chart") {
    return renderChart();
  }

  return (
    <Grid container spacing={2}>
      {[...Array(count)].map((_, i) => (
        <Grid size={{ xs: 12, sm: 6, md: 4 }} key={i}>
          {renderCard()}
        </Grid>
      ))}
    </Grid>
  );
};

// Specialized skeleton components
export const CardSkeleton: React.FC = () => (
  <Card>
    <CardContent>
      <Skeleton variant="text" width="40%" height={30} />
      <Skeleton variant="text" width="80%" />
      <Skeleton variant="rectangular" height={120} sx={{ mt: 2 }} />
    </CardContent>
  </Card>
);

export const TableSkeleton: React.FC<{ rows?: number }> = ({ rows = 5 }) => (
  <Table>
    {[...Array(rows)].map((_, i) => (
      <TableRow key={i}>
        <TableCell>
          <Skeleton variant="text" />
        </TableCell>
        <TableCell>
          <Skeleton variant="text" />
        </TableCell>
        <TableCell>
          <Skeleton variant="text" />
        </TableCell>
        <TableCell>
          <Skeleton variant="text" />
        </TableCell>
      </TableRow>
    ))}
  </Table>
);

export const ChartSkeleton: React.FC<{ height?: number }> = ({
  height = 300,
}) => (
  <Card>
    <CardContent>
      <Skeleton variant="text" width="30%" height={30} />
      <Skeleton variant="rectangular" height={height - 60} sx={{ mt: 2 }} />
    </CardContent>
  </Card>
);

export const StatsCardSkeleton: React.FC = () => (
  <Card sx={{ height: "100%" }}>
    <CardContent>
      <Box
        sx={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "flex-start",
        }}
      >
        <Box sx={{ flex: 1 }}>
          <Skeleton variant="text" width="40%" height={20} />
          <Skeleton variant="text" width="60%" height={40} sx={{ mt: 1 }} />
          <Skeleton variant="text" width="30%" height={20} sx={{ mt: 1 }} />
        </Box>
        <Skeleton variant="circular" width={50} height={50} />
      </Box>
    </CardContent>
  </Card>
);

export const ShimmerEffect: React.FC = () => <LinearProgress sx={{ mb: 2 }} />;

export default SkeletonLoader;
