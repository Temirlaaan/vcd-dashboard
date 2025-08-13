import React from 'react';
import { AlertCircle, RefreshCw } from 'lucide-react';
import './ErrorMessage.css';

const ErrorMessage = ({ message, onRetry }) => {
  return (
    <div className="error-container">
      <div className="error-box">
        <AlertCircle className="error-icon" />
        <h2>Oops! Something went wrong</h2>
        <p>{message}</p>
        <button className="retry-button" onClick={onRetry}>
          <RefreshCw />
          Try Again
        </button>
      </div>
    </div>
  );
};

export default ErrorMessage;