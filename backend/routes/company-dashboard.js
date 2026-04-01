const express = require('express');
const { authenticateToken } = require('../middleware/auth');
const companyDatabaseManager = require('../services/companyDatabaseManager');
const router = express.Router();

// Update company profile
router.put('/profile', authenticateToken, (req, res) => {
  if (req.user.panel !== 'company') {
    return res.status(403).json({
      success: false,
      message: 'Only company users can update profile'
    });
  }

  const db = companyDatabaseManager.getCompanyDatabase(req.user.userId);
  
  if (!db) {
    return res.status(500).json({
      success: false,
      message: 'Company database not found'
    });
  }

  const { companyName, industry, phone, address, website, description, logo } = req.body;

  // Check if profile exists
  db.get('SELECT * FROM company_profile WHERE user_id = ?', [req.user.userId], (err, profile) => {
    if (err) {
      db.close();
      return res.status(500).json({
        success: false,
        message: 'Database error'
      });
    }

    if (profile) {
      // Update existing profile
      db.run(
        `UPDATE company_profile 
         SET company_name = ?, industry = ?, phone = ?, address = ?, website = ?, description = ?, logo_path = ?, updated_at = CURRENT_TIMESTAMP 
         WHERE user_id = ?`,
        [companyName, industry, phone, address, website, description, logo, req.user.userId],
        function(err) {
          db.close();
          
          if (err) {
            return res.status(500).json({
              success: false,
              message: 'Error updating profile'
            });
          }

          res.json({
            success: true,
            message: 'Profile updated successfully'
          });
        }
      );
    } else {
      // Create new profile
      db.run(
        `INSERT INTO company_profile (user_id, company_name, industry, phone, address, website, description, logo_path) 
         VALUES (?, ?, ?, ?, ?, ?, ?, ?)`,
        [req.user.userId, companyName, industry, phone, address, website, description, logo],
        function(err) {
          db.close();
          
          if (err) {
            return res.status(500).json({
              success: false,
              message: 'Error creating profile'
            });
          }

          res.json({
            success: true,
            message: 'Profile created successfully'
          });
        }
      );
    }
  });
});

// Get company dashboard data
router.get('/dashboard', authenticateToken, (req, res) => {
  // Only company users can access their dashboard data
  if (req.user.panel !== 'company') {
    return res.status(403).json({
      success: false,
      message: 'Only company users can access dashboard data'
    });
  }

  const db = companyDatabaseManager.getCompanyDatabase(req.user.userId);
  
  if (!db) {
    return res.status(500).json({
      success: false,
      message: 'Company database not found. Please contact administrator.'
    });
  }

  // Get comprehensive dashboard data
  const queries = {
    profile: 'SELECT * FROM company_profile WHERE user_id = ?',
    projects: 'SELECT * FROM projects ORDER BY created_at DESC',
    files: 'SELECT COUNT(*) as count FROM files',
    images: 'SELECT COUNT(*) as count FROM images',
    dataEntries: 'SELECT COUNT(*) as count FROM company_data',
    recentFiles: 'SELECT * FROM files ORDER BY created_at DESC LIMIT 5',
    recentImages: 'SELECT * FROM images ORDER BY created_at DESC LIMIT 5',
    projectsByStatus: `
      SELECT status, COUNT(*) as count 
      FROM projects 
      GROUP BY status
    `,
    recentActivity: `
      SELECT action_type, action_description, created_at 
      FROM activity_logs 
      ORDER BY created_at DESC 
      LIMIT 10
    `
  };

  const results = {};
  let completedQueries = 0;
  const totalQueries = Object.keys(queries).length;

  Object.entries(queries).forEach(([key, query]) => {
    if (key === 'profile' || key === 'recentActivity') {
      db.get(query, key === 'profile' ? [req.user.userId] : [], (err, row) => {
        if (err) {
          console.error(`Error in ${key} query:`, err);
          results[key] = null;
        } else {
          results[key] = row;
        }
        
        completedQueries++;
        if (completedQueries === totalQueries) {
          sendDashboardResponse();
        }
      });
    } else {
      db.all(query, (err, rows) => {
        if (err) {
          console.error(`Error in ${key} query:`, err);
          results[key] = [];
        } else {
          results[key] = rows;
        }
        
        completedQueries++;
        if (completedQueries === totalQueries) {
          sendDashboardResponse();
        }
      });
    }
  });

  const sendDashboardResponse = () => {
    db.close();
    
    // Calculate statistics
    const totalProjects = results.projects.length;
    const activeProjects = results.projects.filter(p => p.status === 'active').length;
    const completedProjects = results.projects.filter(p => p.status === 'completed').length;
    const totalCredits = results.projects.reduce((sum, p) => sum + (p.budget || 0), 0);
    
    // Calculate project status distribution
    const statusDistribution = results.projectsByStatus.reduce((acc, item) => {
      acc[item.status] = item.count;
      return acc;
    }, {});

    res.json({
      success: true,
      data: {
        profile: results.profile,
        statistics: {
          totalProjects,
          activeProjects,
          completedProjects,
          totalFiles: results.files[0]?.count || 0,
          totalImages: results.images[0]?.count || 0,
          totalDataEntries: results.dataEntries[0]?.count || 0,
          totalCredits,
          statusDistribution
        },
        projects: results.projects,
        recentFiles: results.recentFiles,
        recentImages: results.recentImages,
        recentActivity: results.recentActivity || []
      }
    });
  };
});

