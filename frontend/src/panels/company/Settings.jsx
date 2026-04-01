import React, { useState, useEffect } from 'react';
import {
  Box,
  Card,
  CardContent,
  Typography,
  Button,
  Switch,
  FormControlLabel,
  TextField,
  Select,
  MenuItem,
  FormControl,
  InputLabel,
  Tabs,
  Tab,
  Divider,
  Avatar,
  IconButton,
  Alert,
  Chip,
  Grid,
  Paper,
  CircularProgress
} from '@mui/material';
import {
  Settings as SettingsIcon,
  Person,
  Business,
  Notifications,
  Security,
  Palette,
  Language,
  Storage,
  Email,
  Lock,
  Visibility,
  VisibilityOff,
  PhotoCamera,
  Save,
  Cancel
} from '@mui/icons-material';
import { blueCarbon } from '../../theme/colors';

function TabPanel({ children, value, index }) {
  return (
    <div hidden={value !== index}>
      {value === index && <Box sx={{ py: 3 }}>{children}</Box>}
    </div>
  );
}

const CompanySettings = () => {
  const [currentTab, setCurrentTab] = useState(0);
  const [saveSuccess, setSaveSuccess] = useState(false);
  const [showPassword, setShowPassword] = useState(false);
  const [loading, setLoading] = useState(true);
  const [userInfo, setUserInfo] = useState(null);

  // Profile Settings
  const [profileSettings, setProfileSettings] = useState({
    companyName: '',
    industry: '',
    email: '',
    phone: '',
    address: '',
    website: '',
    description: '',
    logo: null
  });

  // Notification Settings
  const [notificationSettings, setNotificationSettings] = useState({
    emailNotifications: true,
    pushNotifications: true,
    projectUpdates: true,
    creditAlerts: true,
    complianceAlerts: true,
    marketplaceUpdates: false,
    weeklyReports: true,
    monthlyReports: true
  });

  // Security Settings
  const [securitySettings, setSecuritySettings] = useState({
    twoFactorAuth: false,
    loginAlerts: true,
    sessionTimeout: 30,
    ipWhitelist: ''
  });

  // Password Change with Email Verification
  const [passwordChange, setPasswordChange] = useState({
    step: 1, // 1: Request, 2: Verify Code, 3: Change Password
    verificationCode: '',
    newPassword: '',
    confirmPassword: '',
    verificationSent: false,
    loading: false,
    error: null
  });

  // Appearance Settings
  const [appearanceSettings, setAppearanceSettings] = useState({
    theme: 'light',
    language: 'en',
    dateFormat: 'DD/MM/YYYY',
    timeFormat: '24h',
    currency: 'INR',
    timezone: 'Asia/Kolkata'
  });

  // Data & Privacy Settings
  const [dataSettings, setDataSettings] = useState({
    dataRetention: 365,
    autoBackup: true,
    backupFrequency: 'daily',
    shareAnalytics: false,
    allowCookies: true
  });

  // Load user-specific data on mount
  useEffect(() => {
    loadUserData();
    loadSavedSettings();
  }, []);

  const loadUserData = async () => {
    try {
      const token = localStorage.getItem('token');
      const user = JSON.parse(localStorage.getItem('user'));
      
      if (user) {
        setUserInfo(user);
        
        // Load company profile from database
        const response = await fetch('http://localhost:8000/api/company-dashboard/dashboard', {
          headers: {
            'Authorization': `Bearer ${token}`,
            'Content-Type': 'application/json'
          }
        });

        if (response.ok) {
          const data = await response.json();
          if (data.success && data.data.profile) {
            setProfileSettings({
              companyName: data.data.profile.company_name || user.organization || '',
              industry: data.data.profile.industry || 'Technology',
              email: user.email || '',
              phone: data.data.profile.phone || '',
              address: data.data.profile.address || '',
              website: data.data.profile.website || '',
              description: data.data.profile.description || '',
              logo: data.data.profile.logo_path || null
            });
          } else {
            // Fallback to user data
            setProfileSettings({
              companyName: user.organization || user.name || '',
              industry: 'Technology',
              email: user.email || '',
              phone: '',
              address: '',
              website: '',
              description: '',
              logo: null
            });
          }
        }
      }
    } catch (error) {
      console.error('Error loading user data:', error);
    } finally {
      setLoading(false);
    }
  };

  const loadSavedSettings = () => {
    // Load saved settings from localStorage
    const savedNotifications = localStorage.getItem('companyNotificationSettings');
    const savedSecurity = localStorage.getItem('companySecuritySettings');
    const savedAppearance = localStorage.getItem('companyAppearanceSettings');
    const savedData = localStorage.getItem('companyDataSettings');

    if (savedNotifications) {
      setNotificationSettings(JSON.parse(savedNotifications));
    }
    if (savedSecurity) {
      const security = JSON.parse(savedSecurity);
      setSecuritySettings({
        twoFactorAuth: security.twoFactorAuth || false,
        loginAlerts: security.loginAlerts !== undefined ? security.loginAlerts : true,
        sessionTimeout: security.sessionTimeout || 30,
        ipWhitelist: security.ipWhitelist || ''
      });
    }
    if (savedAppearance) {
      setAppearanceSettings(JSON.parse(savedAppearance));
    }
    if (savedData) {
      setDataSettings(JSON.parse(savedData));
    }
  };

  const handleSaveSettings = async () => {
    try {
      const token = localStorage.getItem('token');
      
      // Save profile to backend
      const response = await fetch('http://localhost:8000/api/company-dashboard/profile', {
        method: 'PUT',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify(profileSettings)
      });

      if (response.ok) {
        // Save other settings to localStorage
        localStorage.setItem('companyProfileSettings', JSON.stringify(profileSettings));
        localStorage.setItem('companyNotificationSettings', JSON.stringify(notificationSettings));
        localStorage.setItem('companySecuritySettings', JSON.stringify(securitySettings));
        localStorage.setItem('companyAppearanceSettings', JSON.stringify(appearanceSettings));
        localStorage.setItem('companyDataSettings', JSON.stringify(dataSettings));
        
        setSaveSuccess(true);
        setTimeout(() => setSaveSuccess(false), 3000);
      } else {
        alert('Failed to save settings');
      }
    } catch (error) {
      console.error('Error saving settings:', error);
      alert('Error saving settings');
    }
  };

  const handleLogoUpload = (event) => {
    const file = event.target.files[0];
    if (file) {
      const reader = new FileReader();
      reader.onloadend = () => {
        setProfileSettings({...profileSettings, logo: reader.result});
      };
      reader.readAsDataURL(file);
    }
  };

  // Password Change Functions
  const handleRequestVerification = async () => {
    setPasswordChange({...passwordChange, loading: true, error: null});
    
    try {
      const token = localStorage.getItem('token');
      const response = await fetch('http://localhost:8000/api/password/request-verification', {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        }
      });

      const data = await response.json();

      if (data.success) {
        setPasswordChange({
          ...passwordChange,
          step: 2,
          verificationSent: true,
          loading: false,
          error: null
        });
        alert('Verification code sent to your email!');
      } else {
        setPasswordChange({
          ...passwordChange,
          loading: false,
          error: data.message || 'Failed to send verification code'
        });
      }
    } catch (error) {
      setPasswordChange({
        ...passwordChange,
        loading: false,
        error: 'Network error. Please try again.'
      });
    }
  };

  const handleVerifyCode = async () => {
    if (!passwordChange.verificationCode) {
      setPasswordChange({...passwordChange, error: 'Please enter verification code'});
      return;
    }

    setPasswordChange({...passwordChange, loading: true, error: null});

    try {
      const token = localStorage.getItem('token');
      const response = await fetch('http://localhost:8000/api/password/verify-code', {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          code: passwordChange.verificationCode
        })
      });

      const data = await response.json();

      if (data.success) {
        setPasswordChange({
          ...passwordChange,
          step: 3,
          loading: false,
          error: null
        });
      } else {
        setPasswordChange({
          ...passwordChange,
          loading: false,
          error: data.message || 'Invalid verification code'
        });
      }
    } catch (error) {
      setPasswordChange({
        ...passwordChange,
        loading: false,
        error: 'Network error. Please try again.'
      });
    }
  };

  const handleChangePassword = async () => {
    if (!passwordChange.newPassword || !passwordChange.confirmPassword) {
      setPasswordChange({...passwordChange, error: 'Please fill all fields'});
      return;
    }

    if (passwordChange.newPassword !== passwordChange.confirmPassword) {
      setPasswordChange({...passwordChange, error: 'Passwords do not match'});
      return;
    }

    if (passwordChange.newPassword.length < 8) {
      setPasswordChange({...passwordChange, error: 'Password must be at least 8 characters'});
      return;
    }

    setPasswordChange({...passwordChange, loading: true, error: null});

    try {
      const token = localStorage.getItem('token');
      const response = await fetch('http://localhost:8000/api/password/change-password', {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          code: passwordChange.verificationCode,
          newPassword: passwordChange.newPassword
        })
      });

      const data = await response.json();

      if (data.success) {
        alert('Password changed successfully!');
        setPasswordChange({
          step: 1,
          verificationCode: '',
          newPassword: '',
          confirmPassword: '',
          verificationSent: false,
          loading: false,
          error: null
        });
      } else {
        setPasswordChange({
          ...passwordChange,
          loading: false,
          error: data.message || 'Failed to change password'
        });
      }
    } catch (error) {
      setPasswordChange({
        ...passwordChange,
        loading: false,
        error: 'Network error. Please try again.'
      });
    }
  };

  if (loading) {
    return (
      <Box sx={{ p: 3, display: 'flex', justifyContent: 'center', alignItems: 'center', minHeight: '400px' }}>
        <CircularProgress />
      </Box>
    );
  }

  return (
    <Box sx={{ p: 3 }}>
      {/* Header */}
      <Box sx={{ mb: 4 }}>
        <Typography variant="h4" sx={{ 
          fontWeight: 700,
          background: blueCarbon.gradients.oceanDepth,
          WebkitBackgroundClip: 'text',
          WebkitTextFillColor: 'transparent',
          mb: 1
        }}>
          Company Settings
        </Typography>
        <Typography variant="body2" color="text.secondary">
          Manage your company profile, preferences, and security settings
        </Typography>
        {userInfo && (
          <Chip 
            label={`Logged in as: ${userInfo.email}`} 
            size="small" 
            sx={{ mt: 1 }}
            color="primary"
          />
        )}
      </Box>

      {saveSuccess && (
        <Alert severity="success" sx={{ mb: 3 }}>
          Settings saved successfully!
        </Alert>
      )}

      {/* Settings Tabs */}
      <Card sx={{ 
        borderRadius: 3,
        boxShadow: `0 4px 20px ${blueCarbon.alpha.oceanBlue[20]}`
      }}>
        <Box sx={{ borderBottom: 1, borderColor: 'divider' }}>
          <Tabs 
            value={currentTab} 
            onChange={(e, newValue) => setCurrentTab(newValue)}
            variant="scrollable"
            scrollButtons="auto"
            sx={{
              '& .MuiTab-root': {
                minHeight: 64,
                textTransform: 'none',
                fontSize: '0.95rem',
                fontWeight: 500
              }
            }}
          >
            <Tab icon={<Person />} label="Profile" iconPosition="start" />
            <Tab icon={<Notifications />} label="Notifications" iconPosition="start" />
            <Tab icon={<Security />} label="Security" iconPosition="start" />
            <Tab icon={<Palette />} label="Appearance" iconPosition="start" />
            <Tab icon={<Storage />} label="Data & Privacy" iconPosition="start" />
          </Tabs>
        </Box>

        <CardContent sx={{ p: 4 }}>
          {/* Profile Tab */}
          <TabPanel value={currentTab} index={0}>
            <Grid container spacing={3}>
              {/* Logo Upload */}
              <Grid item xs={12}>
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 3 }}>
                  <Avatar
                    src={profileSettings.logo}
                    sx={{ 
                      width: 100, 
                      height: 100,
                      background: blueCarbon.gradients.oceanDepth
                    }}
                  >
                    <Business sx={{ fontSize: 50 }} />
                  </Avatar>
                  <Box>
                    <Typography variant="subtitle2" gutterBottom>
                      Company Logo
                    </Typography>
                    <input
                      accept="image/*"
                      style={{ display: 'none' }}
                      id="logo-upload"
                      type="file"
                      onChange={handleLogoUpload}
                    />
                    <label htmlFor="logo-upload">
                      <Button
                        variant="outlined"
                        component="span"
                        startIcon={<PhotoCamera />}
                        size="small"
                      >
                        Upload Logo
                      </Button>
                    </label>
                    <Typography variant="caption" display="block" sx={{ mt: 1 }}>
                      Recommended: 500x500px, PNG or JPG
                    </Typography>
                  </Box>
                </Box>
              </Grid>

              {/* Company Name */}
              <Grid item xs={12} md={6}>
                <TextField
                  fullWidth
                  label="Company Name"
                  value={profileSettings.companyName}
                  onChange={(e) => setProfileSettings({...profileSettings, companyName: e.target.value})}
                />
              </Grid>

              {/* Industry */}
              <Grid item xs={12} md={6}>
                <FormControl fullWidth>
                  <InputLabel>Industry</InputLabel>
                  <Select
                    value={profileSettings.industry}
                    label="Industry"
                    onChange={(e) => setProfileSettings({...profileSettings, industry: e.target.value})}
                  >
                    <MenuItem value="Technology">Technology</MenuItem>
                    <MenuItem value="Environmental">Environmental Services</MenuItem>
                    <MenuItem value="Energy">Renewable Energy</MenuItem>
                    <MenuItem value="Agriculture">Agriculture</MenuItem>
                    <MenuItem value="Consulting">Consulting</MenuItem>
                    <MenuItem value="Other">Other</MenuItem>
                  </Select>
                </FormControl>
              </Grid>

              {/* Email */}
              <Grid item xs={12} md={6}>
                <TextField
                  fullWidth
                  label="Email"
                  type="email"
                  value={profileSettings.email}
                  onChange={(e) => setProfileSettings({...profileSettings, email: e.target.value})}
                />
              </Grid>

              {/* Phone */}
              <Grid item xs={12} md={6}>
                <TextField
                  fullWidth
                  label="Phone"
                  value={profileSettings.phone}
                  onChange={(e) => setProfileSettings({...profileSettings, phone: e.target.value})}
                />
              </Grid>

              {/* Website */}
              <Grid item xs={12} md={6}>
                <TextField
                  fullWidth
                  label="Website"
                  value={profileSettings.website}
                  onChange={(e) => setProfileSettings({...profileSettings, website: e.target.value})}
                />
              </Grid>

              {/* Address */}
              <Grid item xs={12} md={6}>
                <TextField
                  fullWidth
                  label="Address"
                  value={profileSettings.address}
                  onChange={(e) => setProfileSettings({...profileSettings, address: e.target.value})}
                />
              </Grid>

              {/* Description */}
              <Grid item xs={12}>
                <TextField
                  fullWidth
                  label="Company Description"
                  multiline
                  rows={4}
                  value={profileSettings.description}
                  onChange={(e) => setProfileSettings({...profileSettings, description: e.target.value})}
                />
              </Grid>
            </Grid>
          </TabPanel>

          {/* Notifications Tab */}
          <TabPanel value={currentTab} index={1}>
            <Grid container spacing={3}>
              <Grid item xs={12}>
                <Typography variant="h6" gutterBottom>
                  Email Notifications
                </Typography>
                <Divider sx={{ mb: 2 }} />
              </Grid>

              <Grid item xs={12} md={6}>
                <FormControlLabel
                  control={
                    <Switch
                      checked={notificationSettings.emailNotifications}
                      onChange={(e) => setNotificationSettings({...notificationSettings, emailNotifications: e.target.checked})}
                    />
                  }
                  label="Enable Email Notifications"
                />
              </Grid>

              <Grid item xs={12} md={6}>
                <FormControlLabel
                  control={
                    <Switch
                      checked={notificationSettings.projectUpdates}
                      onChange={(e) => setNotificationSettings({...notificationSettings, projectUpdates: e.target.checked})}
                    />
                  }
                  label="Project Updates"
                />
              </Grid>

              <Grid item xs={12} md={6}>
                <FormControlLabel
                  control={
                    <Switch
                      checked={notificationSettings.creditAlerts}
                      onChange={(e) => setNotificationSettings({...notificationSettings, creditAlerts: e.target.checked})}
                    />
                  }
                  label="Carbon Credit Alerts"
                />
              </Grid>

              <Grid item xs={12} md={6}>
                <FormControlLabel
                  control={
                    <Switch
                      checked={notificationSettings.complianceAlerts}
                      onChange={(e) => setNotificationSettings({...notificationSettings, complianceAlerts: e.target.checked})}
                    />
                  }
                  label="Compliance Alerts"
                />
              </Grid>

              <Grid item xs={12} md={6}>
                <FormControlLabel
                  control={
                    <Switch
                      checked={notificationSettings.marketplaceUpdates}
                      onChange={(e) => setNotificationSettings({...notificationSettings, marketplaceUpdates: e.target.checked})}
                    />
                  }
                  label="Marketplace Updates"
                />
              </Grid>

              <Grid item xs={12}>
                <Typography variant="h6" gutterBottom sx={{ mt: 2 }}>
                  Reports
                </Typography>
                <Divider sx={{ mb: 2 }} />
              </Grid>

              <Grid item xs={12} md={6}>
                <FormControlLabel
                  control={
                    <Switch
                      checked={notificationSettings.weeklyReports}
                      onChange={(e) => setNotificationSettings({...notificationSettings, weeklyReports: e.target.checked})}
                    />
                  }
                  label="Weekly Summary Reports"
                />
              </Grid>

              <Grid item xs={12} md={6}>
                <FormControlLabel
                  control={
                    <Switch
                      checked={notificationSettings.monthlyReports}
                      onChange={(e) => setNotificationSettings({...notificationSettings, monthlyReports: e.target.checked})}
                    />
                  }
                  label="Monthly Analytics Reports"
                />
              </Grid>
            </Grid>
          </TabPanel>

          {/* Security Tab */}
          <TabPanel value={currentTab} index={2}>
            <Grid container spacing={3}>
              <Grid item xs={12}>
                <Typography variant="h6" gutterBottom>
                  Account Security
                </Typography>
                <Divider sx={{ mb: 2 }} />
              </Grid>

              <Grid item xs={12} md={6}>
                <FormControlLabel
                  control={
                    <Switch
                      checked={securitySettings.twoFactorAuth}
                      onChange={(e) => setSecuritySettings({...securitySettings, twoFactorAuth: e.target.checked})}
                    />
                  }
                  label="Two-Factor Authentication"
                />
                <Typography variant="caption" display="block" color="text.secondary">
                  Add an extra layer of security to your account
                </Typography>
              </Grid>

              <Grid item xs={12} md={6}>
                <FormControlLabel
                  control={
                    <Switch
                      checked={securitySettings.loginAlerts}
                      onChange={(e) => setSecuritySettings({...securitySettings, loginAlerts: e.target.checked})}
                    />
                  }
                  label="Login Alerts"
                />
                <Typography variant="caption" display="block" color="text.secondary">
                  Get notified of new login attempts
                </Typography>
              </Grid>

              <Grid item xs={12} md={6}>
                <FormControl fullWidth>
                  <InputLabel>Session Timeout</InputLabel>
                  <Select
                    value={securitySettings.sessionTimeout}
                    label="Session Timeout"
                    onChange={(e) => setSecuritySettings({...securitySettings, sessionTimeout: e.target.value})}
                  >
                    <MenuItem value={15}>15 minutes</MenuItem>
                    <MenuItem value={30}>30 minutes</MenuItem>
                    <MenuItem value={60}>1 hour</MenuItem>
                    <MenuItem value={120}>2 hours</MenuItem>
                    <MenuItem value={0}>Never</MenuItem>
                  </Select>
                </FormControl>
              </Grid>

              <Grid item xs={12}>
                <Typography variant="h6" gutterBottom sx={{ mt: 2 }}>
                  Change Password
                </Typography>
                <Divider sx={{ mb: 2 }} />
              </Grid>

              {passwordChange.error && (
                <Grid item xs={12}>
                  <Alert severity="error">{passwordChange.error}</Alert>
                </Grid>
              )}

              {/* Step 1: Request Verification */}
              {passwordChange.step === 1 && (
                <Grid item xs={12}>
                  <Paper sx={{ p: 3, background: blueCarbon.alpha.oceanBlue[5] }}>
                    <Typography variant="body2" gutterBottom>
                      To change your password, we'll send a verification code to your registered email address.
                    </Typography>
                    <Button
                      variant="contained"
                      startIcon={<Email />}
                      onClick={handleRequestVerification}
                      disabled={passwordChange.loading}
                      sx={{
                        mt: 2,
                        background: blueCarbon.gradients.oceanDepth,
                        '&:hover': {
                          background: blueCarbon.gradients.shallowWater
                        }
                      }}
                    >
                      {passwordChange.loading ? 'Sending...' : 'Send Verification Code'}
                    </Button>
                  </Paper>
                </Grid>
              )}

              {/* Step 2: Verify Code */}
              {passwordChange.step === 2 && (
                <>
                  <Grid item xs={12}>
                    <Alert severity="info">
                      A verification code has been sent to your email. Please check your inbox.
                    </Alert>
                  </Grid>
                  <Grid item xs={12}>
                    <TextField
                      fullWidth
                      label="Verification Code"
                      placeholder="Enter 6-digit code"
                      value={passwordChange.verificationCode}
                      onChange={(e) => setPasswordChange({...passwordChange, verificationCode: e.target.value})}
                      inputProps={{ maxLength: 6 }}
                    />
                  </Grid>
                  <Grid item xs={12}>
                    <Box sx={{ display: 'flex', gap: 2 }}>
                      <Button
                        variant="contained"
                        onClick={handleVerifyCode}
                        disabled={passwordChange.loading || !passwordChange.verificationCode}
                        sx={{
                          background: blueCarbon.gradients.oceanDepth,
                          '&:hover': {
                            background: blueCarbon.gradients.shallowWater
                          }
                        }}
                      >
                        {passwordChange.loading ? 'Verifying...' : 'Verify Code'}
                      </Button>
                      <Button
                        variant="outlined"
                        onClick={handleRequestVerification}
                        disabled={passwordChange.loading}
                      >
                        Resend Code
                      </Button>
                    </Box>
                  </Grid>
                </>
              )}

              {/* Step 3: Change Password */}
              {passwordChange.step === 3 && (
                <>
                  <Grid item xs={12}>
                    <Alert severity="success">
                      Code verified! Now enter your new password.
                    </Alert>
                  </Grid>
                  <Grid item xs={12} md={6}>
                    <TextField
                      fullWidth
                      label="New Password"
                      type={showPassword ? 'text' : 'password'}
                      value={passwordChange.newPassword}
                      onChange={(e) => setPasswordChange({...passwordChange, newPassword: e.target.value})}
                      InputProps={{
                        endAdornment: (
                          <IconButton onClick={() => setShowPassword(!showPassword)}>
                            {showPassword ? <VisibilityOff /> : <Visibility />}
                          </IconButton>
                        )
                      }}
                      helperText="Minimum 8 characters"
                    />
                  </Grid>
                  <Grid item xs={12} md={6}>
                    <TextField
                      fullWidth
                      label="Confirm New Password"
                      type={showPassword ? 'text' : 'password'}
                      value={passwordChange.confirmPassword}
                      onChange={(e) => setPasswordChange({...passwordChange, confirmPassword: e.target.value})}
                    />
                  </Grid>
                  <Grid item xs={12}>
                    <Button
                      variant="contained"
                      startIcon={<Lock />}
                      onClick={handleChangePassword}
                      disabled={passwordChange.loading || !passwordChange.newPassword || !passwordChange.confirmPassword}
                      sx={{
                        background: blueCarbon.gradients.oceanDepth,
                        '&:hover': {
                          background: blueCarbon.gradients.shallowWater
                        }
                      }}
                    >
                      {passwordChange.loading ? 'Changing Password...' : 'Change Password'}
                    </Button>
                  </Grid>
                </>
              )}
            </Grid>
          </TabPanel>

          {/* Appearance Tab */}
          <TabPanel value={currentTab} index={3}>
            <Grid container spacing={3}>
              <Grid item xs={12} md={6}>
                <FormControl fullWidth>
                  <InputLabel>Theme</InputLabel>
                  <Select
                    value={appearanceSettings.theme}
                    label="Theme"
                    onChange={(e) => setAppearanceSettings({...appearanceSettings, theme: e.target.value})}
                  >
                    <MenuItem value="light">Light</MenuItem>
                    <MenuItem value="dark">Dark</MenuItem>
                    <MenuItem value="auto">Auto (System)</MenuItem>
                  </Select>
                </FormControl>
              </Grid>

              <Grid item xs={12} md={6}>
                <FormControl fullWidth>
                  <InputLabel>Language</InputLabel>
                  <Select
                    value={appearanceSettings.language}
                    label="Language"
                    onChange={(e) => setAppearanceSettings({...appearanceSettings, language: e.target.value})}
                  >
                    <MenuItem value="en">English</MenuItem>
                    <MenuItem value="hi">हिंदी (Hindi)</MenuItem>
                    <MenuItem value="es">Español (Spanish)</MenuItem>
                    <MenuItem value="fr">Français (French)</MenuItem>
                    <MenuItem value="de">Deutsch (German)</MenuItem>
                  </Select>
                </FormControl>
              </Grid>

              <Grid item xs={12} md={6}>
                <FormControl fullWidth>
                  <InputLabel>Date Format</InputLabel>
                  <Select
                    value={appearanceSettings.dateFormat}
                    label="Date Format"
                    onChange={(e) => setAppearanceSettings({...appearanceSettings, dateFormat: e.target.value})}
                  >
                    <MenuItem value="DD/MM/YYYY">DD/MM/YYYY</MenuItem>
                    <MenuItem value="MM/DD/YYYY">MM/DD/YYYY</MenuItem>
                    <MenuItem value="YYYY-MM-DD">YYYY-MM-DD</MenuItem>
                  </Select>
                </FormControl>
              </Grid>

              <Grid item xs={12} md={6}>
                <FormControl fullWidth>
                  <InputLabel>Time Format</InputLabel>
                  <Select
                    value={appearanceSettings.timeFormat}
                    label="Time Format"
                    onChange={(e) => setAppearanceSettings({...appearanceSettings, timeFormat: e.target.value})}
                  >
                    <MenuItem value="12h">12 Hour</MenuItem>
                    <MenuItem value="24h">24 Hour</MenuItem>
                  </Select>
                </FormControl>
              </Grid>

              <Grid item xs={12} md={6}>
                <FormControl fullWidth>
                  <InputLabel>Currency</InputLabel>
                  <Select
                    value={appearanceSettings.currency}
                    label="Currency"
                    onChange={(e) => setAppearanceSettings({...appearanceSettings, currency: e.target.value})}
                  >
                    <MenuItem value="INR">₹ INR (Indian Rupee)</MenuItem>
                    <MenuItem value="USD">$ USD (US Dollar)</MenuItem>
                    <MenuItem value="EUR">€ EUR (Euro)</MenuItem>
                    <MenuItem value="GBP">£ GBP (British Pound)</MenuItem>
                  </Select>
                </FormControl>
              </Grid>

              <Grid item xs={12} md={6}>
                <FormControl fullWidth>
                  <InputLabel>Timezone</InputLabel>
                  <Select
                    value={appearanceSettings.timezone}
                    label="Timezone"
                    onChange={(e) => setAppearanceSettings({...appearanceSettings, timezone: e.target.value})}
                  >
                    <MenuItem value="Asia/Kolkata">Asia/Kolkata (IST)</MenuItem>
                    <MenuItem value="America/New_York">America/New_York (EST)</MenuItem>
                    <MenuItem value="Europe/London">Europe/London (GMT)</MenuItem>
                    <MenuItem value="Asia/Tokyo">Asia/Tokyo (JST)</MenuItem>
                  </Select>
                </FormControl>
              </Grid>
            </Grid>
          </TabPanel>

          {/* Data & Privacy Tab */}
          <TabPanel value={currentTab} index={4}>
            <Grid container spacing={3}>
              <Grid item xs={12}>
                <Typography variant="h6" gutterBottom>
                  Data Management
                </Typography>
                <Divider sx={{ mb: 2 }} />
              </Grid>

              <Grid item xs={12} md={6}>
                <FormControl fullWidth>
                  <InputLabel>Data Retention Period</InputLabel>
                  <Select
                    value={dataSettings.dataRetention}
                    label="Data Retention Period"
                    onChange={(e) => setDataSettings({...dataSettings, dataRetention: e.target.value})}
                  >
                    <MenuItem value={90}>90 days</MenuItem>
                    <MenuItem value={180}>180 days</MenuItem>
                    <MenuItem value={365}>1 year</MenuItem>
                    <MenuItem value={730}>2 years</MenuItem>
                    <MenuItem value={-1}>Forever</MenuItem>
                  </Select>
                </FormControl>
              </Grid>

              <Grid item xs={12} md={6}>
                <FormControlLabel
                  control={
                    <Switch
                      checked={dataSettings.autoBackup}
                      onChange={(e) => setDataSettings({...dataSettings, autoBackup: e.target.checked})}
                    />
                  }
                  label="Automatic Backups"
                />
              </Grid>

              {dataSettings.autoBackup && (
                <Grid item xs={12} md={6}>
                  <FormControl fullWidth>
                    <InputLabel>Backup Frequency</InputLabel>
                    <Select
                      value={dataSettings.backupFrequency}
                      label="Backup Frequency"
                      onChange={(e) => setDataSettings({...dataSettings, backupFrequency: e.target.value})}
                    >
                      <MenuItem value="daily">Daily</MenuItem>
                      <MenuItem value="weekly">Weekly</MenuItem>
                      <MenuItem value="monthly">Monthly</MenuItem>
                    </Select>
                  </FormControl>
                </Grid>
              )}

              <Grid item xs={12}>
                <Typography variant="h6" gutterBottom sx={{ mt: 2 }}>
                  Privacy
                </Typography>
                <Divider sx={{ mb: 2 }} />
              </Grid>

              <Grid item xs={12} md={6}>
                <FormControlLabel
                  control={
                    <Switch
                      checked={dataSettings.shareAnalytics}
                      onChange={(e) => setDataSettings({...dataSettings, shareAnalytics: e.target.checked})}
                    />
                  }
                  label="Share Anonymous Analytics"
                />
                <Typography variant="caption" display="block" color="text.secondary">
                  Help us improve by sharing anonymous usage data
                </Typography>
              </Grid>

              <Grid item xs={12} md={6}>
                <FormControlLabel
                  control={
                    <Switch
                      checked={dataSettings.allowCookies}
                      onChange={(e) => setDataSettings({...dataSettings, allowCookies: e.target.checked})}
                    />
                  }
                  label="Allow Cookies"
                />
                <Typography variant="caption" display="block" color="text.secondary">
                  Required for proper functionality
                </Typography>
              </Grid>

              <Grid item xs={12}>
                <Paper sx={{ p: 2, background: 'rgba(244, 67, 54, 0.05)', border: '1px solid rgba(244, 67, 54, 0.2)' }}>
                  <Typography variant="subtitle2" color="error" gutterBottom>
                    Danger Zone
                  </Typography>
                  <Box sx={{ display: 'flex', gap: 2, mt: 2 }}>
                    <Button
                      variant="outlined"
                      color="error"
                      size="small"
                      onClick={() => {
                        if (window.confirm('Clear all cached data? This cannot be undone.')) {
                          localStorage.clear();
                          alert('All cached data cleared!');
                        }
                      }}
                    >
                      Clear All Data
                    </Button>
                    <Button
                      variant="outlined"
                      color="error"
                      size="small"
                      onClick={() => {
                        const data = {
                          profile: profileSettings,
                          notifications: notificationSettings,
                          security: securitySettings,
                          appearance: appearanceSettings,
                          data: dataSettings
                        };
                        const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
                        const url = URL.createObjectURL(blob);
                        const a = document.createElement('a');
                        a.href = url;
                        a.download = 'company-settings-export.json';
                        a.click();
                      }}
                    >
                      Export All Settings
                    </Button>
                  </Box>
                </Paper>
              </Grid>
            </Grid>
          </TabPanel>
        </CardContent>

        {/* Action Buttons */}
        <Box sx={{ 
          p: 3, 
          background: blueCarbon.alpha.oceanBlue[5],
          borderTop: `1px solid ${blueCarbon.alpha.oceanBlue[20]}`,
          display: 'flex',
          justifyContent: 'flex-end',
          gap: 2
        }}>
          <Button
            variant="outlined"
            startIcon={<Cancel />}
            onClick={() => window.history.back()}
          >
            Cancel
          </Button>
          <Button
            variant="contained"
            startIcon={<Save />}
            onClick={handleSaveSettings}
            sx={{
              background: blueCarbon.gradients.oceanDepth,
              '&:hover': {
                background: blueCarbon.gradients.shallowWater
              }
            }}
          >
            Save All Settings
          </Button>
        </Box>
      </Card>
    </Box>
  );
};

export default CompanySettings;
