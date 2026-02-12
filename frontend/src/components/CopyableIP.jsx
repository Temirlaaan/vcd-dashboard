import React, { useState, useRef, useEffect } from 'react';
import { Copy, CheckCircle } from 'lucide-react';
import './CopyableIP.css';

const CopyableIP = ({ ip }) => {
  const [copied, setCopied] = useState(false);
  const timerRef = useRef(null);

  useEffect(() => {
    return () => {
      if (timerRef.current) clearTimeout(timerRef.current);
    };
  }, []);

  const handleCopy = (e) => {
    e.stopPropagation();
    navigator.clipboard.writeText(ip)
      .then(() => {
        if (timerRef.current) clearTimeout(timerRef.current);
        setCopied(true);
        timerRef.current = setTimeout(() => setCopied(false), 1500);
      })
      .catch(err => console.error('Failed to copy:', err));
  };

  return (
    <span className={`copyable-ip ${copied ? 'copied' : ''}`} onClick={handleCopy} title="Click to copy">
      <span className="copyable-ip-text">{ip}</span>
      {copied ? (
        <CheckCircle className="copyable-ip-icon copied-icon" size={12} />
      ) : (
        <Copy className="copyable-ip-icon" size={12} />
      )}
    </span>
  );
};

export default CopyableIP;
