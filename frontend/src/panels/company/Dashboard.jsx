import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Box,
  Grid,
  Card,
  CardContent,
  Typography,
  Button,
  LinearProgress,
  Chip,
  Avatar,
  List,
  ListItem,
  ListItemText,
  ListItemAvatar,
  Divider,
  Paper,
  IconButton,
  Tooltip,
  Alert,
  CircularProgress,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Switch,
  FormControlLabel,
  TextField,
  Select,
  MenuItem,
  FormControl,
  InputLabel
} from '@mui/material';
import {
  Assessment,
  Nature,
  Business,
  AttachMoney,
  Settings,
  Refresh,
  Folder,
  CheckCircle,
  Schedule
} from '@mui/icons-material';

const CompanyDashboard = () => {
  const navigate = useNavigate();
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState(null);
  const [dashboardData, setDashboardData] = useState(null);

  // Load real data from company's unique database
  const loadDashboardData = async () => {
    try {
      setError(null);
      const token = localStorage.getItem('token');
      
      if (!token) {
        throw new Error('No authentication token found');
      }

      const response = await fetch('http://localhost:8000/api/company-dashboard/dashboard', {
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        }
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const data = await response.json();
      
      if (data.success) {
        setDashboardData(data.data);
        console.log('✅ Company dashboard data loaded:', data.data);
      } else {
        throw new Error(data.message || 'Failed to load dashboard data');
      }
    } catch (error) {
      console.error('Error loading dashboard data:', error);
      setError(error.message);
      
      // Fallback to basic structure if database not found
      if (error.message.includes('database not found')) {
        setDashboardData({
          profile: {
            company_name: 'Your Company',
            industry: 'Not specified',
            address: 'Not specified'
          },
          statistics: {
            totalProjects: 0,
            activeProjects: 0,
            completedProjects: 0,
            totalFiles: 0,
            totalImages: 0,
            totalCredits: 0
          },
          projects: [],
          recentFiles: [],
          recentActivity: []
        });
      }
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  // Load data on component mount
  useEffect(() => {
    loadDashboardData();
  }, []);

  const handleRefresh = async () => {
    setRefreshing(true);
    await loadDashboardData();
  };

  // Show loading state
  if (loading) {
    return (
      <Box sx={{ flexGrow: 1, p: 3, display: 'flex', justifyContent: 'center', alignItems: 'center', minHeight: '400px' }}>
        <Box sx={{ textAlign: 'center' }}>
          <CircularProgress size={60} sx={{ mb: 2 }} />
          <Typography variant="h6" color="text.secondary">
            Loading your company data...
          </Typography>
          <Typography variant="body2" color="text.secondary">
            Connecting to your unique database
          </Typography>
        </Box>
      </Box>
    );
  }

  // Show error state
  if (error && !dashboardData) {
    return (
      <Box sx={{ flexGrow: 1, p: 3 }}>
        <Alert severity="error" sx={{ mb: 3 }}>
          <Typography variant="h6">Failed to load company data</Typography>
          <Typography variant="body2">{error}</Typography>
          <Button 
            variant="contained" 
            onClick={loadDashboardData} 
            sx={{ mt: 2 }}
            startIcon={<Refresh />}
          >
            Retry
          </Button>
        </Alert>
      </Box>
    );
  }

  return (
    <Box sx={{ flexGrow: 1, p: 3 }}>
      {/* Header */}
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
        <Box>
          <Typography variant="h4" component="h1" sx={{ fontWeight: 'bold' }}>
            {dashboardData?.profile?.company_name || 'Company Dashboard'}
          </Typography>
          <Typography variant="subtitle1" color="text.secondary">
            {dashboardData?.profile?.industry || 'Your Industry'} • Real-time data from your unique database
          </Typography>
        </Box>
        <Box sx={{ display: 'flex', gap: 1 }}>
          <Tooltip title="Refresh Data">
            <IconButton 
              onClick={handleRefresh} 
              disabled={refreshing}
              color="primary"
            >
              <Refresh sx={{ 
                animation: refreshing ? 'spin 1s linear infinite' : 'none',
                '@keyframes spin': {
                  '0%': { transform: 'rotate(0deg)' },
                  '100%': { transform: 'rotate(360deg)' }
                }
              }} />
            </IconButton>
          </Tooltip>
          <Button
            variant="outlined"
            startIcon={<Settings />}
            onClick={() => navigate('/company/settings')}
          >
            Settings
          </Button>
        </Box>
      </Box>

      {/* Database Connection Status */}
      {dashboardData && (
        <Alert severity="success" sx={{ mb: 3 }}>
          <Typography variant="body2">
            ✅ Connected to your unique company database • 
            {dashboardData.statistics.totalProjects} projects • 
            {dashboardData.statistics.totalFiles} files • 
            {dashboardData.statistics.totalDataEntries} data entries
          </Typography>
        </Alert>
      )}

      {/* Statistics Cards */}
      <Grid container spacing={3} sx={{ mb: 4 }}>
        <Grid item xs={12} sm={6} md={3}>
          <Card sx={{ height: '100%' }}>
            <CardContent>
              <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                <Box>
                  <Typography color="textSecondary" gutterBottom variant="overline">
                    Total Projects
                  </Typography>
                  <Typography variant="h4" component="h2">
                    {dashboardData?.statistics?.totalProjects || 0}
                  </Typography>
                </Box>
                <Avatar sx={{ bgcolor: 'primary.main' }}>
                  <Assessment />
                </Avatar>
              </Box>
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12} sm={6} md={3}>
          <Card sx={{ height: '100%' }}>
            <CardContent>
              <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                <Box>
                  <Typography color="textSecondary" gutterBottom variant="overline">
                    Active Projects
                  </Typography>
                  <Typography variant="h4" component="h2">
                    {dashboardData?.statistics?.activeProjects || 0}
                  </Typography>
                </Box>
                <Avatar sx={{ bgcolor: 'success.main' }}>
                  <Nature />
                </Avatar>
              </Box>
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12} sm={6} md={3}>
          <Card sx={{ height: '100%' }}>
            <CardContent>
              <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                <Box>
                  <Typography color="textSecondary" gutterBottom variant="overline">
                    Total Budget
                  </Typography>
                  <Typography variant="h4" component="h2">
                    ${(dashboardData?.statistics?.totalCredits || 0).toLocaleString()}
                  </Typography>
                </Box>
                <Avatar sx={{ bgcolor: 'warning.main' }}>
                  <AttachMoney />
                </Avatar>
              </Box>
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12} sm={6} md={3}>
          <Card sx={{ height: '100%' }}>
            <CardContent>
              <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                <Box>
                  <Typography color="textSecondary" gutterBottom variant="overline">
                    Data Entries
                  </Typography>
                  <Typography variant="h4" component="h2">
                    {dashboardData?.statistics?.totalDataEntries || 0}
                  </Typography>
                </Box>
                <Avatar sx={{ bgcolor: 'info.main' }}>
                  <Folder />
                </Avatar>
              </Box>
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      <Grid container spacing={3}>
        {/* Recent Projects */}
        <Grid item xs={12} md={8}>
          <Card sx={{ height: '100%' }}>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                Recent Projects
              </Typography>
              {dashboardData?.projects && dashboardData.projects.length > 0 ? (
                <List>
                  {dashboardData.projects.slice(0, 5).map((project, index) => (
                    <React.Fragment key={project.id}>
                      <ListItem>
                        <ListItemAvatar>
                          <Avatar sx={{ 
                            bgcolor: project.status === 'active' ? 'success.main' : 
                                    project.status === 'completed' ? 'primary.main' : 'warning.main'
                          }}>
                            {project.status === 'active' ? <CheckCircle /> : 
                             project.status === 'completed' ? <Assessment /> : <Schedule />}
                          </Avatar>
                        </ListItemAvatar>
                        <ListItemText
                          primary={project.project_name}
                          secondary={
                            <Box>
                              <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1 }}>
                                <Chip 
                                  label={project.status || 'planning'} 
                                  size="small" 
                                  color={project.status === 'active' ? 'success' : 
                                        project.status === 'completed' ? 'primary' : 'warning'}
                                />
                                {project.budget && (
                                  <Typography variant="body2" color="text.secondary">
                                    Budget: ${project.budget.toLocaleString()}
                                  </Typography>
                                )}
                              </Box>
                              <Typography variant="body2" color="text.secondary">
                                {project.description || 'No description available'}
                              </Typography>
                              {project.start_date && (
                                <Typography variant="caption" color="text.secondary">
                                  Started: {new Date(project.start_date).toLocaleDateString()}
                                </Typography>
                              )}
                            </Box>
                          }
                        />
                      </ListItem>
                      {index < Math.min(dashboardData.projects.length - 1, 4) && <Divider />}
                    </React.Fragment>
                  ))}
                </List>
              ) : (
                <Box sx={{ textAlign: 'center', py: 4 }}>
                  <Assessment sx={{ fontSize: 48, color: 'text.secondary', mb: 2 }} />
                  <Typography variant="h6" color="text.secondary">
                    No Projects Yet
                  </Typography>
                  <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
                    Create your first project to get started
                  </Typography>
                  <Button 
                    variant="contained" 
                    startIcon={<Assessment />}
                    onClick={() => console.log('Create project')}
                  >
                    Create Project
                  </Button>
                </Box>
              )}
              {dashboardData?.projects && dashboardData.projects.length > 0 && (
                <Button 
                  variant="outlined" 
                  fullWidth 
                  sx={{ mt: 2 }}
                  onClick={() => console.log('View all projects')}
                >
                  View All {dashboardData.projects.length} Projects
                </Button>
              )}
            </CardContent>
          </Card>
        </Grid>

        {/* Company Information */}
        <Grid item xs={12} md={4}>
          <Card sx={{ height: '100%' }}>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                Company Information
              </Typography>
              {dashboardData?.profile ? (
                <Box>
                  <Typography variant="body1" sx={{ fontWeight: 'bold', mb: 1 }}>
                    {dashboardData.profile.company_name}
                  </Typography>
                  {dashboardData.profile.industry && (
                    <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
                      Industry: {dashboardData.profile.industry}
                    </Typography>
                  )}
                  {dashboardData.profile.address && (
                    <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
                      Address: {dashboardData.profile.address}
                    </Typography>
                  )}
                  {dashboardData.profile.phone && (
                    <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
                      Phone: {dashboardData.profile.phone}
                    </Typography>
                  )}
                  {dashboardData.profile.website && (
                    <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
                      Website: {dashboardData.profile.website}
                    </Typography>
                  )}
                  {dashboardData.profile.description && (
                    <Typography variant="body2" color="text.secondary" sx={{ mt: 2 }}>
                      {dashboardData.profile.description}
                    </Typography>
                  )}
                </Box>
              ) : (
                <Box sx={{ textAlign: 'center', py: 4 }}>
                  <Business sx={{ fontSize: 48, color: 'text.secondary', mb: 2 }} />
                  <Typography variant="h6" color="text.secondary">
                    No Company Profile
                  </Typography>
                  <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
                    Set up your company profile to get started
                  </Typography>
                  <Button 
                    variant="contained" 
                    startIcon={<Business />}
                    onClick={() => console.log('Setup profile')}
                  >
                    Setup Profile
                  </Button>
                </Box>
              )}
            </CardContent>
          </Card>
        </Grid>
      </Grid>

    </Box>
  );
};

export default CompanyDashboard;