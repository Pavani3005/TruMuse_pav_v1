import React, { useState } from 'react';
import './Dashboard.css';
import { signOut } from 'firebase/auth';
import { auth } from '../firebase';
import { useNavigate } from 'react-router-dom';

const Dashboard = ({ user }) => {
  const [activeTab, setActiveTab] = useState('overview');
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const navigate = useNavigate();

  const menuItems = [
    { id: 'overview', label: 'Overview', icon: '📊' },
    { id: 'analytics', label: 'Analytics', icon: '📈' },
    { id: 'projects', label: 'Projects', icon: '📁' },
    { id: 'tasks', label: 'Tasks', icon: '✅' },
    { id: 'team', label: 'Team', icon: '👥' },
    { id: 'settings', label: 'Settings', icon: '⚙' }
  ];

  const stats = [
    { title: 'Total Revenue', value: '$54,239', change: '+12.5%', positive: true },
    { title: 'Active Users', value: '2,847', change: '+8.2%', positive: true },
    { title: 'Conversion Rate', value: '3.24%', change: '-2.1%', positive: false },
    { title: 'Growth Rate', value: '24.8%', change: '+5.4%', positive: true }
  ];

  const handleLogout = async () => {
    try {
      await signOut(auth);
      navigate('/login');
    } catch (error) {
      alert('Failed to logout. Please try again.');
    }
  };

  const renderContent = () => {
    switch (activeTab) {
      case 'overview':
        return (
          <div className="overview-content">
            <div className="stats-grid">
              {stats.map((stat, index) => (
                <div key={index} className="stat-card">
                  <div className="stat-header">
                    <h3>{stat.title}</h3>
                    <span className={`stat-change ${stat.positive ? 'positive' : 'negative'}`}>
                      {stat.change}
                    </span>
                  </div>
                  <div className="stat-value">{stat.value}</div>
                </div>
              ))}
            </div>
            <div className="charts-section">
              <div className="chart-card large">
                <h3>Revenue Overview</h3>
                <div className="chart-placeholder">
                  <div className="chart-bars">
                    <div className="bar" style={{height: '60%'}}></div>
                    <div className="bar" style={{height: '80%'}}></div>
                    <div className="bar" style={{height: '45%'}}></div>
                    <div className="bar" style={{height: '90%'}}></div>
                    <div className="bar" style={{height: '70%'}}></div>
                    <div className="bar" style={{height: '85%'}}></div>
                  </div>
                </div>
              </div>
              <div className="chart-card">
                <h3>User Activity</h3>
                <div className="activity-list">
                  <div className="activity-item">
                    <div className="activity-dot"></div>
                    <div>
                      <p>New user registered</p>
                      <span>2 minutes ago</span>
                    </div>
                  </div>
                  <div className="activity-item">
                    <div className="activity-dot"></div>
                    <div>
                      <p>Order completed</p>
                      <span>5 minutes ago</span>
                    </div>
                  </div>
                  <div className="activity-item">
                    <div className="activity-dot"></div>
                    <div>
                      <p>Payment received</p>
                      <span>12 minutes ago</span>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        );
      default:
        return (
          <div className="tab-content">
            <h2>{menuItems.find(item => item.id === activeTab)?.label}</h2>
            <p>This is the {activeTab} section. Content for this section would be implemented here.</p>
          </div>
        );
    }
  };

  return (
    <div className="dashboard-container">
      <div className={`sidebar ${sidebarOpen ? 'open' : ''}`}>
        <div className="sidebar-header">
          <h2>Dashboard</h2>
          <button 
            className="sidebar-toggle"
            onClick={() => setSidebarOpen(!sidebarOpen)}
          >
            ☰
          </button>
        </div>
        <nav className="sidebar-nav">
          {menuItems.map(item => (
            <button
              key={item.id}
              className={`nav-item ${activeTab === item.id ? 'active' : ''}`}
              onClick={() => {
                setActiveTab(item.id);
                setSidebarOpen(false);
              }}
            >
              <span className="nav-icon">{item.icon}</span>
              <span className="nav-label">{item.label}</span>
            </button>
          ))}
        </nav>
        <div className="sidebar-footer">
          <button className="logout-button" onClick={handleLogout}>
            <span>🚪</span>
            Logout
          </button>
        </div>
      </div>
      <div className="main-content">
        <header className="dashboard-header">
          <div className="header-left">
            <button 
              className="mobile-menu-button"
              onClick={() => setSidebarOpen(!sidebarOpen)}
            >
              ☰
            </button>
            <h1>Welcome back, {user?.name || 'User'}!</h1>
          </div>
          <div className="header-right">
            <div className="user-menu">
              <div className="user-avatar">
                {(user?.name || 'U').charAt(0).toUpperCase()}
              </div>
              <span>{user?.email || 'user@example.com'}</span>
            </div>
          </div>
        </header>
        <main className="dashboard-main">
          {renderContent()}
        </main>
      </div>
      {sidebarOpen && <div className="sidebar-overlay" onClick={() => setSidebarOpen(false)}></div>}
    </div>
  );
};

export default Dashboard; 