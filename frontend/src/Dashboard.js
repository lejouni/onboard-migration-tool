import React from 'react';

const Dashboard = ({ legacyFiles = [], scanDuration = null }) => {
  // Calculate metrics from legacyFiles
  const totalFiles = legacyFiles.length;
  const repositories = [...new Set(legacyFiles.map(f => f.repository))];
  const totalRepos = repositories.length;
  const branches = [...new Set(legacyFiles.map(f => f.branch || 'main'))];
  
  // Group by keyword
  const keywordStats = {};
  legacyFiles.forEach(file => {
    file.matchedKeywords?.forEach(keyword => {
      keywordStats[keyword] = (keywordStats[keyword] || 0) + 1;
    });
  });

  if (totalFiles === 0) {
    return (
      <div className="dashboard-container">
        <div className="dashboard-empty">
          <div className="empty-icon">📊</div>
          <h2>No Scan Data Available</h2>
          <p>Run a legacy configuration scan to see statistics and visualizations here.</p>
          <p className="empty-hint">Go to the "🧹 Legacy Config Cleanup" tab to start scanning.</p>
        </div>
      </div>
    );
  }

  return (
    <div className="dashboard-container">
      <div className="dashboard-header">
        <h1>📊 Legacy Config Scan Results</h1>
        <p className="dashboard-subtitle">Visual analysis of detected legacy configurations</p>
      </div>

      {/* Summary Cards */}
      <div className="metrics-grid">
        <div className="metric-card">
          <div className="metric-icon">📄</div>
          <div className="metric-content">
            <div className="metric-value">{totalFiles}</div>
            <div className="metric-label">Legacy Files Found</div>
          </div>
        </div>

        <div className="metric-card">
          <div className="metric-icon">📦</div>
          <div className="metric-content">
            <div className="metric-value">{totalRepos}</div>
            <div className="metric-label">Affected Repositories</div>
          </div>
        </div>

        <div className="metric-card">
          <div className="metric-icon">🌿</div>
          <div className="metric-content">
            <div className="metric-value">{branches.length}</div>
            <div className="metric-label">Branches Scanned</div>
          </div>
        </div>

        <div className="metric-card">
          <div className="metric-icon">🔑</div>
          <div className="metric-content">
            <div className="metric-value">{Object.keys(keywordStats).length}</div>
            <div className="metric-label">Keywords Matched</div>
          </div>
        </div>

        {scanDuration !== null && scanDuration > 0 && (
          <div className="metric-card" style={{ background: 'linear-gradient(135deg, #43e97b15 0%, #38f9d715 100%)', border: '1px solid #43e97b30' }}>
            <div className="metric-icon">⏱️</div>
            <div className="metric-content">
              <div className="metric-value">
                {Math.floor(scanDuration / 60)}:{(scanDuration % 60).toString().padStart(2, '0')}
              </div>
              <div className="metric-label" style={{ color: '#059669' }}>Scan Duration</div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default Dashboard;