// Get company projects
router.get('/projects', authenticateToken, (req, res) => {
  if (req.user.panel !== 'company') {
    return res.status(403).json({
      success: false,
      message: 'Only company users can access their projects'
    });
  }

  const db = companyDatabaseManager.getCompanyDatabase(req.user.userId);
  
  if (!db) {
    return res.status(500).json({
      success: false,
      message: 'Company database not found'
    });
  }

  db.all('SELECT * FROM projects ORDER BY created_at DESC', (err, projects) => {
    db.close();
    
    if (err) {
      console.error('Error fetching projects:', err);
      return res.status(500).json({
        success: false,
        message: 'Error fetching projects'
      });
    }

    res.json({
      success: true,
      projects: projects
    });
  });
});

// Get project by unique project ID
router.get('/projects/by-id/:projectId', authenticateToken, (req, res) => {
  if (req.user.panel !== 'company') {
    return res.status(403).json({
      success: false,
      message: 'Only company users can access their projects'
    });
  }

  const { projectId } = req.params;

  const db = companyDatabaseManager.getCompanyDatabase(req.user.userId);
  
  if (!db) {
    return res.status(500).json({
      success: false,
      message: 'Company database not found'
    });
  }

  db.get('SELECT * FROM projects WHERE project_id = ?', [projectId], (err, project) => {
    db.close();
    
    if (err) {
      console.error('Error fetching project:', err);
      return res.status(500).json({
        success: false,
        message: 'Error fetching project'
      });
    }

    if (!project) {
      return res.status(404).json({
        success: false,
        message: 'Project not found'
      });
    }

    res.json({
      success: true,
      project: project
    });
  });
});

