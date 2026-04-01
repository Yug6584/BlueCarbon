const express = require('express');
const cors = require('cors');
const bodyParser = require('body-parser');
const rateLimit = require('express-rate-limit');
const slowDown = require('express-slow-down');
const helmet = require('helmet');
require('dotenv').config();

// Initialize database
require('./database/init');
// Initialize audit database
require('./database/init-audit');
// Initialize monitoring database
require('./database/init-monitoring');
// Initialize backup database
require('./database/init-backup');

const app = express();
const PORT = process.env.PORT || 8000;

// Security Middleware
app.use(helmet({
  contentSecurityPolicy: {
    directives: {
      defaultSrc: ["'self'"],
      styleSrc: ["'self'", "'unsafe-inline'", "https://fonts.googleapis.com"],
      scriptSrc: ["'self'", "'unsafe-inline'"],
      imgSrc: ["'self'", "data:", "https:"],
      fontSrc: ["'self'", "https://fonts.gstatic.com"],
      connectSrc: ["'self'", "http://localhost:8000", "https://localhost:8000"],
    },
  },
  hsts: {
    maxAge: 31536000,
    includeSubDomains: true,
    preload: true
  }
}));

// General rate limiting (increased for development)
const generalLimiter = rateLimit({
  windowMs: 15 * 60 * 1000, // 15 minutes
  max: 1000, // increased limit for development
  message: {
    success: false,
    message: 'Too many requests from this IP, please try again later.'
  },
  standardHeaders: true,
  legacyHeaders: false,
});

// Strict rate limiting for authentication endpoints (increased for development)
const authLimiter = rateLimit({
  windowMs: 15 * 60 * 1000, // 15 minutes
  max: 50, // increased limit for development
  skipSuccessfulRequests: true,
  message: {
    success: false,
    message: 'Too many login attempts, please try again in 15 minutes.'
  },
  standardHeaders: true,
  legacyHeaders: false,
});

// Speed limiter for repeated requests
const speedLimiter = slowDown({
  windowMs: 15 * 60 * 1000, // 15 minutes
  delayAfter: 50, // allow 50 requests per 15 minutes, then...
  delayMs: 500 // begin adding 500ms of delay per request above 50
});

// Apply rate limiting
app.use('/api/', generalLimiter);
app.use('/api/', speedLimiter);
app.use('/api/auth/', authLimiter);

// CORS and body parsing middleware
app.use(cors({
  origin: [
    'http://localhost:3001', 
    'http://localhost:3000', 
    'http://localhost:3002',
    'http://127.0.0.1:3001',
    'http://127.0.0.1:3002',
    'https://localhost:3001'
  ],
  credentials: true,
  methods: ['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS'],
  allowedHeaders: ['Content-Type', 'Authorization', 'Accept']
}));
app.use(bodyParser.json({ limit: '10mb' }));
app.use(bodyParser.urlencoded({ extended: true, limit: '10mb' }));

// Routes
app.use('/api/auth', require('./routes/auth'));
app.use('/api/users', require('./routes/users'));
app.use('/api/stats', require('./routes/stats'));
app.use('/api/system', require('./routes/system'));
app.use('/api/security', require('./routes/security'));
app.use('/api/admin-actions', require('./routes/admin-actions'));
app.use('/api/system-settings', require('./routes/system-settings'));
app.use('/api/audit', require('./routes/audit'));
app.use('/api/monitoring', require('./routes/monitoring'));
app.use('/api/backup', require('./routes/backup'));
app.use('/api/company', require('./routes/company-files'));
app.use('/api/admin/company', require('./routes/admin-company'));
app.use('/api/audit/security-events', require('./routes/security-events'));
app.use('/api/company-dashboard', require('./routes/company-dashboard'));
app.use('/api/trading', require('./routes/trading'));
app.use('/api/password', require('./routes/password-reset'));
app.use('/api/policies', require('./routes/policy-management'));
app.use('/api/compliance', require('./routes/compliance'));
app.use('/api/projects', require('./routes/company-dashboard')); // Projects route uses company-dashboard


// Health check endpoint
app.get('/api/health', (req, res) => {
  res.json({
    success: true,
    message: 'BlueCarbon Backend API is running',
    timestamp: new Date().toISOString()
  });
});

// Database info endpoint
app.get('/api/database/info', (req, res) => {
  const db = require('./database/init');
  
  db.all('SELECT id, email, panel, name, organization, isActive, createdAt, updatedAt, lastLogin FROM users ORDER BY createdAt DESC', (err, users) => {
    if (err) {
      console.error('Database error:', err.message);
      return res.status(500).json({ 
        success: false, 
        message: 'Database error' 
      });
    }

    res.json({
      success: true,
      message: 'User database information',
      tableStructure: {
        tableName: 'users',
        columns: [
          'id (Primary Key)',
          'email (Unique)',
          'password (Encrypted)',
          'panel (admin/company/government)',
          'name',
          'organization',
          'isActive',
          'createdAt',
          'updatedAt',
          'lastLogin'
        ]
      },
      totalUsers: users.length,
      users: users.map(user => ({
        id: user.id,
        email: user.email,
        panel: user.panel,
        name: user.name,
        organization: user.organization,
        isActive: user.isActive,
        createdAt: user.createdAt,
        updatedAt: user.updatedAt,
        lastLogin: user.lastLogin
      }))
    });
  });
});

// Error handling middleware
app.use((err, req, res, next) => {
  console.error('Error:', err.stack);
  res.status(500).json({
    success: false,
    message: 'Something went wrong!'
  });
});

// 404 handler
app.use('*', (req, res) => {
  res.status(404).json({
    success: false,
    message: 'API endpoint not found'
  });
});

app.listen(PORT, () => {
  console.log(`🚀 BlueCarbon Backend Server running on port ${PORT}`);
  console.log(`📊 API Health Check: http://localhost:${PORT}/api/health`);
  console.log(`🗄️ Database Info: http://localhost:${PORT}/api/database/info`);
  console.log(`🔐 Default Admin Login: admin@bluecarbon.com / admin123`);
});

module.exports = app;