const express = require('express');
const router = express.Router();
const fs = require('fs').promises;
const path = require('path');

// Policy data file path
const POLICIES_FILE = path.join(__dirname, '../data/policies.json');

// Ensure data directory exists
const ensureDataDirectory = async () => {
  const dataDir = path.dirname(POLICIES_FILE);
  try {
    await fs.access(dataDir);
  } catch (error) {
    await fs.mkdir(dataDir, { recursive: true });
  }
};

// Load policies from file
const loadPolicies = async () => {
  try {
    await ensureDataDirectory();
    const data = await fs.readFile(POLICIES_FILE, 'utf8');
    return JSON.parse(data);
  } catch (error) {
    // Return default policies if file doesn't exist
    return getDefaultPolicies();
  }
};

// Save policies to file
const savePolicies = async (policies) => {
  await ensureDataDirectory();
  await fs.writeFile(POLICIES_FILE, JSON.stringify(policies, null, 2));
};

// Default Indian Blue Carbon Policies
const getDefaultPolicies = () => [
  {
    id: 'IND-BC-001',
    name: 'Coastal Regulation Zone (CRZ) Notification 2019',
    description: 'Comprehensive regulations for coastal zone management and protection of marine ecosystems',
    status: 'active',
    lastUpdated: '2019-01-18',
    version: '2019',
    ministry: 'Ministry of Environment, Forest and Climate Change',
    type: 'Regulation',
    scope: 'National',
    applicableStates: 'All coastal states and UTs',
    content: `The Coastal Regulation Zone (CRZ) Notification 2019 is a comprehensive framework for managing India's coastal areas and protecting marine ecosystems.

Key Provisions:
• CRZ-I: Ecologically Sensitive Areas including mangroves, coral reefs, sand dunes, and biologically active areas
• CRZ-II: Areas that have been developed up to or close to the shoreline
• CRZ-III: Areas that are relatively undisturbed and do not belong to CRZ-I or CRZ-II
• CRZ-IV: Water area from the low tide line to territorial waters

Blue Carbon Relevance:
• Strict protection of mangrove areas under CRZ-I
• Prohibition of activities that may damage marine ecosystems
• Mandatory Environmental Impact Assessment for coastal projects
• Restoration and conservation requirements for degraded coastal areas
• Buffer zones around ecologically sensitive areas`,
    legalBasis: 'Environment (Protection) Act, 1986',
    enforcementAgency: 'State Coastal Zone Management Authority (SCZMA)',
    penalties: 'Fine up to ₹1 lakh and/or imprisonment up to 5 years',
    relatedPolicies: ['IND-BC-002', 'IND-BC-003', 'IND-BC-007'],
    createdAt: '2019-01-18T00:00:00.000Z',
    updatedAt: '2019-01-18T00:00:00.000Z'
  },
  {
    id: 'IND-BC-002',
    name: 'National Action Plan on Climate Change (NAPCC) 2008',
    description: 'India\'s comprehensive strategy to address climate change challenges including coastal ecosystem protection',
    status: 'active',
    lastUpdated: '2008-06-30',
    version: '2008',
    ministry: 'Prime Minister\'s Office',
    type: 'Policy Framework',
    scope: 'National',
    applicableStates: 'All states and UTs',
    content: `The National Action Plan on Climate Change (NAPCC) outlines India's strategy to address climate change while maintaining economic growth.

Eight National Missions:
1. National Solar Mission
2. National Mission for Enhanced Energy Efficiency
3. National Mission on Sustainable Habitat
4. National Water Mission
5. National Mission for Sustaining the Himalayan Ecosystem
6. National Mission for a Green India
7. National Mission for Sustainable Agriculture
8. National Mission on Strategic Knowledge for Climate Change

Blue Carbon Components:
• Green India Mission includes coastal forest restoration
• Sustainable Habitat Mission covers coastal urban planning
• Strategic Knowledge Mission supports blue carbon research
• Water Mission addresses coastal water management`,
    legalBasis: 'Cabinet decision and subsequent notifications',
    enforcementAgency: 'Ministry of Environment, Forest and Climate Change',
    penalties: 'Varies by specific mission and implementing agency',
    relatedPolicies: ['IND-BC-001', 'IND-BC-004', 'IND-BC-008'],
    createdAt: '2008-06-30T00:00:00.000Z',
    updatedAt: '2008-06-30T00:00:00.000Z'
  }
];

// GET /api/policies - Get all policies
router.get('/', async (req, res) => {
  try {
    const policies = await loadPolicies();
    res.json({
      success: true,
      data: policies,
      count: policies.length
    });
  } catch (error) {
    console.error('Error fetching policies:', error);
    res.status(500).json({
      success: false,
      message: 'Failed to fetch policies',
      error: error.message
    });
  }
});