// Submit new project (alias for create)
router.post('/submit', authenticateToken, (req, res) => {
  if (req.user.panel !== 'company') {
    return res.status(403).json({
      success: false,
      message: 'Only company users can submit projects'
    });
  }

  const { 
    project_name, 
    description, 
    project_type, 
    area_hectares, 
    location, 
    status, 
    start_date, 
    end_date, 
    budget, 
    expected_credits,
    coordinates,
    additional_data
  } = req.body;

  if (!project_name || !project_type || !area_hectares || !start_date || !end_date) {
    return res.status(400).json({
      success: false,
      message: 'Project name, type, area, start date, and end date are required'
    });
  }

  const db = companyDatabaseManager.getCompanyDatabase(req.user.userId);
  
  if (!db) {
    return res.status(500).json({
      success: false,
      message: 'Company database not found'
    });
  }

  // Generate unique project ID
  const uniqueProjectId = companyDatabaseManager.generateProjectId();

  db.run(
    `INSERT INTO projects (project_id, project_name, description, project_type, area_hectares, location, status, start_date, end_date, budget, expected_credits, created_by) 
     VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)`,
    [uniqueProjectId, project_name, description, project_type, area_hectares, location || JSON.stringify(coordinates), status || 'submitted', start_date, end_date, budget, expected_credits || 0, req.user.userId],
    function(err) {
      db.close();
      
      if (err) {
        console.error('Error submitting project:', err);
        return res.status(500).json({
          success: false,
          message: 'Error submitting project'
        });
      }

      res.json({
        success: true,
        message: 'Project submitted successfully',
        projectId: this.lastID,
        uniqueProjectId: uniqueProjectId
      });
    }
  );
});

// Create new project
router.post('/projects', authenticateToken, (req, res) => {
  if (req.user.panel !== 'company') {
    return res.status(403).json({
      success: false,
      message: 'Only company users can create projects'
    });
  }

  const { 
    project_name, 
    description, 
    project_type, 
    area_hectares, 
    location, 
    status, 
    start_date, 
    end_date, 
    budget, 
    expected_credits 
  } = req.body;

  if (!project_name || !project_type || !area_hectares || !start_date || !end_date) {
    return res.status(400).json({
      success: false,
      message: 'Project name, type, area, start date, and end date are required'
    });
  }

  const db = companyDatabaseManager.getCompanyDatabase(req.user.userId);
  
  if (!db) {
    return res.status(500).json({
      success: false,
      message: 'Company database not found'
    });
  }

  // Generate unique project ID
  const uniqueProjectId = companyDatabaseManager.generateProjectId();

  db.run(
    `INSERT INTO projects (project_id, project_name, description, project_type, area_hectares, location, status, start_date, end_date, budget, expected_credits, created_by) 
     VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)`,
    [uniqueProjectId, project_name, description, project_type, area_hectares, location, status || 'planning', start_date, end_date, budget, expected_credits || 0, req.user.userId],
    function(err) {
      db.close();
      
      if (err) {
        console.error('Error creating project:', err);
        return res.status(500).json({
          success: false,
          message: 'Error creating project'
        });
      }

      res.json({
        success: true,
        message: 'Project created successfully',
        projectId: this.lastID,
        uniqueProjectId: uniqueProjectId
      });
    }
  );
});

// Update project
router.put('/projects/:id', authenticateToken, (req, res) => {
  if (req.user.panel !== 'company') {
    return res.status(403).json({
      success: false,
      message: 'Only company users can update their projects'
    });
  }

  const projectId = req.params.id;
  const { 
    project_name, 
    description, 
    project_type, 
    area_hectares, 
    location, 
    status, 
    start_date, 
    end_date, 
    budget, 
    expected_credits 
  } = req.body;

  const db = companyDatabaseManager.getCompanyDatabase(req.user.userId);
  
  if (!db) {
    return res.status(500).json({
      success: false,
      message: 'Company database not found'
    });
  }

  db.run(
    `UPDATE projects 
     SET project_name = ?, description = ?, project_type = ?, area_hectares = ?, 
         location = ?, status = ?, start_date = ?, end_date = ?, budget = ?, 
         expected_credits = ?, updated_at = CURRENT_TIMESTAMP 
     WHERE id = ?`,
    [project_name, description, project_type, area_hectares, location, status, start_date, end_date, budget, expected_credits || 0, projectId],
    function(err) {
      db.close();
      
      if (err) {
        console.error('Error updating project:', err);
        return res.status(500).json({
          success: false,
          message: 'Error updating project'
        });
      }

      if (this.changes === 0) {
        return res.status(404).json({
          success: false,
          message: 'Project not found'
        });
      }

      res.json({
        success: true,
        message: 'Project updated successfully'
      });
    }
  );
});

