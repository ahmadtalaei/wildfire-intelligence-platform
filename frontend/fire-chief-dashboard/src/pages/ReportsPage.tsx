import React, { useState, useEffect } from 'react';
import {
  Box,
  Paper,
  Typography,
  Card,
  CardContent,
  Grid,
  Button,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  IconButton,
  Tooltip,
  Chip,
  TextField,
  MenuItem,
  FormControl,
  InputLabel,
  Select,
} from '@mui/material';
import {
  Assessment,
  Download,
  Visibility,
  DateRange,
  TrendingUp,
  PictureAsPdf,
  TableChart,
} from '@mui/icons-material';
import { DatePicker } from '@mui/x-date-pickers/DatePicker';
import { LocalizationProvider } from '@mui/x-date-pickers/LocalizationProvider';
import { AdapterDateFns } from '@mui/x-date-pickers/AdapterDateFns';

interface Report {
  id: string;
  title: string;
  type: 'incident' | 'resource' | 'analytics' | 'compliance';
  status: 'draft' | 'pending' | 'completed' | 'archived';
  createdDate: string;
  generatedBy: string;
  format: 'pdf' | 'excel' | 'csv';
  size: string;
}

const ReportsPage: React.FC = () => {
  const [reports, setReports] = useState<Report[]>([]);
  const [loading, setLoading] = useState(true);
  const [filterType, setFilterType] = useState<string>('all');
  const [filterStatus, setFilterStatus] = useState<string>('all');
  const [dateRange, setDateRange] = useState<{start: Date | null, end: Date | null}>({
    start: null,
    end: null,
  });

  useEffect(() => {
    // Simulate API call
    const fetchReports = async () => {
      setLoading(true);
      try {
        // Mock data - replace with actual API call
        const mockReports: Report[] = [
          {
            id: '1',
            title: 'Weekly Incident Summary',
            type: 'incident',
            status: 'completed',
            createdDate: '2024-09-10',
            generatedBy: 'Chief Williams',
            format: 'pdf',
            size: '2.3 MB',
          },
          {
            id: '2',
            title: 'Resource Utilization Analysis',
            type: 'resource',
            status: 'pending',
            createdDate: '2024-09-09',
            generatedBy: 'System Auto',
            format: 'excel',
            size: '1.8 MB',
          },
          {
            id: '3',
            title: 'Fire Season Analytics',
            type: 'analytics',
            status: 'completed',
            createdDate: '2024-09-08',
            generatedBy: 'Analyst Johnson',
            format: 'pdf',
            size: '5.2 MB',
          },
          {
            id: '4',
            title: 'Compliance Audit Report',
            type: 'compliance',
            status: 'draft',
            createdDate: '2024-09-07',
            generatedBy: 'Inspector Davis',
            format: 'csv',
            size: '0.9 MB',
          },
        ];
        
        setReports(mockReports);
      } catch (error) {
        console.error('Failed to fetch reports:', error);
      } finally {
        setLoading(false);
      }
    };

    fetchReports();
  }, []);

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'completed': return 'success';
      case 'pending': return 'warning';
      case 'draft': return 'info';
      case 'archived': return 'default';
      default: return 'default';
    }
  };

  const getTypeIcon = (type: string) => {
    switch (type) {
      case 'incident': return <Assessment />;
      case 'resource': return <TableChart />;
      case 'analytics': return <TrendingUp />;
      case 'compliance': return <PictureAsPdf />;
      default: return <Assessment />;
    }
  };

  const getFormatIcon = (format: string) => {
    switch (format) {
      case 'pdf': return <PictureAsPdf />;
      case 'excel': return <TableChart />;
      case 'csv': return <TableChart />;
      default: return <Assessment />;
    }
  };

  const filteredReports = reports.filter(report => {
    const typeMatch = filterType === 'all' || report.type === filterType;
    const statusMatch = filterStatus === 'all' || report.status === filterStatus;
    return typeMatch && statusMatch;
  });

  const getReportStats = () => {
    return {
      total: reports.length,
      completed: reports.filter(r => r.status === 'completed').length,
      pending: reports.filter(r => r.status === 'pending').length,
      draft: reports.filter(r => r.status === 'draft').length,
    };
  };

  const stats = getReportStats();

  if (loading) {
    return (
      <Box display="flex" justifyContent="center" alignItems="center" minHeight="400px">
        <Typography>Loading reports...</Typography>
      </Box>
    );
  }

  return (
    <LocalizationProvider dateAdapter={AdapterDateFns}>
      <Box>
        <Typography variant="h4" gutterBottom>
          Reports & Analytics
        </Typography>

        <Grid container spacing={3} sx={{ mb: 3 }}>
          <Grid item xs={12} sm={6} md={3}>
            <Card>
              <CardContent>
                <Box display="flex" alignItems="center" mb={1}>
                  <Assessment color="primary" sx={{ mr: 1 }} />
                  <Typography variant="h6">Total Reports</Typography>
                </Box>
                <Typography variant="h4" color="primary">
                  {stats.total}
                </Typography>
              </CardContent>
            </Card>
          </Grid>

          <Grid item xs={12} sm={6} md={3}>
            <Card>
              <CardContent>
                <Box display="flex" alignItems="center" mb={1}>
                  <Typography variant="h6">Completed</Typography>
                </Box>
                <Typography variant="h4" color="success">
                  {stats.completed}
                </Typography>
              </CardContent>
            </Card>
          </Grid>

          <Grid item xs={12} sm={6} md={3}>
            <Card>
              <CardContent>
                <Box display="flex" alignItems="center" mb={1}>
                  <Typography variant="h6">Pending</Typography>
                </Box>
                <Typography variant="h4" color="warning">
                  {stats.pending}
                </Typography>
              </CardContent>
            </Card>
          </Grid>

          <Grid item xs={12} sm={6} md={3}>
            <Card>
              <CardContent>
                <Box display="flex" alignItems="center" mb={1}>
                  <Typography variant="h6">Draft</Typography>
                </Box>
                <Typography variant="h4" color="info">
                  {stats.draft}
                </Typography>
              </CardContent>
            </Card>
          </Grid>
        </Grid>

        <Paper sx={{ mb: 3 }}>
          <Box p={2}>
            <Typography variant="h6" gutterBottom>
              Quick Actions
            </Typography>
            <Grid container spacing={2}>
              <Grid item>
                <Button variant="contained" color="primary" startIcon={<Assessment />}>
                  Generate Incident Report
                </Button>
              </Grid>
              <Grid item>
                <Button variant="outlined" color="primary" startIcon={<TrendingUp />}>
                  Analytics Dashboard
                </Button>
              </Grid>
              <Grid item>
                <Button variant="outlined" color="primary" startIcon={<TableChart />}>
                  Resource Summary
                </Button>
              </Grid>
              <Grid item>
                <Button variant="outlined" color="primary" startIcon={<DateRange />}>
                  Scheduled Reports
                </Button>
              </Grid>
            </Grid>
          </Box>
        </Paper>

        <Paper>
          <Box p={2}>
            <Box display="flex" justifyContent="space-between" alignItems="center" mb={2}>
              <Typography variant="h6">Report History</Typography>
              <Box display="flex" gap={2}>
                <FormControl size="small" sx={{ minWidth: 120 }}>
                  <InputLabel>Type</InputLabel>
                  <Select
                    value={filterType}
                    onChange={(e) => setFilterType(e.target.value)}
                    label="Type"
                  >
                    <MenuItem value="all">All Types</MenuItem>
                    <MenuItem value="incident">Incident</MenuItem>
                    <MenuItem value="resource">Resource</MenuItem>
                    <MenuItem value="analytics">Analytics</MenuItem>
                    <MenuItem value="compliance">Compliance</MenuItem>
                  </Select>
                </FormControl>

                <FormControl size="small" sx={{ minWidth: 120 }}>
                  <InputLabel>Status</InputLabel>
                  <Select
                    value={filterStatus}
                    onChange={(e) => setFilterStatus(e.target.value)}
                    label="Status"
                  >
                    <MenuItem value="all">All Status</MenuItem>
                    <MenuItem value="completed">Completed</MenuItem>
                    <MenuItem value="pending">Pending</MenuItem>
                    <MenuItem value="draft">Draft</MenuItem>
                    <MenuItem value="archived">Archived</MenuItem>
                  </Select>
                </FormControl>
              </Box>
            </Box>

            <TableContainer>
              <Table>
                <TableHead>
                  <TableRow>
                    <TableCell>Type</TableCell>
                    <TableCell>Title</TableCell>
                    <TableCell>Status</TableCell>
                    <TableCell>Created Date</TableCell>
                    <TableCell>Generated By</TableCell>
                    <TableCell>Format</TableCell>
                    <TableCell>Size</TableCell>
                    <TableCell>Actions</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {filteredReports.map((report) => (
                    <TableRow key={report.id} hover>
                      <TableCell>
                        <Box display="flex" alignItems="center">
                          {getTypeIcon(report.type)}
                          <Typography variant="body2" sx={{ ml: 1, textTransform: 'capitalize' }}>
                            {report.type}
                          </Typography>
                        </Box>
                      </TableCell>
                      <TableCell>
                        <Typography variant="subtitle2">
                          {report.title}
                        </Typography>
                      </TableCell>
                      <TableCell>
                        <Chip
                          label={report.status.toUpperCase()}
                          color={getStatusColor(report.status) as any}
                          size="small"
                        />
                      </TableCell>
                      <TableCell>{report.createdDate}</TableCell>
                      <TableCell>{report.generatedBy}</TableCell>
                      <TableCell>
                        <Box display="flex" alignItems="center">
                          {getFormatIcon(report.format)}
                          <Typography variant="body2" sx={{ ml: 0.5 }}>
                            {report.format.toUpperCase()}
                          </Typography>
                        </Box>
                      </TableCell>
                      <TableCell>{report.size}</TableCell>
                      <TableCell>
                        <Tooltip title="View Report">
                          <IconButton size="small">
                            <Visibility />
                          </IconButton>
                        </Tooltip>
                        {report.status === 'completed' && (
                          <Tooltip title="Download">
                            <IconButton size="small">
                              <Download />
                            </IconButton>
                          </Tooltip>
                        )}
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </TableContainer>
          </Box>
        </Paper>
      </Box>
    </LocalizationProvider>
  );
};

export default ReportsPage;