import React, { useState, useEffect, useRef } from 'react';
import { api } from './api';
import { 
  Building2, 
  MapPin, 
  AlertTriangle, 
  BookOpen, 
  LogOut, 
  Send, 
  CheckCircle2, 
  Loader2, 
  FileText, 
  Trash2, 
  Upload, 
  Activity, 
  AlertCircle, 
  RefreshCw,
  Sparkles,
  Search,
  Clock,
  ShieldAlert
} from 'lucide-react';

export default function App() {
  const [user, setUser] = useState(api.getUser());
  const [activeTab, setActiveTab] = useState('report'); // report | dashboard | kb
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  // Login form state
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');

  // Citizen Report form state
  const [description, setDescription] = useState('');
  const [wardId, setWardId] = useState('w1');
  const [lat, setLat] = useState('18.5204');
  const [lng, setLng] = useState('73.8567');
  const [imageUrl, setImageUrl] = useState('');
  
  // Pipeline streaming state
  const [pipelineSessionId, setPipelineSessionId] = useState(null);
  const [pipelineSteps, setPipelineSteps] = useState([]);
  const [pipelineResult, setPipelineResult] = useState(null);
  const [streamActive, setStreamActive] = useState(false);

  // Dashboard state
  const [dashboardData, setDashboardData] = useState({
    health_score: 82.5,
    heatmap: [],
    trend_7d: [],
    top_critical_issues: []
  });
  const [dashboardStreamConnected, setDashboardStreamConnected] = useState(false);
  const [dashboardNotifications, setDashboardNotifications] = useState([]);
  const [operationsFeed, setOperationsFeed] = useState([
    { id: '1', time: '10:42', text: 'New water issue TSK-003 submitted in Ward 1', type: 'info' },
    { id: '2', time: '10:42', text: 'RAG cited Water Leakage Protocol', type: 'rag' },
    { id: '3', time: '10:43', text: 'Task TSK-003 assigned to Water Department', type: 'routing' },
    { id: '4', time: '10:43', text: 'Auto-dispatch validation: CONFIDENCE 95%', type: 'success' },
  ]);

  // Knowledge base state
  const [kbDocs, setKbDocs] = useState([]);
  const [kbUploading, setKbUploading] = useState(false);
  const [kbFile, setKbFile] = useState(null);

  useEffect(() => {
    // If logged in, set active tab based on role
    if (user) {
      if (user.role === 'government_officer') {
        setActiveTab('dashboard');
      } else {
        setActiveTab('report');
      }
    }
  }, [user]);

  // Handle dashboard fetching and SSE stream
  useEffect(() => {
    if (!user || activeTab !== 'dashboard') return;

    fetchDashboard();

    // Setup dashboard stream
    const url = api.getStreamUrl('/analytics/dashboard/stream');
    let sse;
    try {
      sse = new EventSource(url);
      setDashboardStreamConnected(true);

      sse.onmessage = (event) => {
        const updatedTask = JSON.parse(event.data);
        const timestamp = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
        
        setOperationsFeed(prev => [
          {
            id: Math.random().toString(36).substring(7),
            time: timestamp,
            text: `Task ${updatedTask.task_id} status changed to ${updatedTask.status.toUpperCase()}`,
            type: 'update'
          },
          {
            id: Math.random().toString(36).substring(7),
            time: timestamp,
            text: `Task ${updatedTask.task_id} in Ward ${updatedTask.ward_id} registered (${updatedTask.priority} priority)`,
            type: 'routing'
          },
          ...prev
        ]);

        setDashboardNotifications(prev => [
          {
            id: Math.random().toString(36).substring(7),
            message: `Task ${updatedTask.task_id} in Ward ${updatedTask.ward_id} status updated to ${updatedTask.status}`,
            timestamp: new Date().toLocaleTimeString()
          },
          ...prev.slice(0, 4)
        ]);
        
        fetchDashboard();
      };

      sse.onerror = () => {
        setDashboardStreamConnected(false);
      };
    } catch (err) {
      console.error(err);
    }

    return () => {
      if (sse) sse.close();
      setDashboardStreamConnected(false);
    };
  }, [user, activeTab]);

  // Handle KB listing
  useEffect(() => {
    if (!user || activeTab !== 'kb') return;
    fetchKbDocs();
  }, [user, activeTab]);

  const fetchDashboard = async () => {
    try {
      const data = await api.getDashboard();
      setDashboardData(data);
    } catch (err) {
      console.error('Failed to fetch dashboard data', err);
    }
  };

  const fetchKbDocs = async () => {
    try {
      const data = await api.listDocuments();
      setKbDocs(data);
    } catch (err) {
      console.error('Failed to fetch KB docs', err);
    }
  };

  const handleLogin = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    try {
      const loggedUser = await api.login(username, password);
      setUser(loggedUser);
    } catch (err) {
      setError(err.message || 'Login failed');
    } finally {
      setLoading(false);
    }
  };

  const handleLogout = () => {
    api.logout();
    setUser(null);
  };

  const handleIssueSubmit = async (e) => {
    e.preventDefault();
    if (description.length < 10) {
      setError('Description must be at least 10 characters long');
      return;
    }

    setLoading(true);
    setError(null);
    setPipelineResult(null);
    setPipelineSteps([]);
    
    // Generate a unique session ID
    const sessionId = `sess_${Math.random().toString(36).substring(7)}`;
    setPipelineSessionId(sessionId);
    setStreamActive(true);

    // Open EventSource stream for progress before making the post request
    const streamUrl = api.getStreamUrl(`/chat/stream/${sessionId}`);
    const sse = new EventSource(streamUrl);

    sse.onmessage = (event) => {
      const message = event.data;
      if (message === 'Done') {
        sse.close();
        setStreamActive(false);
      } else {
        setPipelineSteps(prev => [...prev, message]);
      }
    };

    sse.onerror = () => {
      sse.close();
      setStreamActive(false);
    };

    try {
      // POST the issue
      const result = await api.reportIssue(description, wardId, lat, lng, sessionId, imageUrl || null);
      setPipelineResult(result);
      // Clear form
      setDescription('');
      setImageUrl('');
    } catch (err) {
      setError(err.message || 'Submission failed');
      sse.close();
      setStreamActive(false);
    } finally {
      setLoading(false);
    }
  };

  const handleFileUpload = async (e) => {
    e.preventDefault();
    if (!kbFile) return;
    setKbUploading(true);
    setError(null);
    try {
      await api.uploadDocument(kbFile);
      setKbFile(null);
      // Reset input element
      document.getElementById('kb-file-input').value = '';
      fetchKbDocs();
    } catch (err) {
      setError(err.message || 'File upload failed');
    } finally {
      setKbUploading(false);
    }
  };

  const handleDocDelete = async (docId) => {
    if (!confirm(`Are you sure you want to delete ${docId}?`)) return;
    try {
      await api.deleteDocument(docId);
      fetchKbDocs();
    } catch (err) {
      alert(err.message || 'Delete failed');
    }
  };

  const isAdmin = user && (user.role === 'government_officer' || user.ward_ids.includes('*'));

  // RENDER LOGIN SCREEN
  if (!user) {
    return (
      <div className="login-container">
        <div className="glass-panel login-card">
          <div className="login-header">
            <div className="brand-logo" style={{ marginBottom: '16px' }}><Building2 size={48} color="var(--primary-color)" /></div>
            <h2 className="brand-name">SAMPARK AI</h2>
            <p style={{ color: 'var(--text-secondary)' }}>Community Decision Intelligence Platform</p>
          </div>

          {error && <div className="alert alert-error">{error}</div>}

          <form onSubmit={handleLogin}>
            <div className="form-group">
              <label className="form-label">Username</label>
              <input 
                type="text" 
                className="input-field" 
                placeholder="admin or leader_w1" 
                value={username}
                onChange={e => setUsername(e.target.value)}
                required
              />
            </div>
            
            <div className="form-group">
              <label className="form-label">Password</label>
              <input 
                type="password" 
                className="input-field" 
                placeholder="••••••••" 
                value={password}
                onChange={e => setPassword(e.target.value)}
                required
              />
            </div>

            <button type="submit" className="btn btn-primary" style={{ width: '100%', marginTop: '12px' }} disabled={loading}>
              {loading ? (
                <>
                  <Loader2 className="spinner" style={{ marginRight: '8px' }} />
                  Authenticating...
                </>
              ) : 'Sign In'}
            </button>
          </form>

          <div style={{ marginTop: '24px', textAlign: 'center', fontSize: '13px', color: 'var(--text-secondary)' }}>
            <p>Demo credentials:</p>
            <p style={{ fontFamily: 'monospace', marginTop: '4px' }}>admin / password (Officer/Admin)</p>
            <p style={{ fontFamily: 'monospace' }}>leader_w1 / password (Community Leader)</p>
          </div>
        </div>
      </div>
    );
  }

  // RENDER APP PORTAL
  return (
    <div className="layout-wrapper">
      {/* SIDEBAR */}
      <aside className="sidebar">
        <div>
          <div className="brand-section">
            <span className="brand-logo"><Building2 size={28} color="var(--primary-color)" /></span>
            <span className="brand-name">Sampark AI</span>
          </div>

          <nav>
            <ul className="menu-list">
              <li 
                className={`menu-item ${activeTab === 'report' ? 'active' : ''}`}
                onClick={() => { setActiveTab('report'); setError(null); }}
              >
                <Send size={18} />
                Report Issue
              </li>
              
              <li 
                className={`menu-item ${activeTab === 'dashboard' ? 'active' : ''}`}
                onClick={() => { setActiveTab('dashboard'); setError(null); }}
              >
                <Activity size={18} />
                Dashboard
              </li>

              {isAdmin && (
                <li 
                  className={`menu-item ${activeTab === 'kb' ? 'active' : ''}`}
                  onClick={() => { setActiveTab('kb'); setError(null); }}
                >
                  <BookOpen size={18} />
                  Knowledge Base
                </li>
              )}
            </ul>
          </nav>
        </div>

        <div className="sidebar-footer" style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
          <div className="user-profile">
            <div className="profile-avatar">
              {user.username ? user.username[0].toUpperCase() : 'U'}
            </div>
            <div className="profile-info">
              <h4>{user.username || 'Demo User'}</h4>
              <span>{user.role === 'government_officer' ? 'Govt Officer' : 'Community Leader'}</span>
            </div>
          </div>
          
          <button onClick={handleLogout} className="btn btn-secondary" style={{ width: '100%' }}>
            <LogOut size={16} />
            Logout
          </button>
        </div>
      </aside>

      {/* MAIN CONTENT AREA */}
      <main className="main-content">
        <header className="header-container">
          <div>
            <h1 className="page-title">
              {activeTab === 'report' && 'Citizen Intake Portal'}
              {activeTab === 'dashboard' && 'Decision Intelligence Dashboard'}
              {activeTab === 'kb' && 'Knowledge Base Administration'}
            </h1>
            <p style={{ color: 'var(--text-secondary)', marginTop: '4px' }}>
              {activeTab === 'report' && 'Submit community complaints for automated multi-agent routing.'}
              {activeTab === 'dashboard' && `Geospatial risks and predictive analytics for Ward scope: ${user.ward_ids.join(', ')}`}
              {activeTab === 'kb' && 'Manage policy acts and municipal guidelines that ground recommendations.'}
            </p>
          </div>

          <div style={{ display: 'flex', gap: '12px', alignItems: 'center' }}>
            {activeTab === 'dashboard' && (
              <>
                <button onClick={async () => {
                  if (confirm("Reset local database to initial demo state?")) {
                    try {
                      await api.resetDemo();
                      alert("Database reset successfully!");
                      fetchDashboard();
                    } catch (err) {
                      alert(err.message || "Reset failed");
                    }
                  }
                }} className="btn btn-secondary" style={{ borderColor: 'var(--error-color)', color: '#f87171' }}>
                  <Trash2 size={15} />
                  Reset Demo
                </button>
                <button onClick={fetchDashboard} className="btn btn-secondary">
                  <RefreshCw size={15} />
                  Refresh
                </button>
              </>
            )}
            <span className="badge badge-medium" style={{ display: 'flex', alignItems: 'center', height: 'fit-content' }}>
              {user.role}
            </span>
          </div>
        </header>

        {error && <div className="alert alert-error" style={{ marginBottom: '32px' }}>{error}</div>}

        {/* TAB 1: REPORT ISSUE */}
        {activeTab === 'report' && (
          <div style={{ maxWidth: '800px' }}>
            <div className="glass-panel">
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
                <h3 style={{ fontSize: '20px', fontWeight: '700', margin: 0 }}>File a Complaint</h3>
                <button type="button" className="btn btn-secondary" style={{ padding: '4px 12px', fontSize: '12px' }} onClick={() => {
                  setDescription("Massive water leakage from the main municipal pipeline on MG Road causing urban flooding in the lowland zone.");
                  setWardId("w1");
                }}>
                  <Sparkles size={12} style={{ marginRight: '4px' }} /> Quick Fill Sample
                </button>
              </div>
              
              <form onSubmit={handleIssueSubmit}>
                <div className="form-group">
                  <label className="form-label">Issue Description</label>
                  <textarea 
                    className="input-field" 
                    rows="4" 
                    placeholder="Describe the community issue in detail (minimum 10 characters)... E.g., Major water leak on MG Road corner."
                    value={description}
                    onChange={e => setDescription(e.target.value)}
                    required
                  />
                </div>

                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: '16px' }}>
                  <div className="form-group">
                    <label className="form-label">Ward ID</label>
                    <select 
                      className="input-field"
                      value={wardId}
                      onChange={e => setWardId(e.target.value)}
                    >
                      <option value="w1">Ward 1 (w1)</option>
                      <option value="w2">Ward 2 (w2)</option>
                      <option value="w3">Ward 3 (w3)</option>
                    </select>
                  </div>

                  <div className="form-group">
                    <label className="form-label">Latitude</label>
                    <input 
                      type="text" 
                      className="input-field"
                      value={lat}
                      onChange={e => setLat(e.target.value)}
                      required
                    />
                  </div>

                  <div className="form-group">
                    <label className="form-label">Longitude</label>
                    <input 
                      type="text" 
                      className="input-field"
                      value={lng}
                      onChange={e => setLng(e.target.value)}
                      required
                    />
                  </div>
                </div>

                <div className="form-group">
                  <label className="form-label">Evidence Image URL (Optional)</label>
                  <input 
                    type="text" 
                    className="input-field"
                    placeholder="http://example.com/pothole.jpg"
                    value={imageUrl}
                    onChange={e => setImageUrl(e.target.value)}
                  />
                </div>

                <button type="submit" className="btn btn-primary" style={{ width: '100%', marginTop: '12px' }} disabled={loading}>
                  {loading ? (
                    <>
                      <Loader2 className="spinner" style={{ marginRight: '8px' }} />
                      Invoking LangGraph...
                    </>
                  ) : (
                    <>
                      <Send size={16} />
                      Submit to Decision Engine
                    </>
                  )}
                </button>
              </form>
            </div>

            {/* REAL-TIME PROGRESS SSE STREAM */}
            {(streamActive || pipelineSteps.length > 0) && (
              <div className="glass-panel progress-container">
                <div className="progress-header">
                  {streamActive && <div className="spinner" />}
                  <h4 style={{ fontWeight: '700' }}>
                    {streamActive ? 'Agent Pipeline Processing...' : 'Agent Execution History'}
                  </h4>
                </div>
                
                <div className="step-list">
                  {pipelineSteps.map((step, idx) => (
                    <div key={idx} className="step-item completed">
                      <div className="step-bullet" />
                      <span>{step}</span>
                    </div>
                  ))}
                  {streamActive && (
                    <div className="step-item">
                      <div className="step-bullet" style={{ animation: 'pulse 1s infinite' }} />
                      <span style={{ fontStyle: 'italic' }}>Waiting for next agent checkpoint...</span>
                    </div>
                  )}
                </div>
              </div>
            )}

            {/* PIPELINE RESPONSE PAYLOAD RESULT CARD */}
            {pipelineResult && (
              <div className="glass-panel result-card">
                <div className="result-header">
                  <CheckCircle2 size={20} />
                  <span>Issue Processed Successfully</span>
                </div>

                <div className="result-detail-grid">
                  <div>
                    <div className="result-label">Session ID</div>
                    <div className="result-value" style={{ fontFamily: 'monospace' }}>{pipelineResult.session_id}</div>
                  </div>
                  <div>
                    <div className="result-label">Issue ID</div>
                    <div className="result-value" style={{ fontFamily: 'monospace' }}>{pipelineResult.issue_id}</div>
                  </div>
                  <div>
                    <div className="result-label">Task ID</div>
                    <div className="result-value" style={{ fontFamily: 'monospace' }}>{pipelineResult.task_id}</div>
                  </div>
                  <div>
                    <div className="result-label">Issue Category</div>
                    <div className="result-value" style={{ textTransform: 'capitalize' }}>{pipelineResult.issue_type}</div>
                  </div>
                  <div>
                    <div className="result-label">Assigned Department</div>
                    <div className="result-value" style={{ color: 'var(--primary-color)' }}>{pipelineResult.department}</div>
                  </div>
                  <div>
                    <div className="result-label">Priority Level</div>
                    <div className="result-value">
                      <span className={`badge badge-${(pipelineResult.priority || 'low').toLowerCase()}`}>
                        {pipelineResult.priority}
                      </span>
                    </div>
                  </div>
                  <div>
                    <div className="result-label">Validation Confidence</div>
                    <div className="result-value">
                      <span className="badge badge-medium" style={{ background: pipelineResult.confidence >= 0.5 ? 'rgba(16, 185, 129, 0.2)' : 'rgba(239, 68, 68, 0.2)', color: pipelineResult.confidence >= 0.5 ? '#34d399' : '#f87171' }}>
                        {(pipelineResult.confidence * 100).toFixed(0)}%
                      </span>
                    </div>
                  </div>
                </div>

                <div style={{ marginBottom: '20px' }}>
                  <div className="result-label">Recommended Action</div>
                  <div className="result-value" style={{ color: 'var(--warning-color)', fontStyle: 'italic' }}>
                    "{pipelineResult.next_action}"
                  </div>
                </div>

                <div style={{ background: 'rgba(255, 255, 255, 0.03)', padding: '16px', borderRadius: '12px', border: '1px solid var(--border-color)', marginBottom: '20px' }}>
                  <div className="result-label">Citizen-facing Message</div>
                  <p style={{ fontSize: '15px', fontWeight: '500' }}>{pipelineResult.message}</p>
                </div>

                {pipelineResult.confidence < 0.4 && (
                  <div className="alert alert-error" style={{ marginBottom: '20px', background: 'rgba(239, 68, 68, 0.1)', borderColor: 'rgba(239, 68, 68, 0.2)', color: '#f87171' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px', fontWeight: 'bold' }}>
                      <ShieldAlert size={16} />
                      <span>Responsible AI Guardrail: Auto-dispatch Blocked</span>
                    </div>
                    <p style={{ fontSize: '13px', marginTop: '4px', opacity: 0.9 }}>
                      Reason: Low credibility score ({(pipelineResult.confidence * 100).toFixed(0)}%). Location or details require manual corroboration. Requesting citizen photos/evidence.
                    </p>
                  </div>
                )}

                {/* AI Decision Trace Panel */}
                {pipelineResult.ai_trace && (
                  <div className="trace-container">
                    <div className="trace-title">
                      <Sparkles size={20} />
                      <span>🤖 AI Decision Trace & Agent Reasoning Pipeline</span>
                    </div>

                    <div className="trace-timeline">
                      {/* 1. INTAKE AGENT */}
                      <div className="trace-agent-card">
                        <div className="trace-agent-header">
                          <div className="trace-agent-icon-wrapper">
                            <Send size={14} />
                          </div>
                          <span className="trace-agent-name">Intake Agent</span>
                          <span className="trace-agent-badge">Processed</span>
                        </div>
                        <div className="trace-grid">
                          <div className="trace-item">
                            <span className="trace-item-label">Extracted issue type</span>
                            <span className="trace-item-value" style={{ textTransform: 'capitalize' }}>
                              {pipelineResult.ai_trace.intake.extracted_type}
                            </span>
                          </div>
                          <div className="trace-item">
                            <span className="trace-item-label">Extracted location</span>
                            <span className="trace-item-value">
                              {pipelineResult.ai_trace.intake.extracted_location}
                            </span>
                          </div>
                          <div className="trace-item">
                            <span className="trace-item-label">Language detected</span>
                            <span className="trace-item-value" style={{ textTransform: 'uppercase' }}>
                              {pipelineResult.ai_trace.intake.language_detected}
                            </span>
                          </div>
                          <div className="trace-item" style={{ gridColumn: '1 / -1' }}>
                            <span className="trace-item-label">Summary</span>
                            <span className="trace-item-value" style={{ fontWeight: '500' }}>
                              "{pipelineResult.ai_trace.intake.summary}"
                            </span>
                          </div>
                        </div>
                      </div>

                      {/* 2. VALIDATION AGENT */}
                      <div className="trace-agent-card">
                        <div className="trace-agent-header">
                          <div className="trace-agent-icon-wrapper">
                            <CheckCircle2 size={14} />
                          </div>
                          <span className="trace-agent-name">Validation Agent</span>
                          <span className="trace-agent-badge">Evaluated</span>
                        </div>
                        <div className="trace-grid">
                          <div className="trace-item">
                            <span className="trace-item-label">Duplicate found</span>
                            <span className="trace-item-value" style={{ textTransform: 'capitalize', color: pipelineResult.ai_trace.validation.duplicate_found === 'yes' ? 'var(--warning-color)' : 'var(--success-color)' }}>
                              {pipelineResult.ai_trace.validation.duplicate_found}
                            </span>
                          </div>
                          <div className="trace-item">
                            <span className="trace-item-label">Location verified</span>
                            <span className="trace-item-value" style={{ textTransform: 'capitalize', color: pipelineResult.ai_trace.validation.location_verified === 'yes' ? 'var(--success-color)' : 'var(--error-color)' }}>
                              {pipelineResult.ai_trace.validation.location_verified}
                            </span>
                          </div>
                          <div className="trace-item">
                            <span className="trace-item-label">Weather corroboration</span>
                            <span className="trace-item-value" style={{ textTransform: 'capitalize', color: pipelineResult.ai_trace.validation.weather_corroboration === 'yes' ? 'var(--success-color)' : 'var(--text-secondary)' }}>
                              {pipelineResult.ai_trace.validation.weather_corroboration}
                            </span>
                          </div>
                          <div className="trace-item">
                            <span className="trace-item-label">Media evidence</span>
                            <span className="trace-item-value" style={{ textTransform: 'capitalize' }}>
                              {pipelineResult.ai_trace.validation.media_evidence}
                            </span>
                          </div>
                          <div className="trace-item">
                            <span className="trace-item-label">Confidence score</span>
                            <span className="trace-item-value" style={{ color: 'var(--primary-color)' }}>
                              {pipelineResult.ai_trace.validation.confidence_score}
                            </span>
                          </div>
                          
                          {pipelineResult.evidence_score && (
                            <div className="trace-item" style={{ gridColumn: '1 / -1', marginTop: '8px', background: 'rgba(255, 255, 255, 0.02)', padding: '12px', borderRadius: '8px', border: '1px solid var(--border-color)' }}>
                              <span className="trace-item-label" style={{ fontWeight: 'bold', color: 'var(--text-primary)', marginBottom: '8px', display: 'block' }}>
                                Credibility Evidence Score Breakdown ({pipelineResult.evidence_score.total}/100)
                              </span>
                              <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
                                {pipelineResult.evidence_score.components.map((comp, cIdx) => (
                                  <div key={cIdx} style={{ display: 'flex', justifyContent: 'space-between', fontSize: '12px' }}>
                                    <span style={{ color: 'var(--text-secondary)' }}>• {comp.label}</span>
                                    <span style={{ fontWeight: 'bold', color: comp.points > 10 ? 'var(--success-color)' : 'var(--text-secondary)' }}>+{comp.points} pts</span>
                                  </div>
                                ))}
                              </div>
                            </div>
                          )}
                        </div>
                      </div>

                      {/* 3. PREDICTION AGENT */}
                      <div className="trace-agent-card">
                        <div className="trace-agent-header">
                          <div className="trace-agent-icon-wrapper">
                            <Activity size={14} />
                          </div>
                          <span className="trace-agent-name">Prediction Agent</span>
                          <span className="trace-agent-badge">Forecasted</span>
                        </div>
                        <div className="trace-grid">
                          <div className="trace-item">
                            <span className="trace-item-label">Flood risk</span>
                            <span className="trace-item-value" style={{ color: parseFloat(pipelineResult.ai_trace.prediction.flood_risk) > 70 ? 'var(--error-color)' : 'var(--text-primary)' }}>
                              {pipelineResult.ai_trace.prediction.flood_risk}
                            </span>
                          </div>
                          <div className="trace-item">
                            <span className="trace-item-label">Road risk</span>
                            <span className="trace-item-value" style={{ color: parseFloat(pipelineResult.ai_trace.prediction.road_risk) > 70 ? 'var(--error-color)' : 'var(--text-primary)' }}>
                              {pipelineResult.ai_trace.prediction.road_risk}
                            </span>
                          </div>
                          <div className="trace-item">
                            <span className="trace-item-label">Traffic risk</span>
                            <span className="trace-item-value" style={{ textTransform: 'capitalize' }}>
                              {pipelineResult.ai_trace.prediction.traffic_risk}
                            </span>
                          </div>
                          <div className="trace-item" style={{ gridColumn: '1 / -1' }}>
                            <span className="trace-item-label">Risk explanation</span>
                            <span className="trace-item-value" style={{ fontSize: '13px', color: 'var(--text-secondary)' }}>
                              {pipelineResult.ai_trace.prediction.risk_explanation}
                            </span>
                          </div>

                          {pipelineResult.ai_trace.prediction.risk_factors && (
                            <div style={{ gridColumn: '1 / -1', marginTop: '8px', background: 'rgba(255, 255, 255, 0.02)', padding: '12px', borderRadius: '8px', border: '1px solid var(--border-color)' }}>
                              <span className="trace-item-label" style={{ fontWeight: 'bold', color: 'var(--text-primary)', marginBottom: '8px', display: 'block' }}>
                                Risk Factor Contribution Breakdown
                              </span>
                              <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
                                {pipelineResult.ai_trace.prediction.risk_factors.map((f, fIdx) => (
                                  <div key={fIdx} style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
                                    <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '12px' }}>
                                      <span style={{ color: 'var(--text-secondary)' }}>{f.factor}</span>
                                      <span style={{ fontWeight: 'bold', color: 'var(--primary-color)' }}>{f.weight}%</span>
                                    </div>
                                    <div style={{ width: '100%', height: '4px', background: 'rgba(255,255,255,0.05)', borderRadius: '99px', overflow: 'hidden' }}>
                                      <div style={{ width: `${f.weight}%`, height: '100%', background: 'var(--primary-color)' }} />
                                    </div>
                                  </div>
                                ))}
                              </div>
                            </div>
                          )}
                        </div>
                      </div>

                      {/* 4. RECOMMENDATION AGENT */}
                      <div className="trace-agent-card">
                        <div className="trace-agent-header">
                          <div className="trace-agent-icon-wrapper">
                            <Sparkles size={14} />
                          </div>
                          <span className="trace-agent-name">Recommendation Agent</span>
                          <span className="trace-agent-badge">Grounded</span>
                        </div>
                        <div className="trace-grid">
                          <div className="trace-item" style={{ gridColumn: '1 / -1' }}>
                            <span className="trace-item-label">Recommended action</span>
                            <span className="trace-item-value" style={{ color: 'var(--warning-color)' }}>
                              {pipelineResult.ai_trace.recommendation.action}
                            </span>
                          </div>
                          <div className="trace-item">
                            <span className="trace-item-label">Priority</span>
                            <span className="trace-item-value">
                              <span className={`badge badge-${pipelineResult.ai_trace.recommendation.priority.toLowerCase()}`}>
                                {pipelineResult.ai_trace.recommendation.priority}
                              </span>
                            </span>
                          </div>
                          <div className="trace-item">
                            <span className="trace-item-label">SLA</span>
                            <span className="trace-item-value">
                              {pipelineResult.ai_trace.recommendation.sla}
                            </span>
                          </div>
                          <div className="trace-item" style={{ gridColumn: '1 / -1' }}>
                            <span className="trace-item-label">Policy Citation Details (RAG Grounding)</span>
                            <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', marginTop: '6px' }}>
                              {pipelineResult.ai_trace.recommendation.policy_details && pipelineResult.ai_trace.recommendation.policy_details.map((detail, dIdx) => (
                                <div key={dIdx} style={{ background: 'rgba(99, 102, 241, 0.05)', border: '1px solid rgba(99, 102, 241, 0.15)', padding: '12px', borderRadius: '8px', fontSize: '13px' }}>
                                  <div style={{ display: 'flex', justifyContent: 'space-between', fontWeight: '700', color: '#a5b4fc', marginBottom: '4px' }}>
                                    <span>📜 {detail.name}</span>
                                    <span style={{ fontSize: '11px', background: 'rgba(255,255,255,0.05)', padding: '2px 6px', borderRadius: '4px' }}>{detail.citation}</span>
                                  </div>
                                  <div style={{ color: 'var(--text-secondary)', fontStyle: 'italic', lineHeight: '1.4' }}>
                                    "{detail.why_applies}"
                                  </div>
                                </div>
                              ))}
                              {(!pipelineResult.ai_trace.recommendation.policy_details || pipelineResult.ai_trace.recommendation.policy_details.length === 0) && (
                                <span style={{ color: 'var(--text-secondary)', fontSize: '13px' }}>No policy details available.</span>
                              )}
                            </div>
                          </div>
                          <div className="trace-item" style={{ gridColumn: '1 / -1' }}>
                            <span className="trace-item-label">Rationale</span>
                            <span className="trace-item-value" style={{ fontSize: '13px', color: 'var(--text-secondary)' }}>
                              {pipelineResult.ai_trace.recommendation.rationale}
                            </span>
                          </div>
                        </div>
                      </div>

                      {/* 5. WORKFLOW AGENT */}
                      <div className="trace-agent-card">
                        <div className="trace-agent-header">
                          <div className="trace-agent-icon-wrapper">
                            <Building2 size={14} />
                          </div>
                          <span className="trace-agent-name">Workflow Agent</span>
                          <span className="trace-agent-badge">Dispatched</span>
                        </div>
                        <div className="trace-grid">
                          <div className="trace-item">
                            <span className="trace-item-label">Assigned department</span>
                            <span className="trace-item-value" style={{ color: 'var(--success-color)' }}>
                              {pipelineResult.ai_trace.workflow.assigned_department}
                            </span>
                          </div>
                          <div className="trace-item">
                            <span className="trace-item-label">Task ID</span>
                            <span className="trace-item-value" style={{ fontFamily: 'monospace' }}>
                              {pipelineResult.ai_trace.workflow.task_id}
                            </span>
                          </div>
                          <div className="trace-item">
                            <span className="trace-item-label">Due date</span>
                            <span className="trace-item-value">
                              {new Date(pipelineResult.ai_trace.workflow.due_date).toLocaleString()}
                            </span>
                          </div>
                          <div className="trace-item">
                            <span className="trace-item-label">Status</span>
                            <span className="trace-item-value" style={{ textTransform: 'capitalize', color: 'var(--success-color)' }}>
                              {pipelineResult.ai_trace.workflow.status}
                            </span>
                          </div>
                        </div>
                      </div>

                    </div>
                  </div>
                )}
              </div>
            )}
          </div>
        )}

        {/* TAB 2: OFFICER DASHBOARD */}
        {activeTab === 'dashboard' && (
          <div>
            {/* Real-time Status Connection Badge */}
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '24px' }}>
              <span className={`step-bullet`} style={{ 
                background: dashboardStreamConnected ? 'var(--success-color)' : 'var(--error-color)',
                boxShadow: dashboardStreamConnected ? '0 0 8px var(--success-color)' : 'none',
                width: '10px', height: '10px'
              }} />
              <span style={{ fontSize: '13px', fontWeight: '600', color: 'var(--text-secondary)' }}>
                {dashboardStreamConnected ? 'Real-time task stream connected' : 'Stream disconnected'}
              </span>
            </div>

            {/* Dashboard Notifications Banner */}
            {dashboardNotifications.length > 0 && (
              <div style={{ marginBottom: '24px', display: 'flex', flexDirection: 'column', gap: '8px' }}>
                {dashboardNotifications.map(notif => (
                  <div key={notif.id} className="alert" style={{ background: 'rgba(99, 102, 241, 0.15)', borderColor: 'rgba(99, 102, 241, 0.25)', color: '#a5b4fc', display: 'flex', justifyContent: 'space-between', fontSize: '14px', margin: 0 }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                      <Sparkles size={16} />
                      <span>{notif.message}</span>
                    </div>
                    <span style={{ opacity: 0.7, fontSize: '12px' }}>{notif.timestamp}</span>
                  </div>
                ))}
              </div>
            )}

            {/* Command Center Dashboard V2 */}
            <div className="dashboard-v2-grid">
              {/* Left Main Column */}
              <div className="dashboard-v2-main">
                <div className="summary-grid" style={{ marginBottom: 0, display: 'grid', gridTemplateColumns: '1fr 1fr 1fr 1fr', gap: '16px' }}>
                  <div className="glass-panel metric-card" style={{ flex: 1 }}>
                    <div className="metric-icon">
                      <Activity />
                    </div>
                    <div className="metric-data" style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                        <h3>{dashboardData.health_score ? dashboardData.health_score.toFixed(1) : '82.5'}</h3>
                        {dashboardData.health_score_change && (
                          <span className={`health-trend ${dashboardData.health_score_change.startsWith('+') ? 'up' : 'down'}`}>
                            {dashboardData.health_score_change}
                          </span>
                        )}
                      </div>
                      <p>Community Health</p>
                    </div>
                  </div>
                  
                  <div className="glass-panel metric-card" style={{ flex: 1 }}>
                    <div className="metric-icon" style={{ color: 'var(--error-color)', background: 'rgba(239, 68, 68, 0.1)' }}>
                      <AlertTriangle />
                    </div>
                    <div className="metric-data">
                      <h3>{dashboardData.top_critical_issues ? dashboardData.top_critical_issues.length : 0}</h3>
                      <p>Critical Open Tasks</p>
                    </div>
                  </div>

                  <div className="glass-panel metric-card" style={{ flex: 1 }}>
                    <div className="metric-icon" style={{ color: 'var(--warning-color)', background: 'rgba(245, 158, 11, 0.1)' }}>
                      <Sparkles />
                    </div>
                    <div className="metric-data">
                      <h3>{dashboardData.sla_breach_risk || '14%'}</h3>
                      <p>SLA Breach Risk</p>
                    </div>
                  </div>

                  <div className="glass-panel metric-card" style={{ flex: 1 }}>
                    <div className="metric-icon" style={{ color: '#60a5fa', background: 'rgba(96, 165, 250, 0.1)' }}>
                      <Clock />
                    </div>
                    <div className="metric-data">
                      <h3>{dashboardData.avg_response_time || '2.4 hrs'}</h3>
                      <p>Avg Response Time</p>
                    </div>
                  </div>
                </div>

                {/* Critical Action Queue Table */}
                <div className="glass-panel">
                  <h3 style={{ fontSize: '20px', fontWeight: '700', marginBottom: '20px', display: 'flex', alignItems: 'center', gap: '8px' }}>
                    <AlertCircle size={20} color="var(--error-color)" /> Critical Action Queue
                  </h3>
                  
                  <div className="critical-list">
                    {dashboardData.top_critical_issues && dashboardData.top_critical_issues.map((issue, idx) => (
                      <div key={idx} className="critical-item">
                        <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
                          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                            <span style={{ fontSize: '12px', fontWeight: 'bold', color: 'var(--primary-color)' }}>
                              {issue.task_id || `TSK-${issue.id?.substring(0, 4).toUpperCase()}`}
                            </span>
                            <h5 style={{ fontWeight: '700', fontSize: '15px' }}>
                              {issue.desc ? (issue.desc.length > 50 ? `${issue.desc.substring(0, 50)}...` : issue.desc) : 'Critical Task'}
                            </h5>
                          </div>
                          <p style={{ fontSize: '13px', color: 'var(--text-secondary)' }}>
                            <MapPin size={12} style={{ display: 'inline', marginRight: '4px' }}/> Ward {issue.ward_id?.toUpperCase() || 'W1'} • Dept: {issue.department}
                            {issue.sla_due && (
                              <span style={{ color: 'var(--warning-color)', marginLeft: '8px', fontWeight: '600' }}>
                                • SLA: {Math.max(1, Math.floor((new Date(issue.sla_due) - new Date()) / (1000 * 60 * 60)))}h remaining
                              </span>
                            )}
                          </p>
                          {issue.estimated_impact && (
                            <p style={{ fontSize: '12px', color: '#a5b4fc', marginTop: '4px', display: 'flex', alignItems: 'center', gap: '4px' }}>
                              <Sparkles size={10} /> Impact: {issue.estimated_impact}
                            </p>
                          )}
                        </div>
                        
                        <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-end', gap: '8px' }}>
                          <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                            <span style={{ fontSize: '12px', fontWeight: 'bold', color: 'var(--text-secondary)', textTransform: 'uppercase' }}>
                              {issue.status || 'OPEN'}
                            </span>
                            <span className={`badge badge-${(issue.priority || 'high').toLowerCase()}`}>
                              {issue.priority || 'HIGH'}
                            </span>
                          </div>
                          <div style={{ display: 'flex', gap: '8px', marginTop: '4px' }}>
                            <button className="btn btn-primary" style={{ padding: '4px 10px', fontSize: '11px' }} onClick={async () => {
                              try {
                                await api.performTaskAction(issue.task_id, 'approve');
                                setOperationsFeed(prev => [
                                  {
                                    id: Math.random().toString(36).substring(7),
                                    time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
                                    text: `Officer approved task dispatch for ${issue.task_id}`,
                                    type: 'success'
                                  },
                                  ...prev
                                ]);
                                fetchDashboard();
                              } catch (err) {
                                alert(err.message || 'Action failed');
                              }
                            }}>Approve</button>
                            <button className="btn btn-secondary" style={{ padding: '4px 10px', fontSize: '11px' }} onClick={async () => {
                              try {
                                await api.performTaskAction(issue.task_id, 'escalate');
                                setOperationsFeed(prev => [
                                  {
                                    id: Math.random().toString(36).substring(7),
                                    time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
                                    text: `Task ${issue.task_id} escalated to supervisor`,
                                    type: 'warning'
                                  },
                                  ...prev
                                ]);
                                fetchDashboard();
                              } catch (err) {
                                alert(err.message || 'Action failed');
                              }
                            }}>Escalate</button>
                            <button className="btn btn-secondary" style={{ padding: '4px 10px', fontSize: '11px' }} onClick={async () => {
                              try {
                                await api.performTaskAction(issue.task_id, 'request_evidence');
                                setOperationsFeed(prev => [
                                  {
                                    id: Math.random().toString(36).substring(7),
                                    time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
                                    text: `Evidence requested from reporting citizen for task ${issue.task_id}`,
                                    type: 'info'
                                  },
                                  ...prev
                                ]);
                                fetchDashboard();
                              } catch (err) {
                                alert(err.message || 'Action failed');
                              }
                            }}>Request Evidence</button>
                          </div>
                        </div>
                      </div>
                    ))}

                    {(!dashboardData.top_critical_issues || dashboardData.top_critical_issues.length === 0) && (
                      <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', padding: '32px 0', color: 'var(--text-secondary)' }}>
                        <CheckCircle2 size={32} style={{ marginBottom: '8px', color: 'var(--success-color)' }} />
                        <p style={{ fontSize: '14px' }}>Action queue is clear.</p>
                      </div>
                    )}
                  </div>
                </div>
              </div>

              {/* Right Side Column */}
              <div className="dashboard-v2-side">
                {/* AI Insights Panel */}
                <div className="glass-panel" style={{ background: 'linear-gradient(180deg, rgba(22, 30, 49, 0.8) 0%, rgba(17, 24, 39, 0.95) 100%)' }}>
                  <h3 style={{ fontSize: '18px', fontWeight: '700', marginBottom: '16px', display: 'flex', alignItems: 'center', gap: '8px', color: '#a5b4fc' }}>
                    <Sparkles size={18} /> AI Insights
                  </h3>
                  <div>
                    {dashboardData.ai_insights && dashboardData.ai_insights.map((insight, idx) => (
                      <div key={idx} className="insight-card">
                        <Activity size={16} className="insight-icon" />
                        <span className="insight-text">{insight}</span>
                      </div>
                    ))}
                    {(!dashboardData.ai_insights || dashboardData.ai_insights.length === 0) && (
                      <p style={{ fontSize: '13px', color: 'var(--text-secondary)' }}>Gathering insights...</p>
                    )}
                  </div>
                </div>

                {/* Department Workloads */}
                {dashboardData.department_workload && dashboardData.department_workload.length > 0 && (
                  <div className="glass-panel">
                    <h3 style={{ fontSize: '18px', fontWeight: '700', marginBottom: '16px', display: 'flex', alignItems: 'center', gap: '8px' }}>
                      <Building2 size={18} /> Department Workload
                    </h3>
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
                      {dashboardData.department_workload.map((dept, idx) => (
                        <div key={idx} style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
                          <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '12px', fontWeight: '600' }}>
                            <span style={{ maxWidth: '170px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{dept.name}</span>
                            <span>{dept.workload}% ({dept.count} tasks)</span>
                          </div>
                          <div style={{ width: '100%', height: '6px', background: 'rgba(255,255,255,0.05)', borderRadius: '99px', overflow: 'hidden' }}>
                            <div style={{ 
                              width: `${dept.workload}%`, height: '100%', 
                              background: dept.workload > 80 ? 'var(--error-color)' : (dept.workload > 50 ? 'var(--warning-color)' : 'var(--success-color)')
                            }} />
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* Live Operations Feed */}
                <div className="glass-panel">
                  <h3 style={{ fontSize: '18px', fontWeight: '700', marginBottom: '16px', display: 'flex', alignItems: 'center', gap: '8px' }}>
                    <Clock size={18} /> Live Operations Feed
                  </h3>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '10px', maxHeight: '180px', overflowY: 'auto', paddingRight: '4px' }}>
                    {operationsFeed.map((feed) => (
                      <div key={feed.id} style={{ fontSize: '12px', borderLeft: '2px solid var(--border-color)', paddingLeft: '8px', display: 'flex', gap: '6px' }}>
                        <span style={{ opacity: 0.6, fontWeight: 'bold' }}>[{feed.time}]</span>
                        <span style={{ color: feed.type === 'success' ? '#34d399' : (feed.type === 'warning' ? '#fbbf24' : 'var(--text-primary)') }}>
                          {feed.text}
                        </span>
                      </div>
                    ))}
                  </div>
                </div>

                {/* Ward Risk Map */}
                <div className="glass-panel">
                  <h3 style={{ fontSize: '18px', fontWeight: '700', marginBottom: '16px' }}>Ward Risk Map</h3>
                  
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
                    {dashboardData.heatmap && dashboardData.heatmap.map((w, idx) => (
                      <div key={idx} style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
                        <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '13px', fontWeight: '600' }}>
                          <span>Ward {w.ward_id.toUpperCase()}</span>
                          <span>{(w.risk * 100).toFixed(0)}% Risk</span>
                        </div>
                        <div style={{ width: '100%', height: '8px', background: 'rgba(255,255,255,0.05)', borderRadius: '99px', overflow: 'hidden' }}>
                          <div style={{ 
                            width: `${w.risk * 100}%`, height: '100%', 
                            background: w.risk > 0.7 ? 'var(--error-color)' : (w.risk > 0.4 ? 'var(--warning-color)' : 'var(--success-color)')
                          }} />
                        </div>
                        {w.dominant_risk && (
                          <span style={{ fontSize: '11px', color: 'var(--text-secondary)', textTransform: 'uppercase' }}>
                            Dominant Risk: {w.dominant_risk}
                          </span>
                        )}
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* TAB 3: KNOWLEDGE BASE */}
        {activeTab === 'kb' && isAdmin && (
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 2fr', gap: '24px' }}>
            {/* Upload PDF Column */}
            <div className="glass-panel" style={{ height: 'fit-content' }}>
              <h3 style={{ fontSize: '20px', fontWeight: '700', marginBottom: '20px' }}>Upload Document</h3>
              
              <form onSubmit={handleFileUpload}>
                <div className="form-group">
                  <label className="form-label">Select PDF Policy Act</label>
                  <div style={{ border: '2px dashed var(--border-color)', borderRadius: '12px', padding: '24px', textAlign: 'center', position: 'relative', cursor: 'pointer', background: 'rgba(255,255,255,0.01)' }}>
                    <Upload size={32} style={{ margin: '0 auto 12px auto', color: 'var(--text-secondary)' }} />
                    <p style={{ fontSize: '14px', fontWeight: '500', color: 'var(--text-secondary)' }}>
                      {kbFile ? kbFile.name : 'Choose a PDF file...'}
                    </p>
                    <input 
                      type="file" 
                      id="kb-file-input"
                      accept=".pdf"
                      style={{ opacity: 0, position: 'absolute', top: 0, left: 0, right: 0, bottom: 0, cursor: 'pointer' }}
                      onChange={e => setKbFile(e.target.files[0])}
                      required
                    />
                  </div>
                </div>

                <button type="submit" className="btn btn-primary" style={{ width: '100%', marginTop: '12px' }} disabled={kbUploading || !kbFile}>
                  {kbUploading ? (
                    <>
                      <Loader2 className="spinner" style={{ marginRight: '8px' }} />
                      Ingesting Document...
                    </>
                  ) : 'Upload & Embed (768-dim)'}
                </button>
              </form>
            </div>

            {/* List Documents Column */}
            <div className="glass-panel">
              <h3 style={{ fontSize: '20px', fontWeight: '700', marginBottom: '20px' }}>Embedded Policy Documents</h3>
              
              <div className="kb-grid">
                {kbDocs.map((doc, idx) => (
                  <div key={idx} className="kb-card">
                    <div className="kb-card-info" style={{ overflow: 'hidden' }}>
                      <h5 title={doc.name}>
                        {doc.name}
                      </h5>
                      <span className="badge badge-low" style={{ display: 'inline-block', marginTop: '4px' }}>
                        {doc.status}
                      </span>
                    </div>
                    
                    <button onClick={() => handleDocDelete(doc.document_id)} className="delete-btn">
                      <Trash2 size={16} />
                    </button>
                  </div>
                ))}

                {kbDocs.length === 0 && (
                  <div style={{ gridColumn: '1 / -1', padding: '48px 0', textAlign: 'center', color: 'var(--text-secondary)' }}>
                    <FileText size={48} style={{ margin: '0 auto 12px auto', opacity: 0.5 }} />
                    <p style={{ fontSize: '15px' }}>No policy documents embedded yet.</p>
                  </div>
                )}
              </div>
            </div>
          </div>
        )}
      </main>
    </div>
  );
}
