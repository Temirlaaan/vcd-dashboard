// frontend/src/components/Login.jsx
import React, { useState } from 'react';
import { Lock, User, AlertCircle, Eye, EyeOff } from 'lucide-react';

const Login = ({ onLogin }) => {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setLoading(true);

    // Определяем правильный URL для backend
    const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';
    const loginUrl = `${API_BASE_URL}/api/login`;
    
    console.log('🔐 Attempting login...');
    console.log('📍 Backend URL:', loginUrl);
    console.log('👤 Username:', username);

    try {
      const response = await fetch(loginUrl, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ username, password }),
      });

      console.log('📥 Response status:', response.status);

      const data = await response.json();
      console.log('📦 Response data:', data);

      if (response.ok) {
        console.log('✅ Login successful!');
        localStorage.setItem('token', data.access_token);
        onLogin(data.access_token);
      } else {
        console.log('❌ Login failed:', data.detail);
        setError(data.detail || 'Invalid credentials');
      }
    } catch (err) {
      console.error('🚫 Connection error:', err);
      setError(`Connection error: ${err.message}. Backend may not be running on ${API_BASE_URL}`);
    } finally {
      setLoading(false);
    }
  };

  // Стили компонента (оставляем как было)
  const styles = {
    container: {
      minHeight: '100vh',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
      padding: '20px',
    },
    loginBox: {
      background: 'white',
      borderRadius: '20px',
      padding: '40px',
      width: '100%',
      maxWidth: '400px',
      boxShadow: '0 20px 60px rgba(0,0,0,0.3)',
    },
    logo: {
      display: 'flex',
      justifyContent: 'center',
      marginBottom: '30px',
    },
    logoIcon: {
      width: '60px',
      height: '60px',
      padding: '15px',
      background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
      borderRadius: '15px',
      color: 'white',
    },
    title: {
      textAlign: 'center',
      marginBottom: '10px',
      fontSize: '28px',
      fontWeight: '600',
      color: '#1e293b',
    },
    subtitle: {
      textAlign: 'center',
      marginBottom: '30px',
      fontSize: '14px',
      color: '#64748b',
    },
    form: {
      display: 'flex',
      flexDirection: 'column',
      gap: '20px',
    },
    inputGroup: {
      position: 'relative',
    },
    inputIcon: {
      position: 'absolute',
      left: '15px',
      top: '50%',
      transform: 'translateY(-50%)',
      width: '20px',
      height: '20px',
      color: '#94a3b8',
    },
    input: {
      width: '100%',
      padding: '12px 15px 12px 45px',
      border: '2px solid #e2e8f0',
      borderRadius: '10px',
      fontSize: '15px',
      transition: 'all 0.3s ease',
      outline: 'none',
    },
    passwordToggle: {
      position: 'absolute',
      right: '15px',
      top: '50%',
      transform: 'translateY(-50%)',
      background: 'none',
      border: 'none',
      cursor: 'pointer',
      padding: '5px',
      color: '#94a3b8',
      transition: 'color 0.2s',
    },
    errorBox: {
      background: '#fef2f2',
      border: '1px solid #fecaca',
      borderRadius: '8px',
      padding: '12px',
      display: 'flex',
      alignItems: 'flex-start',
      gap: '10px',
      color: '#dc2626',
      fontSize: '14px',
      maxHeight: '150px',
      overflow: 'auto',
    },
    errorIcon: {
      width: '18px',
      height: '18px',
      flexShrink: '0',
      marginTop: '2px',
    },
    errorText: {
      flex: 1,
      wordBreak: 'break-word',
    },
    submitButton: {
      background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
      color: 'white',
      border: 'none',
      borderRadius: '10px',
      padding: '14px',
      fontSize: '16px',
      fontWeight: '600',
      cursor: 'pointer',
      transition: 'all 0.3s ease',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      gap: '10px',
    },
    submitButtonDisabled: {
      opacity: '0.6',
      cursor: 'not-allowed',
    },
    lockIcon: {
      width: '18px',
      height: '18px',
    },
    footer: {
      marginTop: '30px',
      textAlign: 'center',
      fontSize: '13px',
      color: '#94a3b8',
    },
    debugInfo: {
      marginTop: '20px',
      padding: '10px',
      background: '#f3f4f6',
      borderRadius: '8px',
      fontSize: '12px',
      color: '#6b7280',
    },
  };

  return (
    <div style={styles.container}>
      <div style={styles.loginBox}>
        <div style={styles.logo}>
          <Lock style={styles.logoIcon} />
        </div>
        
        <h1 style={styles.title}>VCD IP Manager</h1>
        <p style={styles.subtitle}>Sign in to access the dashboard</p>
        
        <form style={styles.form} onSubmit={handleSubmit}>
          <div style={styles.inputGroup}>
            <User style={styles.inputIcon} />
            <input
              type="text"
              placeholder="Username"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              style={styles.input}
              onFocus={(e) => e.target.style.borderColor = '#667eea'}
              onBlur={(e) => e.target.style.borderColor = '#e2e8f0'}
              required
              disabled={loading}
            />
          </div>
          
          <div style={styles.inputGroup}>
            <Lock style={styles.inputIcon} />
            <input
              type={showPassword ? 'text' : 'password'}
              placeholder="Password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              style={styles.input}
              onFocus={(e) => e.target.style.borderColor = '#667eea'}
              onBlur={(e) => e.target.style.borderColor = '#e2e8f0'}
              required
              disabled={loading}
            />
            <button
              type="button"
              style={styles.passwordToggle}
              onClick={() => setShowPassword(!showPassword)}
              tabIndex={-1}
            >
              {showPassword ? <EyeOff size={20} /> : <Eye size={20} />}
            </button>
          </div>
          
          {error && (
            <div style={styles.errorBox}>
              <AlertCircle style={styles.errorIcon} />
              <div style={styles.errorText}>{error}</div>
            </div>
          )}
          
          <button
            type="submit"
            style={{
              ...styles.submitButton,
              ...(loading ? styles.submitButtonDisabled : {})
            }}
            disabled={loading}
          >
            <Lock style={styles.lockIcon} />
            {loading ? 'Signing in...' : 'Sign In'}
          </button>
        </form>
        
        <div style={styles.footer}>
          <p>VMware vCloud Director IP Management System</p>
        </div>
        
        {/* Debug информация */}
        <div style={styles.debugInfo}>
          <strong>Debug Info:</strong><br/>
          Backend URL: {process.env.REACT_APP_API_URL || 'http://localhost:8000'}<br/>
          Frontend Port: {window.location.port || '80'}<br/>
          Check console (F12) for detailed logs
        </div>
      </div>
    </div>
  );
};

export default Login;