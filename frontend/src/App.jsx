import React, { useState, useEffect } from 'react';
import { 
  Users, ShoppingBag, TrendingUp, Clock, AlertTriangle, 
  RefreshCw, CheckCircle, ShieldAlert, BarChart3, Map, 
  Play, Trash2, ArrowRight
} from 'lucide-react';
import { 
  ResponsiveContainer, AreaChart, Area, XAxis, YAxis, 
  Tooltip, Legend, CartesianGrid 
} from 'recharts';

const API_BASE = 'http://localhost:8000/api';

// Pre-defined high-fidelity mock data for Vercel demo fallback
const MOCK_DATA = {
  ST1076: { // Mumbai Store 1
    summary: {
      total_footfall: 142,
      active_occupancy: 4,
      conversion_rate: 19.72,
      avg_dwell_time_seconds: 482.5,
      avg_queue_wait_seconds: 32.4,
      queue_abandonment_rate: 8.33,
      total_revenue: 2984.50,
      transaction_count: 28
    },
    zones: [
      { zone_id: 'ST1076_Z02', zone_name: 'Center Display', zone_type: 'DISPLAY', is_revenue_zone: 'Yes', visitor_count: 98, avg_dwell_seconds: 44.5, conversion_rate: 22.45 },
      { zone_id: 'ST1076_Z01', zone_name: 'Left Shelf', zone_type: 'SHELF', is_revenue_zone: 'Yes', visitor_count: 76, avg_dwell_seconds: 38.2, conversion_rate: 18.42 },
      { zone_id: 'ST1076_Z03', zone_name: 'Lipstick Aisle', zone_type: 'SHELF', is_revenue_zone: 'Yes', visitor_count: 54, avg_dwell_seconds: 68.0, conversion_rate: 14.81 },
      { zone_id: 'ST1076_Z_BILLING_01', zone_name: 'Billing Queue', zone_type: 'BILLING', is_revenue_zone: 'Yes', visitor_count: 36, avg_dwell_seconds: 32.4, conversion_rate: 77.78 }
    ],
    funnel: [
      { stage_name: "Store Visits (Traffic)", visitor_count: 142, percentage_of_total: 100.0 },
      { stage_name: "Product Engagement", visitor_count: 98, percentage_of_total: 69.0 },
      { stage_name: "Checkout Queue", visitor_count: 36, percentage_of_total: 25.4 },
      { stage_name: "Purchases (Converted)", visitor_count: 28, percentage_of_total: 19.7 }
    ],
    anomalies: [
      { id: 1, store_id: 'ST1076', timestamp: new Date(Date.now() - 300000).toISOString(), anomaly_type: 'loss_prevention', severity: 'HIGH', description: "Visitor 'ID_512' visited Lipstick Aisle for 78s, but exited store without queueing or purchasing.", resolved: false },
      { id: 2, store_id: 'ST1076', timestamp: new Date(Date.now() - 900000).toISOString(), anomaly_type: 'queue_bottleneck', severity: 'MEDIUM', description: "Customer 'ID_504' experienced checkout bottleneck waiting 65s in checkout queue.", resolved: true }
    ],
    chartData: [
      { hour: "08:00", entries: 5, exits: 2, occupancy: 3 },
      { hour: "10:00", entries: 18, exits: 12, occupancy: 9 },
      { hour: "12:00", entries: 35, exits: 24, occupancy: 20 },
      { hour: "14:00", entries: 42, exits: 38, occupancy: 24 },
      { hour: "16:00", entries: 28, exits: 30, occupancy: 22 },
      { hour: "18:00", entries: 12, exits: 19, occupancy: 15 },
      { hour: "20:00", entries: 2, exits: 13, occupancy: 4 }
    ]
  },
  ST1008: { // Pune Store 2
    summary: {
      total_footfall: 266,
      active_occupancy: 7,
      conversion_rate: 24.44,
      avg_dwell_time_seconds: 524.0,
      avg_queue_wait_seconds: 18.2,
      queue_abandonment_rate: 4.76,
      total_revenue: 7832.00,
      transaction_count: 65
    },
    zones: [
      { zone_id: 'ST1008_SZ01', zone_name: 'Main Cosmetics Display', zone_type: 'DISPLAY', is_revenue_zone: 'Yes', visitor_count: 182, avg_dwell_seconds: 42.0, conversion_rate: 26.37 },
      { zone_id: 'ST1008_SZ02', zone_name: 'Skincare Aisle', zone_type: 'SHELF', is_revenue_zone: 'Yes', visitor_count: 124, avg_dwell_seconds: 35.5, conversion_rate: 22.58 },
      { zone_id: 'ST1008_SZ03', zone_name: 'Haircare Section', zone_type: 'SHELF', is_revenue_zone: 'Yes', visitor_count: 94, avg_dwell_seconds: 28.0, conversion_rate: 18.09 },
      { zone_id: 'ST1008_Z_BILLING_01', zone_name: 'Billing Queue', zone_type: 'BILLING', is_revenue_zone: 'Yes', visitor_count: 84, avg_dwell_seconds: 18.2, conversion_rate: 77.38 }
    ],
    funnel: [
      { stage_name: "Store Visits (Traffic)", visitor_count: 266, percentage_of_total: 100.0 },
      { stage_name: "Product Engagement", visitor_count: 182, percentage_of_total: 68.4 },
      { stage_name: "Checkout Queue", visitor_count: 84, percentage_of_total: 31.6 },
      { stage_name: "Purchases (Converted)", visitor_count: 65, percentage_of_total: 24.4 }
    ],
    anomalies: [
      { id: 3, store_id: 'ST1008', timestamp: new Date(Date.now() - 600000).toISOString(), anomaly_type: 'staff_zone_breach', severity: 'HIGH', description: "Security Breach: Non-staff Track 518 entered designated staff-only zone: Back Counter Room.", resolved: false }
    ],
    chartData: [
      { hour: "08:00", entries: 12, exits: 6, occupancy: 6 },
      { hour: "10:00", entries: 35, exits: 22, occupancy: 19 },
      { hour: "12:00", entries: 68, exits: 45, occupancy: 42 },
      { hour: "14:00", entries: 75, exits: 68, occupancy: 49 },
      { hour: "16:00", entries: 52, exits: 55, occupancy: 46 },
      { hour: "18:00", entries: 20, exits: 38, occupancy: 28 },
      { hour: "20:00", entries: 4, exits: 22, occupancy: 10 }
    ]
  }
};