// Delete project
router.delete('/projects/:id', authenticateToken, (req, res) => {
  if (req.user.panel !== 'company') {
    return res.status(403).json({
      success: false,
      message: 'Only company users can delete their projects'
    });
  }

  const projectId = req.params.id;

  const db = companyDatabaseManager.getCompanyDatabase(req.user.userId);
  
  if (!db) {
    return res.status(500).json({
      success: false,
      message: 'Company database not found'
    });
  }

  db.run('DELETE FROM projects WHERE id = ?', [projectId], function(err) {
    db.close();
    
    if (err) {
      console.error('Error deleting project:', err);
      return res.status(500).json({
        success: false,
        message: 'Error deleting project'
      });
    }

    if (this.changes === 0) {
      return res.status(404).json({
        success: false,
        message: 'Project not found'
      });
    }

    res.json({
      success: true,
      message: 'Project deleted successfully'
    });
  });
});

// Log company activity
router.post('/activity', authenticateToken, (req, res) => {
  if (req.user.panel !== 'company') {
    return res.status(403).json({
      success: false,
      message: 'Only company users can log activities'
    });
  }

  const { action_type, action_description, target_type, target_id } = req.body;

  const db = companyDatabaseManager.getCompanyDatabase(req.user.userId);
  
  if (!db) {
    return res.status(500).json({
      success: false,
      message: 'Company database not found'
    });
  }

  const clientIP = req.ip || req.connection.remoteAddress || 'unknown';
  const userAgent = req.get('User-Agent') || 'unknown';

  db.run(
    `INSERT INTO activity_logs (user_id, action_type, action_description, target_type, target_id, ip_address, user_agent) 
     VALUES (?, ?, ?, ?, ?, ?, ?)`,
    [req.user.userId, action_type, action_description, target_type, target_id, clientIP, userAgent],
    function(err) {
      db.close();
      
      if (err) {
        console.error('Error logging activity:', err);
        return res.status(500).json({
          success: false,
          message: 'Error logging activity'
        });
      }

      res.json({
        success: true,
        message: 'Activity logged successfully',
        activityId: this.lastID
      });
    }
  );
});

// Get company files/uploads
router.get('/files', authenticateToken, (req, res) => {
  if (req.user.panel !== 'company') {
    return res.status(403).json({
      success: false,
      message: 'Only company users can access files'
    });
  }

  const { project_id } = req.query;

  const db = companyDatabaseManager.getCompanyDatabase(req.user.userId);
  
  if (!db) {
    return res.status(500).json({
      success: false,
      message: 'Company database not found'
    });
  }

  let query = 'SELECT f.*, p.project_name FROM files f LEFT JOIN projects p ON f.project_id = p.id';
  let params = [];

  if (project_id) {
    query += ' WHERE f.project_id = ?';
    params.push(project_id);
  }

  query += ' ORDER BY f.created_at DESC';

  db.all(query, params, (err, files) => {
    if (err) {
      console.error('Error fetching files:', err);
      return res.status(500).json({
        success: false,
        message: 'Error fetching files'
      });
    }

    res.json({
      success: true,
      files: files || []
    });
  });
});

// Upload new file
router.post('/files', authenticateToken, (req, res) => {
  if (req.user.panel !== 'company') {
    return res.status(403).json({
      success: false,
      message: 'Only company users can upload files'
    });
  }

  const { filename, file_type, file_size, description, category, project_id } = req.body;

  if (!filename || !project_id) {
    return res.status(400).json({
      success: false,
      message: 'Filename and project ID are required'
    });
  }

  const db = companyDatabaseManager.getCompanyDatabase(req.user.userId);
  
  if (!db) {
    return res.status(500).json({
      success: false,
      message: 'Company database not found'
    });
  }

  db.run(
    `INSERT INTO files (filename, original_name, file_path, file_size, mime_type, category, description, project_id, uploaded_by) 
     VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)`,
    [filename, filename, `/uploads/${filename}`, file_size || 0, file_type || 'application/octet-stream', category || 'general', description, project_id, req.user.userId],
    function(err) {
      if (err) {
        console.error('Error uploading file:', err);
        return res.status(500).json({
          success: false,
          message: 'Error uploading file'
        });
      }

      res.json({
        success: true,
        message: 'File uploaded successfully',
        fileId: this.lastID
      });
    }
  );
});