// GET /api/policies/:id - Get specific policy
router.get('/:id', async (req, res) => {
  try {
    const policies = await loadPolicies();
    const policy = policies.find(p => p.id === req.params.id);
    
    if (!policy) {
      return res.status(404).json({
        success: false,
        message: 'Policy not found'
      });
    }
    
    res.json({
      success: true,
      data: policy
    });
  } catch (error) {
    console.error('Error fetching policy:', error);
    res.status(500).json({
      success: false,
      message: 'Failed to fetch policy',
      error: error.message
    });
  }
});

// POST /api/policies - Create new policy
router.post('/', async (req, res) => {
  try {
    const { name, description, status, version, ministry, type, scope, applicableStates, content, legalBasis, enforcementAgency, penalties } = req.body;
    
    // Validation
    if (!name || !description) {
      return res.status(400).json({
        success: false,
        message: 'Name and description are required'
      });
    }
    
    const policies = await loadPolicies();
    
    // Generate new ID
    const maxId = policies.reduce((max, policy) => {
      const num = parseInt(policy.id.split('-').pop());
      return num > max ? num : max;
    }, 0);
    
    const newPolicy = {
      id: `IND-BC-${String(maxId + 1).padStart(3, '0')}`,
      name,
      description,
      status: status || 'draft',
      version: version || '1.0',
      ministry: ministry || '',
      type: type || 'Policy',
      scope: scope || 'National',
      applicableStates: applicableStates || '',
      content: content || '',
      legalBasis: legalBasis || '',
      enforcementAgency: enforcementAgency || '',
      penalties: penalties || '',
      relatedPolicies: [],
      lastUpdated: new Date().toISOString().split('T')[0],
      createdAt: new Date().toISOString(),
      updatedAt: new Date().toISOString()
    };
    
    policies.push(newPolicy);
    await savePolicies(policies);
    
    res.status(201).json({
      success: true,
      message: 'Policy created successfully',
      data: newPolicy
    });
  } catch (error) {
    console.error('Error creating policy:', error);
    res.status(500).json({
      success: false,
      message: 'Failed to create policy',
      error: error.message
    });
  }
});

// PUT /api/policies/:id - Update policy
router.put('/:id', async (req, res) => {
  try {
    const policies = await loadPolicies();
    const policyIndex = policies.findIndex(p => p.id === req.params.id);
    
    if (policyIndex === -1) {
      return res.status(404).json({
        success: false,
        message: 'Policy not found'
      });
    }
    
    const { name, description, status, version, ministry, type, scope, applicableStates, content, legalBasis, enforcementAgency, penalties } = req.body;
    
    // Update policy
    policies[policyIndex] = {
      ...policies[policyIndex],
      name: name || policies[policyIndex].name,
      description: description || policies[policyIndex].description,
      status: status || policies[policyIndex].status,
      version: version || policies[policyIndex].version,
      ministry: ministry || policies[policyIndex].ministry,
      type: type || policies[policyIndex].type,
      scope: scope || policies[policyIndex].scope,
      applicableStates: applicableStates || policies[policyIndex].applicableStates,
      content: content || policies[policyIndex].content,
      legalBasis: legalBasis || policies[policyIndex].legalBasis,
      enforcementAgency: enforcementAgency || policies[policyIndex].enforcementAgency,
      penalties: penalties || policies[policyIndex].penalties,
      lastUpdated: new Date().toISOString().split('T')[0],
      updatedAt: new Date().toISOString()
    };
    
    await savePolicies(policies);
    
    res.json({
      success: true,
      message: 'Policy updated successfully',
      data: policies[policyIndex]
    });
  } catch (error) {
    console.error('Error updating policy:', error);
    res.status(500).json({
      success: false,
      message: 'Failed to update policy',
      error: error.message
    });
  }
});

// DELETE /api/policies/:id - Delete policy
router.delete('/:id', async (req, res) => {
  try {
    const policies = await loadPolicies();
    const policyIndex = policies.findIndex(p => p.id === req.params.id);
    
    if (policyIndex === -1) {
      return res.status(404).json({
        success: false,
        message: 'Policy not found'
      });
    }
    
    const deletedPolicy = policies.splice(policyIndex, 1)[0];
    await savePolicies(policies);
    
    res.json({
      success: true,
      message: 'Policy deleted successfully',
      data: deletedPolicy
    });
  } catch (error) {
    console.error('Error deleting policy:', error);
    res.status(500).json({
      success: false,
      message: 'Failed to delete policy',
      error: error.message
    });
  }
});

// GET /api/policies/search/:query - Search policies
router.get('/search/:query', async (req, res) => {
  try {
    const policies = await loadPolicies();
    const query = req.params.query.toLowerCase();
    
    const filteredPolicies = policies.filter(policy => 
      policy.name.toLowerCase().includes(query) ||
      policy.description.toLowerCase().includes(query) ||
      policy.ministry.toLowerCase().includes(query) ||
      policy.type.toLowerCase().includes(query) ||
      policy.content.toLowerCase().includes(query)
    );
    
    res.json({
      success: true,
      data: filteredPolicies,
      count: filteredPolicies.length,
      query: req.params.query
    });
  } catch (error) {
    console.error('Error searching policies:', error);
    res.status(500).json({
      success: false,
      message: 'Failed to search policies',
      error: error.message
    });
  }
});

