// frontend/src/components/ConflictAlert.jsx
import React from 'react';
import { AlertTriangle, X, Globe, Server } from 'lucide-react';
import CopyableIP from './CopyableIP';
import './ConflictAlert.css';

const ConflictAlert = ({ conflicts, onClose }) => {
  const conflictEntries = Object.entries(conflicts);
  
  return (
    <div className="conflict-alert">
      <div className="conflict-header">
        <div className="conflict-title">
          <AlertTriangle className="conflict-icon" />
          <h3>Обнаружены конфликты IP адресов</h3>
        </div>
        <button className="close-button" onClick={onClose}>
          <X />
        </button>
      </div>
      
      <div className="conflict-description">
        <p>
          Следующие IP адреса используются одновременно в нескольких облаках. 
          Это может привести к проблемам с маршрутизацией и доступностью сервисов.
        </p>
      </div>
      
      <div className="conflicts-list">
        {conflictEntries.map(([ip, conflictList]) => (
          <div key={ip} className="conflict-item">
            <div className="conflict-ip">
              <Server className="ip-icon" />
              <CopyableIP ip={ip} />
            </div>
            
            {conflictList.map((conflict, idx) => (
              <div key={idx} className="conflict-details">
                <div className="conflict-clouds">
                  <Globe className="detail-icon" />
                  <span className="label">Облака:</span>
                  <div className="cloud-badges">
                    {conflict.clouds.map(cloud => (
                      <span key={cloud} className="cloud-badge">{cloud.toUpperCase()}</span>
                    ))}
                  </div>
                </div>
                
                <div className="conflict-orgs">
                  <span className="label">Организации:</span>
                  <span className="value">{conflict.organizations.join(', ')}</span>
                </div>
                
                <div className="conflict-pools">
                  <span className="label">Пулы:</span>
                  <span className="value">{conflict.pools.join(', ')}</span>
                </div>
              </div>
            ))}
          </div>
        ))}
      </div>
      
      <div className="conflict-footer">
        <p className="warning-text">
          ⚠️ Рекомендуется срочно устранить конфликты для предотвращения проблем с сетью.
        </p>
      </div>
    </div>
  );
};

export default ConflictAlert;