// Update file status
router.put('/files/:id', authenticateToken, (req, res) => {
  if (req.user.panel !== 'company') {
    return res.status(403).json({
      success: false,
      message: 'Only company users can update files'
    });
  }

  const { status, verification_notes } = req.body;
  const fileId = req.params.id;

  const db = companyDatabaseManager.getCompanyDatabase(req.user.userId);
  
  if (!db) {
    return res.status(500).json({
      success: false,
      message: 'Company database not found'
    });
  }

  db.run(
    `UPDATE files SET description = ?, updated_at = datetime('now') WHERE id = ?`,
    [verification_notes || status, fileId],
    function(err) {
      if (err) {
        console.error('Error updating file:', err);
        return res.status(500).json({
          success: false,
          message: 'Error updating file'
        });
      }

      res.json({
        success: true,
        message: 'File updated successfully'
      });
    }
  );
});

// Delete file
router.delete('/files/:id', authenticateToken, (req, res) => {
  if (req.user.panel !== 'company') {
    return res.status(403).json({
      success: false,
      message: 'Only company users can delete files'
    });
  }

  const fileId = req.params.id;

  const db = companyDatabaseManager.getCompanyDatabase(req.user.userId);
  
  if (!db) {
    return res.status(500).json({
      success: false,
      message: 'Company database not found'
    });
  }

  db.run('DELETE FROM files WHERE id = ?', [fileId], function(err) {
    if (err) {
      console.error('Error deleting file:', err);
      return res.status(500).json({
        success: false,
        message: 'Error deleting file'
      });
    }

    res.json({
      success: true,
      message: 'File deleted successfully'
    });
  });
});

// Get marketplace data
router.get('/marketplace', authenticateToken, (req, res) => {
  if (req.user.panel !== 'company') {
    return res.status(403).json({
      success: false,
      message: 'Only company users can access marketplace data'
    });
  }

  const db = companyDatabaseManager.getCompanyDatabase(req.user.userId);
  
  if (!db) {
    return res.status(500).json({
      success: false,
      message: 'Company database not found'
    });
  }

  // Get marketplace statistics
  const queries = {
    ownedCredits: 'SELECT COUNT(*) as count, SUM(credits) as total FROM carbon_credits WHERE owner_id = ?',
    listedCredits: 'SELECT COUNT(*) as count, SUM(credits) as total FROM carbon_credits WHERE status = "listed"',
    transactions: 'SELECT COUNT(*) as count, SUM(amount) as volume FROM credit_transactions WHERE buyer_id = ? OR seller_id = ?',
    marketListings: `
      SELECT cc.*, p.project_name, cp.company_name as seller_name
      FROM carbon_credits cc
      LEFT JOIN projects p ON cc.project_id = p.id
      LEFT JOIN company_profile cp ON cc.owner_id = cp.user_id
      WHERE cc.status = 'listed'
      ORDER BY cc.created_at DESC
      LIMIT 10
    `,
    myListings: `
      SELECT cc.*, p.project_name
      FROM carbon_credits cc
      LEFT JOIN projects p ON cc.project_id = p.id
      WHERE cc.owner_id = ? AND cc.status = 'listed'
      ORDER BY cc.created_at DESC
    `
  };

  const results = {};
  let completedQueries = 0;
  const totalQueries = Object.keys(queries).length;

  Object.entries(queries).forEach(([key, query]) => {
    const params = key === 'ownedCredits' ? [req.user.userId] :
                  key === 'transactions' ? [req.user.userId, req.user.userId] :
                  key === 'myListings' ? [req.user.userId] : [];

    if (key === 'marketListings' || key === 'myListings') {
      db.all(query, params, (err, rows) => {
        if (err) {
          console.error(`Error in ${key} query:`, err);
          results[key] = [];
        } else {
          results[key] = rows || [];
        }
        
        completedQueries++;
        if (completedQueries === totalQueries) {
          sendMarketplaceResponse();
        }
      });
    } else {
      db.get(query, params, (err, row) => {
        if (err) {
          console.error(`Error in ${key} query:`, err);
          results[key] = { count: 0, total: 0 };
        } else {
          results[key] = row || { count: 0, total: 0 };
        }
        
        completedQueries++;
        if (completedQueries === totalQueries) {
          sendMarketplaceResponse();
        }
      });
    }
  });

  function sendMarketplaceResponse() {
    const marketplaceData = {
      statistics: {
        marketPrice: 27.50, // This would come from external market data in real app
        availableCredits: results.listedCredits.total || 0,
        myPortfolio: results.ownedCredits.total || 0,
        totalVolume: results.transactions.volume || 0,
        myListings: results.myListings.length || 0
      },
      marketListings: results.marketListings || [],
      myListings: results.myListings || [],
      recentTransactions: [] // Would be populated from transactions table
    };

    res.json({
      success: true,
      data: marketplaceData
    });
  }
});

