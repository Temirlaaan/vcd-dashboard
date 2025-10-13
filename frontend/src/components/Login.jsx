// frontend/src/components/Login.jsx
import React, { useState } from 'react';
import { Lock, AlertCircle } from 'lucide-react';

const Login = ({ onLogin }) => {
  const [error, setError] = useState('');

  const handleKeycloakLogin = () => {
    setError('');
    try {
      // Получаем конфиг из env или hardcoded (рекомендую добавить в .env: REACT_APP_KEYCLOAK_URL, etc.)
      const keycloakUrl = process.env.REACT_APP_KEYCLOAK_URL || 'https://sso-ttc.t-cloud.kz';
      const realm = process.env.REACT_APP_KEYCLOAK_REALM || 'prod-v1';
      const clientId = process.env.REACT_APP_KEYCLOAK_CLIENT_ID || 'vcd-ip-manager';
      const redirectUri = encodeURIComponent(`${window.location.origin}/callback`);  // Динамический redirect

      const authUrl = `${keycloakUrl}/realms/${realm}/protocol/openid-connect/auth?client_id=${clientId}&redirect_uri=${redirectUri}&response_type=code&scope=openid profile email`;
      
      console.log('Redirecting to Keycloak:', authUrl);
      window.location.href = authUrl;  // Редирект на Keycloak login page
    } catch (err) {
      setError('Failed to initiate login. Please try again.');
      console.error('Keycloak redirect error:', err);
    }
  };

  // Стили (вставьте ваши стили из оригинала, упростил без password/username inputs)
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
      width: '100%', // Ensure it spans the full width of the parent
      display: 'block', // Ensure it's a block element for consistent centering
      marginLeft: 'auto', // Explicitly center horizontally
      marginRight: 'auto',
    },
    form: {
      display: 'flex',
      flexDirection: 'column',
      gap: '20px',
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
    footer: {
      marginTop: '30px',
      textAlign: 'center',
      fontSize: '13px',
      color: '#94a3b8',
    },
  };

  return (
    <div style={styles.container}>
      <div style={styles.loginBox}>
        <div style={styles.logo}>
          <Lock style={styles.logoIcon} />
        </div>
        
        <h1 style={styles.title}>VCD IP Manager</h1>
        <p style={styles.subtitle}>Sign in with Keycloak to access the dashboard</p>
        
        {error && (
          <div style={styles.errorBox}>
            <AlertCircle style={styles.errorIcon} />
            <div style={styles.errorText}>{error}</div>
          </div>
        )}
        
        <button
          type="button"
          style={styles.submitButton}
          onClick={handleKeycloakLogin}
        >
          <Lock style={styles.lockIcon} />
          Sign In with Keycloak
        </button>
        
        <div style={styles.footer}>
          <p>VMware vCloud Director IP Management System</p>
        </div>
      </div>
    </div>
  );
};

export default Login;