// GET /api/policies/filter/status/:status - Filter by status
router.get('/filter/status/:status', async (req, res) => {
  try {
    const policies = await loadPolicies();
    const filteredPolicies = policies.filter(policy => 
      policy.status.toLowerCase() === req.params.status.toLowerCase()
    );
    
    res.json({
      success: true,
      data: filteredPolicies,
      count: filteredPolicies.length,
      filter: req.params.status
    });
  } catch (error) {
    console.error('Error filtering policies:', error);
    res.status(500).json({
      success: false,
      message: 'Failed to filter policies',
      error: error.message
    });
  }
});

// Export policies
router.get('/export/:format', async (req, res) => {
  try {
    const policies = await loadPolicies();
    const format = req.params.format.toLowerCase();
    
    if (format === 'json') {
      res.setHeader('Content-Type', 'application/json');
      res.setHeader('Content-Disposition', 'attachment; filename="indian-blue-carbon-policies.json"');
      res.json(policies);
    } else if (format === 'csv') {
      // Convert to CSV
      const csvHeader = 'ID,Name,Description,Status,Ministry,Type,Scope,Last Updated,Version\n';
      const csvRows = policies.map(policy => 
        `"${policy.id}","${policy.name}","${policy.description.replace(/"/g, '""')}","${policy.status}","${policy.ministry}","${policy.type}","${policy.scope}","${policy.lastUpdated}","${policy.version}"`
      ).join('\n');
      
      res.setHeader('Content-Type', 'text/csv');
      res.setHeader('Content-Disposition', 'attachment; filename="indian-blue-carbon-policies.csv"');
      res.send(csvHeader + csvRows);
    } else if (format === 'pdf') {
      // For PDF, we'll return a structured text format
      const pdfContent = policies.map(policy => 
        `Policy ID: ${policy.id}\nName: ${policy.name}\nMinistry: ${policy.ministry}\nStatus: ${policy.status}\nDescription: ${policy.description}\n\n---\n\n`
      ).join('');
      
      res.setHeader('Content-Type', 'text/plain');
      res.setHeader('Content-Disposition', 'attachment; filename="indian-blue-carbon-policies.txt"');
      res.send(`INDIAN BLUE CARBON POLICIES REPORT\nGenerated on: ${new Date().toISOString()}\n\n${pdfContent}`);
    } else {
      res.status(400).json({
        success: false,
        message: 'Unsupported export format. Use json, csv, or pdf.'
      });
    }
  } catch (error) {
    console.error('Error exporting policies:', error);
    res.status(500).json({
      success: false,
      message: 'Error exporting policies'
    });
  }
});

// Refresh policies (reload from default data)
router.post('/refresh', async (req, res) => {
  try {
    const defaultPolicies = getDefaultPolicies();
    await savePolicies(defaultPolicies);
    
    res.json({
      success: true,
      message: 'Policies refreshed successfully',
      count: defaultPolicies.length
    });
  } catch (error) {
    console.error('Error refreshing policies:', error);
    res.status(500).json({
      success: false,
      message: 'Error refreshing policies'
    });
  }
});

// Get policy statistics
router.get('/stats', async (req, res) => {
  try {
    const policies = await loadPolicies();
    
    const stats = {
      total: policies.length,
      active: policies.filter(p => p.status === 'active').length,
      draft: policies.filter(p => p.status === 'draft').length,
      inactive: policies.filter(p => p.status === 'inactive').length,
      byMinistry: {},
      byType: {},
      byScope: {},
      recentUpdates: policies
        .sort((a, b) => new Date(b.lastUpdated) - new Date(a.lastUpdated))
        .slice(0, 5)
        .map(p => ({ id: p.id, name: p.name, lastUpdated: p.lastUpdated }))
    };
    
    // Group by ministry
    policies.forEach(policy => {
      stats.byMinistry[policy.ministry] = (stats.byMinistry[policy.ministry] || 0) + 1;
    });
    
    // Group by type
    policies.forEach(policy => {
      stats.byType[policy.type] = (stats.byType[policy.type] || 0) + 1;
    });
    
    // Group by scope
    policies.forEach(policy => {
      stats.byScope[policy.scope] = (stats.byScope[policy.scope] || 0) + 1;
    });
    
    res.json({
      success: true,
      stats
    });
  } catch (error) {
    console.error('Error getting policy stats:', error);
    res.status(500).json({
      success: false,
      message: 'Error getting policy statistics'
    });
  }
});

module.exports = router;