import React from 'react';
import {
  Card,
  CardContent,
  Typography,
  Box,
  IconButton,
  Chip,
  CircularProgress,
  LinearProgress,
} from '@mui/material';
import {
  TrendingUp,
  TrendingDown,
  TrendingFlat,
  MoreVert,
} from '@mui/icons-material';
import CountUp from 'react-countup';

export interface MetricCardProps {
  title: string;
  value: string | number;
  subtitle?: string;
  icon?: React.ReactNode;
  trend?: 'up' | 'down' | 'flat';
  trendValue?: string;
  color?: 'primary' | 'secondary' | 'success' | 'warning' | 'error' | 'info';
  loading?: boolean;
  progress?: number; // 0-100
  unit?: string;
  onClick?: () => void;
  actions?: React.ReactNode;
}

const MetricCard: React.FC<MetricCardProps> = ({
  title,
  value,
  subtitle,
  icon,
  trend,
  trendValue,
  color = 'primary',
  loading = false,
  progress,
  unit,
  onClick,
  actions,
}) => {
  const getTrendIcon = () => {
    switch (trend) {
      case 'up':
        return <TrendingUp fontSize="small" color="success" />;
      case 'down':
        return <TrendingDown fontSize="small" color="error" />;
      case 'flat':
        return <TrendingFlat fontSize="small" color="info" />;
      default:
        return null;
    }
  };

  const getTrendColor = () => {
    switch (trend) {
      case 'up':
        return 'success';
      case 'down':
        return 'error';
      case 'flat':
        return 'info';
      default:
        return 'default';
    }
  };

  return (
    <Card
      sx={{
        cursor: onClick ? 'pointer' : 'default',
        transition: 'all 0.2s ease-in-out',
        '&:hover': onClick ? {
          transform: 'translateY(-2px)',
          boxShadow: 4,
        } : {},
      }}
      onClick={onClick}
    >
      <CardContent>
        <Box display="flex" justifyContent="space-between" alignItems="flex-start" mb={2}>
          <Typography variant="h6" color="text.secondary" gutterBottom>
            {title}
          </Typography>
          <Box display="flex" alignItems="center" gap={1}>
            {icon && (
              <Box
                sx={{
                  color: `${color}.main`,
                  display: 'flex',
                  alignItems: 'center',
                }}
              >
                {icon}
              </Box>
            )}
            {actions && actions}
            {!actions && (
              <IconButton size="small" sx={{ opacity: 0.6 }}>
                <MoreVert fontSize="small" />
              </IconButton>
            )}
          </Box>
        </Box>

        {loading ? (
          <Box display="flex" justifyContent="center" py={2}>
            <CircularProgress size={32} color={color} />
          </Box>
        ) : (
          <>
            <Box display="flex" alignItems="baseline" mb={1}>
              <Typography
                variant="h4"
                component="div"
                color={`${color}.main`}
                sx={{ fontWeight: 'bold' }}
              >
                {typeof value === 'number' ? (
                  <CountUp
                    end={value}
                    duration={2}
                    separator=","
                    decimals={value % 1 !== 0 ? 1 : 0}
                  />
                ) : value}
              </Typography>
              {unit && (
                <Typography
                  variant="body2"
                  color="text.secondary"
                  sx={{ ml: 0.5 }}
                >
                  {unit}
                </Typography>
              )}
            </Box>

            {subtitle && (
              <Typography variant="body2" color="text.secondary" gutterBottom>
                {subtitle}
              </Typography>
            )}

            {progress !== undefined && (
              <Box sx={{ mt: 1 }}>
                <Box display="flex" justifyContent="space-between" alignItems="center" mb={0.5}>
                  <Typography variant="body2" color="text.secondary">
                    Progress
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    {progress}%
                  </Typography>
                </Box>
                <LinearProgress
                  variant="determinate"
                  value={progress}
                  color={color}
                  sx={{
                    height: 6,
                    borderRadius: 3,
                    backgroundColor: 'grey.200',
                  }}
                />
              </Box>
            )}

            {trend && trendValue && (
              <Box display="flex" alignItems="center" mt={1}>
                {getTrendIcon()}
                <Chip
                  label={trendValue}
                  size="small"
                  color={getTrendColor() as any}
                  variant="outlined"
                  sx={{ ml: 0.5, fontSize: '0.75rem' }}
                />
                <Typography variant="body2" color="text.secondary" sx={{ ml: 1 }}>
                  vs last period
                </Typography>
              </Box>
            )}
          </>
        )}
      </CardContent>
    </Card>
  );
};

export default MetricCard;