// List carbon credits for sale
router.post('/marketplace/list', authenticateToken, (req, res) => {
  if (req.user.panel !== 'company') {
    return res.status(403).json({
      success: false,
      message: 'Only company users can list credits'
    });
  }

  const { project_id, credits, price_per_credit, description } = req.body;

  if (!project_id || !credits || !price_per_credit) {
    return res.status(400).json({
      success: false,
      message: 'Project ID, credits amount, and price are required'
    });
  }

  const db = companyDatabaseManager.getCompanyDatabase(req.user.userId);
  
  if (!db) {
    return res.status(500).json({
      success: false,
      message: 'Company database not found'
    });
  }

  db.run(
    `INSERT INTO carbon_credits (project_id, owner_id, credits, price_per_credit, description, status, created_at) 
     VALUES (?, ?, ?, ?, ?, 'listed', datetime('now'))`,
    [project_id, req.user.userId, credits, price_per_credit, description],
    function(err) {
      if (err) {
        console.error('Error listing credits:', err);
        return res.status(500).json({
          success: false,
          message: 'Error listing credits'
        });
      }

      res.json({
        success: true,
        message: 'Credits listed successfully',
        creditId: this.lastID
      });
    }
  );
});

// Buy carbon credits
router.post('/marketplace/buy', authenticateToken, (req, res) => {
  if (req.user.panel !== 'company') {
    return res.status(403).json({
      success: false,
      message: 'Only company users can buy credits'
    });
  }

  const { credit_id, quantity } = req.body;

  if (!credit_id || !quantity) {
    return res.status(400).json({
      success: false,
      message: 'Credit ID and quantity are required'
    });
  }

  const db = companyDatabaseManager.getCompanyDatabase(req.user.userId);
  
  if (!db) {
    return res.status(500).json({
      success: false,
      message: 'Company database not found'
    });
  }

  // In a real app, this would handle the transaction logic
  // For now, we'll just record the transaction
  db.run(
    `INSERT INTO credit_transactions (credit_id, buyer_id, seller_id, quantity, amount, status, created_at) 
     VALUES (?, ?, ?, ?, ?, 'completed', datetime('now'))`,
    [credit_id, req.user.userId, 0, quantity, quantity * 27.50], // Using market price
    function(err) {
      if (err) {
        console.error('Error buying credits:', err);
        return res.status(500).json({
          success: false,
          message: 'Error processing purchase'
        });
      }

      res.json({
        success: true,
        message: 'Credits purchased successfully',
        transactionId: this.lastID
      });
    }
  );
});

module.exports = router;