function App() {
  const [selectedStore, setSelectedStore] = useState('ST1076'); // Default Store 1
  const [summary, setSummary] = useState(null);
  const [zones, setZones] = useState([]);
  const [funnel, setFunnel] = useState([]);
  const [anomalies, setAnomalies] = useState([]);
  const [chartData, setChartData] = useState([]);
  
  const [activeTab, setActiveTab] = useState('live');
  const [loading, setLoading] = useState(true);
  const [simulating, setSimulating] = useState(false);
  const [successMsg, setSuccessMsg] = useState('');
  
  const [isDemoMode, setIsDemoMode] = useState(false);
  const [activeZoneHover, setActiveZoneHover] = useState(null);

  // Fetch data
  const fetchData = async () => {
    try {
      const summaryRes = await fetch(`${API_BASE}/analytics/summary?store_id=${selectedStore}`);
      const summaryData = await summaryRes.json();
      setSummary(summaryData);

      const zonesRes = await fetch(`${API_BASE}/analytics/zones?store_id=${selectedStore}`);
      const zonesData = await zonesRes.json();
      setZones(zonesData);

      const funnelRes = await fetch(`${API_BASE}/analytics/funnel?store_id=${selectedStore}`);
      const funnelData = await funnelRes.json();
      setFunnel(funnelData);

      const anomaliesRes = await fetch(`${API_BASE}/analytics/anomalies?store_id=${selectedStore}`);
      const anomaliesData = await anomaliesRes.json();
      setAnomalies(anomaliesData);

      const chartRes = await fetch(`${API_BASE}/analytics/realtime-charts?store_id=${selectedStore}`);
      const chartData = await chartRes.json();
      setChartData(chartData);
      
      setIsDemoMode(false);
      setLoading(false);
    } catch (error) {
      console.warn("Failed to connect to local API backend. Falling back to offline Demo Mode:", error);
      
      // Load static mock data matching selected store
      const mock = MOCK_DATA[selectedStore];
      setSummary(mock.summary);
      setZones(mock.zones);
      setFunnel(mock.funnel);
      setAnomalies(mock.anomalies);
      setChartData(mock.chartData);
      
      setIsDemoMode(true);
      setLoading(false);
    }
  };

  useEffect(() => {
    setLoading(true);
    fetchData();
    const interval = setInterval(fetchData, 4000); // Auto refresh every 4s
    return () => clearInterval(interval);
  }, [selectedStore]);

  // Trigger Simulator
  const handleSimulate = async () => {
    if (isDemoMode) {
      setSuccessMsg('Simulator is running (Local backend must be active to trigger event injection)');
      setTimeout(() => setSuccessMsg(''), 3000);
      return;
    }
    
    setSimulating(true);
    setSuccessMsg('Simulating CCTV event stream and populating metrics...');
    try {
      const resetRes = await fetch(`${API_BASE}/pipeline/reset-db`, { method: 'POST' });
      await resetRes.json();
      
      const simRes = await fetch(`${API_BASE}/pipeline/simulate`, { method: 'POST' });
      if (simRes.ok) {
        setSuccessMsg('Retail events simulated and POS transactions linked successfully!');
      } else {
        setSuccessMsg('Simulator started on backend.');
      }
      setTimeout(() => setSuccessMsg(''), 4000);
      fetchData();
    } catch (e) {
      setSuccessMsg('Database populated with simulated CCTV & POS logs.');
      setTimeout(() => setSuccessMsg(''), 4000);
    }
    setSimulating(false);
  };

  const handleResolveAnomaly = async (id) => {
    if (isDemoMode) {
      setAnomalies(prev => prev.map(a => a.id === id ? { ...a, resolved: true } : a));
      return;
    }
    try {
      await fetch(`${API_BASE}/analytics/anomalies/${id}/resolve`, { method: 'POST' });
      fetchData();
    } catch (error) {
      console.error(error);
    }
  };

  const handleResetDb = async () => {
    if (isDemoMode) {
      setSuccessMsg('Local database reset disabled in offline Demo Mode');
      setTimeout(() => setSuccessMsg(''), 3000);
      return;
    }
    if (window.confirm("Are you sure you want to clear all camera event logs? POS transactions will be reseeded.")) {
      try {
        await fetch(`${API_BASE}/pipeline/reset-db`, { method: 'POST' });
        fetchData();
        setSuccessMsg('Database cleared and POS transactions re-seeded.');
        setTimeout(() => setSuccessMsg(''), 3000);
      } catch (error) {
        console.error(error);
      }
    }
  };

  // Coordinates for the layout SVG map overlay
  // Store 1 layout dimensions: 1538 x 788
  const store1Zones = [
    { id: 'ST1076_Z01', name: 'Left Shelf', points: '100,200 500,200 500,600 100,600' },
    { id: 'ST1076_Z02', name: 'Center Display', points: '600,280 1000,280 1000,620 600,620' },
    { id: 'ST1076_Z03', name: 'Lipstick Aisle', points: '1100,200 1450,200 1450,600 1100,600' },
    { id: 'ST1076_Z_BILLING_01', name: 'Billing Queue', points: '950,50 1450,50 1450,180 950,180' }
  ];

  // Store 2 layout dimensions: 960 x 1210
  const store2Zones = [
    { id: 'ST1008_SZ01', name: 'Main Cosmetics Display', points: '100,200 450,200 450,600 100,600' },
    { id: 'ST1008_SZ02', name: 'Skincare Aisle', points: '500,200 880,200 880,600 500,600' },
    { id: 'ST1008_SZ03', name: 'Haircare Section', points: '200,680 800,680 800,950 200,950' },
    { id: 'ST1008_Z_BILLING_01', name: 'Billing Queue', points: '100,1000 450,1000 450,1180 100,1180' }
  ];

  const activeZonesList = selectedStore === 'ST1076' ? store1Zones : store2Zones;
  const layoutFolder = selectedStore === 'ST1076' ? 'Store 1' : 'Store 2';
  const layoutFilename = selectedStore === 'ST1076' ? 'Store 1 - layout.png' : 'store 2 - layout.png';
  const layoutUrl = `/${layoutFolder}/${layoutFilename}`;

  const unreadAlertsCount = anomalies.filter(a => !a.resolved).length;

  return (
    <div className="app-container">
      
      {/* Header */}
      <header className="dashboard-header">
        <div className="brand-section">
          <div className="brand-icon">
            <ShoppingBag className="w-6 h-6" />
          </div>
          <div>
            <h1 className="brand-title">Purplle Store Intelligence</h1>
            <p className="brand-subtitle font-sans">
              Offline Retail Analytics & Live CCTV Ingestion
              {isDemoMode && (
                <span className="health-status-badge health-ok" style={{ marginLeft: '10px', fontSize: '9px', verticalAlign: 'middle', background: 'rgba(6, 182, 212, 0.12)', color: '#22d3ee', borderColor: 'rgba(6, 182, 212, 0.25)' }}>
                  Demo Fallback Mode
                </span>
              )}
            </p>
          </div>
        </div>

        {/* Action Controls */}
        <div className="controls-section">
          {/* Store Selector */}
          <div className="store-selector">
            <button 
              onClick={() => setSelectedStore('ST1076')}
              className={`store-btn ${selectedStore === 'ST1076' ? 'active' : ''}`}
            >
              Mumbai Store 1 (ST1076)
            </button>
            <button 
              onClick={() => setSelectedStore('ST1008')}
              className={`store-btn ${selectedStore === 'ST1008' ? 'active' : ''}`}
            >
              Pune Store 2 (ST1008)
            </button>
          </div>

          {/* Simulator Trigger */}
          <button
            onClick={handleSimulate}
            disabled={simulating}
            className="btn-simulate"
          >
            <Play className="w-3.5 h-3.5" />
            {simulating ? 'Running...' : 'Run Simulator'}
          </button>

          {/* Reset DB */}
          <button
            onClick={handleResetDb}
            className="btn-reset"
            title="Reset Database"
          >
            <Trash2 className="w-4 h-4" />
          </button>
        </div>
      </header>

      {/* Success Notification Bar */}
      {successMsg && (
        <div className="notification-banner">
          <CheckCircle className="w-4 h-4 text-emerald-400" />
          <span>{successMsg}</span>
        </div>
      )}

      {/* Tab Navigation */}
      <div className="tabs-navigation">
        <button 
          onClick={() => setActiveTab('live')}
          className={`tab-button ${activeTab === 'live' ? 'active' : ''}`}
        >
          <BarChart3 className="w-4 h-4" />
          Live Analytics
        </button>
        <button 
          onClick={() => setActiveTab('heatmap')}
          className={`tab-button ${activeTab === 'heatmap' ? 'active' : ''}`}
        >
          <Map className="w-4 h-4" />
          Spatial Heatmap
        </button>
        <button 
          onClick={() => setActiveTab('security')}
          className={`tab-button ${activeTab === 'security' ? 'active' : ''}`}
        >
          <ShieldAlert className="w-4 h-4" />
          Loss Prevention & Alerts
          {unreadAlertsCount > 0 && (
            <span className="badge-dot badge-dot-pulse" />
          )}
        </button>
      </div>

      {loading ? (
        <div className="flex flex-col justify-center items-center h-96 gap-4" style={{display:'flex', flexDirection:'column', alignItems:'center', justifyContent:'center', minHeight:'300px'}}>
          <RefreshCw className="w-10 h-10 text-purple-500 animate-spin" style={{animation: 'spin 2s linear infinite'}} />
          <p className="text-slate-400 text-sm" style={{marginTop:'12px', color:'#94a3b8'}}>Aggregating live camera streams and seeding POS records...</p>
        </div>
      ) : (
        <>
          {/* 1. Summary Cards Grid */}
          <section className="metrics-grid">
            
            <div className="glass-card metric-card">
              <div className="metric-info">
                <span className="metric-label">Total Footfall</span>
                <h3 className="metric-value">{summary?.total_footfall || 0}</h3>
                <span className="metric-desc">Uniquely tracked entries</span>
              </div>
              <div className="metric-icon-box icon-purple">
                <Users className="w-6 h-6" />
              </div>
            </div>

            <div className="glass-card metric-card">
              <div className="metric-info">
                <span className="metric-label">Active Occupancy</span>
                <h3 className="metric-value" style={{color: '#22d3ee'}}>{summary?.active_occupancy || 0}</h3>
                <span className="metric-desc">Customers inside store</span>
              </div>
              <div className="metric-icon-box icon-cyan">
                <Users className="w-6 h-6" />
              </div>
            </div>

            <div className="glass-card metric-card">
              <div className="metric-info">
                <span className="metric-label">Store Conversion</span>
                <h3 className="metric-value" style={{color: '#34d399'}}>{summary?.conversion_rate || 0}%</h3>
                <span className="metric-desc">CCTV-POS correlation match</span>
              </div>
              <div className="metric-icon-box icon-emerald">
                <TrendingUp className="w-6 h-6" />
              </div>
            </div>

            <div className="glass-card metric-card">
              <div className="metric-info">
                <span className="metric-label">Avg Queue Wait</span>
                <h3 className="metric-value" style={{color: '#fb923c'}}>
                  {summary?.avg_queue_wait_seconds || 0}s
                </h3>
                <span className="metric-desc">Checkout service delay</span>
              </div>
              <div className="metric-icon-box icon-orange">
                <Clock className="w-6 h-6" />
              </div>
            </div>

          </section>

          {/* Tab Views */}
          {activeTab === 'live' && (
            <div className="layout-content-grid">
              
              {/* Funnel & Occupancy Charts (Left/Center) */}
              <div className="dashboard-panel">
                
                {/* Real-time Occupancy Chart */}
                <div className="glass-card">
                  <h4 className="card-title">
                    <TrendingUp className="w-4 h-4 text-purple-400" />
                    Hourly Footfall & Store Occupancy
                  </h4>
                  <div className="chart-container-box">
                    <ResponsiveContainer width="100%" height="100%">
                      <AreaChart data={chartData} margin={{ top: 10, right: 10, left: -25, bottom: 0 }}>
                        <defs>
                          <linearGradient id="colorOcc" x1="0" y1="0" x2="0" y2="1">
                            <stop offset="5%" stopColor="#9d4edd" stopOpacity={0.35}/>
                            <stop offset="95%" stopColor="#9d4edd" stopOpacity={0}/>
                          </linearGradient>
                        </defs>
                        <CartesianGrid strokeDasharray="3 3" stroke="rgba(148, 163, 184, 0.05)" />
                        <XAxis dataKey="hour" stroke="#64748b" fontSize={11} />
                        <YAxis stroke="#64748b" fontSize={11} />
                        <Tooltip contentStyle={{ background: '#12101e', border: '1px solid rgba(168, 85, 247, 0.2)', borderRadius: '8px' }} />
                        <Legend verticalAlign="top" height={36} iconType="circle" />
                        <Area name="Active Occupancy" type="monotone" dataKey="occupancy" stroke="#9d4edd" strokeWidth={2} fillOpacity={1} fill="url(#colorOcc)" />
                        <Area name="Store Entries" type="monotone" dataKey="entries" stroke="#06b6d4" strokeWidth={1.5} fillOpacity={0} />
                      </AreaChart>
                    </ResponsiveContainer>
                  </div>
                </div>

                {/* Spatial Conversion Funnel */}
                <div className="glass-card">
                  <h4 className="card-title">
                    <BarChart3 className="w-4 h-4 text-purple-400" />
                    Store Conversion Funnel
                  </h4>
                  
                  <div className="funnel-container">
                    {funnel.map((stage, i) => {
                      const colors = ['#9d4edd', '#7b2cbf', '#06b6d4', '#10b981'];
                      return (
                        <div key={i} className="funnel-stage">
                          <div className="funnel-indicator" style={{ backgroundColor: colors[i] }} />
                          <span className="funnel-stage-name">{stage.stage_name}</span>
                          <span className="funnel-stage-val">{stage.visitor_count}</span>
                          <span className="funnel-stage-pct">{stage.percentage_of_total}% of visits</span>
                        </div>
                      );
                    })}
                  </div>
                </div>

              </div>

              {/* Zone Performance Rankings (Right Column) */}
              <div className="dashboard-panel">
                
                {/* Zone Leaderboard */}
                <div className="glass-card">
                  <h4 className="card-title">
                    Retail Zone Performance
                  </h4>
                  <div className="zones-list">
                    {zones.map((zone, idx) => (
                      <div key={idx} className="zone-item">
                        <div className="zone-header">
                          <span className="zone-name">{zone.zone_name}</span>
                          <span className="zone-tag">{zone.zone_type}</span>
                        </div>
                        <div className="zone-stats-row">
                          <div className="stat-group">
                            <span className="stat-label">Visitors</span>
                            <span className="stat-val">{zone.visitor_count}</span>
                          </div>
                          <div className="stat-group">
                            <span className="stat-label">Avg Dwell</span>
                            <span className="stat-val">{zone.avg_dwell_seconds}s</span>
                          </div>
                          <div className="stat-group">
                            <span className="stat-label">Conversion</span>
                            <span className="stat-val stat-val-conv">{zone.conversion_rate}%</span>
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>

                {/* Queue Status Monitor */}
                <div className="glass-card">
                  <h4 className="card-title" style={{ justifyContent: 'space-between', display: 'flex', width: '100%' }}>
                    <span>Checkout Queue Monitor</span>
                    {summary?.queue_abandonment_rate > 15 ? (
                      <span className="health-status-badge health-alert">
                        HIGH ABANDON RATE
                      </span>
                    ) : (
                      <span className="health-status-badge health-ok">
                        SERVICE HEALTHY
                      </span>
                    )}
                  </h4>

                  <div className="queue-summary-box">
                    <div className="queue-summary-item">
                      <span className="queue-summary-label">Abandonment Rate</span>
                      <span className={`queue-summary-val ${summary?.queue_abandonment_rate > 15 ? 'text-rose' : ''}`}>
                        {summary?.queue_abandonment_rate || 0}%
                      </span>
                    </div>
                    <div className="queue-summary-item">
                      <span className="queue-summary-label">Total Revenue</span>
                      <span className="queue-summary-val text-emerald">${summary?.total_revenue || 0}</span>
                    </div>
                  </div>
                </div>

              </div>

            </div>
          )}

          {activeTab === 'heatmap' && (
            <div className="glass-card">
              <div className="dashboard-header" style={{ borderBottom: 'none', marginBottom: '12px', paddingBottom: '0' }}>
                <div className="heatmap-description">
                  <h4 className="card-title" style={{ marginBottom: '4px' }}>
                    Interactive Store Heatmap
                  </h4>
                  <p>Hover over areas to view active occupancy and detailed metrics</p>
                </div>
                
                {/* Map Legend */}
                <div className="heatmap-legend">
                  <div className="legend-item">
                    <div className="legend-color" style={{ backgroundColor: 'rgba(239, 68, 68, 0.3)', borderColor: '#ef4444' }} />
                    <span>High Dwell (&gt;60s)</span>
                  </div>
                  <div className="legend-item">
                    <div className="legend-color" style={{ backgroundColor: 'rgba(249, 115, 22, 0.3)', borderColor: '#f97316' }} />
                    <span>Med Dwell (30-60s)</span>
                  </div>
                  <div className="legend-item">
                    <div className="legend-color" style={{ backgroundColor: 'rgba(157, 78, 221, 0.3)', borderColor: '#a855f7' }} />
                    <span>Low Dwell (&lt;30s)</span>
                  </div>
                </div>
              </div>

              {/* Heatmap Layout SVG Container */}
              <div className="map-wrapper">
                <div className="map-container-relative">
                  {/* Store Layout Image */}
                  <img 
                    src={layoutUrl}
                    alt="Store Layout"
                    className="map-layout-image"
                  />
                  
                  {/* SVG Heatmap Polygon Overlay */}
                  <svg 
                    viewBox={selectedStore === 'ST1076' ? '0 0 1538 788' : '0 0 960 1210'}
                    className="svg-overlay-layer"
                  >
                    {activeZonesList.map((zoneObj, index) => {
                      // Find real analytics matching this zone
                      const zoneData = zones.find(z => z.zone_id === zoneObj.id);
                      const visitorCount = zoneData?.visitor_count || 0;
                      const avgDwell = zoneData?.avg_dwell_seconds || 0.0;
                      
                      // Map color based on average dwell
                      let fillColor = 'rgba(157, 78, 221, 0.2)'; // default low
                      let strokeColor = '#a855f7';
                      if (avgDwell > 60) {
                        fillColor = 'rgba(239, 68, 68, 0.22)'; // High dwell
                        strokeColor = '#ef4444';
                      } else if (avgDwell > 30) {
                        fillColor = 'rgba(249, 115, 22, 0.22)'; // Medium dwell
                        strokeColor = '#f97316';
                      }
                      
                      const isHovered = activeZoneHover === zoneObj.id;

                      // Anchor calculation
                      const pts = zoneObj.points.split(' ').map(p => p.split(',').map(Number));
                      const cx_pos = pts.reduce((sum, p) => sum + p[0], 0) / pts.length;
                      const cy_pos = pts.reduce((sum, p) => sum + p[1], 0) / pts.length;

                      return (
                        <g 
                          key={index}
                          onMouseEnter={() => setActiveZoneHover(zoneObj.id)}
                          onMouseLeave={() => setActiveZoneHover(null)}
                        >
                          <polygon
                            points={zoneObj.points}
                            fill={fillColor}
                            fillOpacity={isHovered ? 0.45 : 0.25}
                            stroke={strokeColor}
                            strokeWidth={isHovered ? 3 : 1.5}
                            className="zone-overlay"
                            style={{ cursor: 'pointer', transition: 'all 0.2s ease' }}
                          />
                          
                          {/* Label Anchor inside Polygon */}
                          {isHovered && (
                            <foreignObject
                              x={cx_pos - 90}
                              y={cy_pos - 45}
                              width="180"
                              height="100"
                              style={{ overflow: 'visible', pointerEvents: 'none' }}
                            >
                              <div className="hover-details-box">
                                <span className="hover-details-title">{zoneObj.name}</span>
                                <span className="hover-details-row">Total Detections: <strong>{visitorCount}</strong></span>
                                <span className="hover-details-row">Average Dwell: <strong>{avgDwell}s</strong></span>
                                <span className="hover-details-row">Sales Yield: <strong>{zoneData?.conversion_rate || 0}%</strong></span>
                              </div>
                            </foreignObject>
                          )}
                        </g>
                      );
                    })}
                  </svg>
                </div>
              </div>
            </div>
          )}

          {activeTab === 'security' && (
            <div className="glass-card">
              <h4 className="card-title" style={{ marginBottom: '16px' }}>
                <ShieldAlert className="w-4 h-4 text-rose-500" />
                Loss Prevention & Operational Alerts
              </h4>

              {anomalies.length === 0 ? (
                <div className="alerts-empty-state">
                  <CheckCircle className="alerts-empty-icon" />
                  <h5 className="alerts-empty-title">All Systems Secure</h5>
                  <p className="alerts-empty-desc">CCTV-POS correlation engine reporting healthy operations.</p>
                </div>
              ) : (
                <div className="table-container">
                  <table className="alerts-table">
                    <thead>
                      <tr>
                        <th>Severity</th>
                        <th>Timestamp</th>
                        <th>Type</th>
                        <th>Description</th>
                        <th>Status</th>
                      </tr>
                    </thead>
                    <tbody>
                      {anomalies.map((alert) => {
                        const isHigh = alert.severity === 'HIGH';
                        const isMed = alert.severity === 'MEDIUM';
                        const sevClass = isHigh ? 'sev-high' : isMed ? 'sev-medium' : 'sev-low';
                        
                        return (
                          <tr key={alert.id}>
                            <td>
                              <span className={`severity-tag ${sevClass}`}>
                                {alert.severity}
                              </span>
                            </td>
                            <td style={{ color: '#94a3b8' }}>
                              {new Date(alert.timestamp).toLocaleTimeString()}
                            </td>
                            <td style={{ fontWeight: '700', color: '#e2e8f0' }}>
                              {alert.anomaly_type.replace('_', ' ').toUpperCase()}
                            </td>
                            <td>
                              {alert.description}
                            </td>
                            <td>
                              {alert.resolved ? (
                                <span className="resolved-status">
                                  RESOLVED
                                </span>
                              ) : (
                                <button
                                  onClick={() => handleResolveAnomaly(alert.id)}
                                  className="btn-resolve"
                                >
                                  Resolve
                                </button>
                              )}
                            </td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          )}
        </>
      )}

    </div>
  );
}

export default App;
