import React from 'react';
import { Routes, Route } from 'react-router-dom';
import {
  Dashboard,
  Business,
  CloudUpload,
  Map,
  Store,
  TrendingUp,
  AccountBalance
} from '@mui/icons-material';
import Layout from '../components/Layout';
import DashboardPage from './Dashboard';
import ProjectManagement from './ProjectManagement';
import MRVUpload from './MRVUpload';
import Marketplace from './Marketplace';
import GISMapping from './GISMapping';
import CreditTrading from './CreditTrading';
import GovernmentSchemes from './GovernmentSchemes';
import CompanySettings from './Settings';
import FloatingChatbot from '../../components/FloatingChatbot';

const CompanyPanel = ({ darkMode, setDarkMode }) => {
  const menuItems = [
    { text: 'Dashboard', icon: <Dashboard />, path: '/company/dashboard' },
    { text: 'Project Management', icon: <Business />, path: '/company/projects' },
    { text: 'MRV Upload', icon: <CloudUpload />, path: '/company/mrv-upload' },
    { text: 'GIS Mapping', icon: <Map />, path: '/company/gis-mapping' },
    { text: 'Marketplace', icon: <Store />, path: '/company/marketplace' },
    { text: 'Credit Trading', icon: <TrendingUp />, path: '/company/trading' },
    { text: 'Government Schemes', icon: <AccountBalance />, path: '/company/schemes' },
  ];

  return (
    <>
      <Layout 
        menuItems={menuItems} 
        panelType="company"
        darkMode={darkMode}
        setDarkMode={setDarkMode}
      >
        <Routes>
          <Route path="/" element={<DashboardPage />} />
          <Route path="/dashboard" element={<DashboardPage />} />
          <Route path="/projects" element={<ProjectManagement />} />
          <Route path="/mrv-upload" element={<MRVUpload />} />
          <Route path="/gis-mapping" element={<GISMapping />} />
          <Route path="/marketplace" element={<Marketplace />} />
          <Route path="/trading" element={<CreditTrading />} />
          <Route path="/schemes" element={<GovernmentSchemes />} />
          <Route path="/settings" element={<CompanySettings />} />
        </Routes>
      </Layout>
      
      {/* Floating AI Chatbot - Available on all Company Panel pages */}
      <FloatingChatbot />
    </>
  );
};

export default CompanyPanel;