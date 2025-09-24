/**
 * Environment Controls Component
 * 
 * Provides controls for managing the Run Engine environment,
 * equivalent to QtReEnvironmentControls in the Qt version.
 */

import React, { useState } from 'react';
import { ManagerStatus } from '../types/queueServerTypes';

interface EnvironmentControlsProps {
  status: ManagerStatus | null;
  onOpenEnvironment: (lockKey?: string) => Promise<void>;
  onCloseEnvironment: (lockKey?: string) => Promise<void>;
  onDestroyEnvironment: (lockKey?: string) => Promise<void>;
  disabled?: boolean;
}

export const EnvironmentControls: React.FC<EnvironmentControlsProps> = ({
  status,
  onOpenEnvironment,
  onCloseEnvironment,
  onDestroyEnvironment,
  disabled = false
}) => {
  const [loading, setLoading] = useState<string | null>(null);

  const handleAction = async (action: string, actionFn: () => Promise<void>) => {
    if (loading) return;
    
    setLoading(action);
    try {
      await actionFn();
    } catch (error) {
      console.error(`Failed to ${action}:`, error);
      alert(`Failed to ${action}: ${error}`);
    } finally {
      setLoading(null);
    }
  };

  const getButtonStyle = (variant: 'primary' | 'secondary' | 'danger' = 'secondary') => {
    const baseStyle = {
      padding: '6px 12px',
      fontSize: '12px',
      fontWeight: 'bold' as const,
      border: 'none',
      borderRadius: '4px',
      cursor: disabled ? 'not-allowed' : 'pointer',
      opacity: disabled ? 0.6 : 1,
      minWidth: '80px',
      height: '32px'
    };

    const variants = {
      primary: { backgroundColor: '#28a745', color: '#fff' },
      secondary: { backgroundColor: '#6c757d', color: '#fff' },
      danger: { backgroundColor: '#dc3545', color: '#fff' }
    };

    return { ...baseStyle, ...variants[variant] };
  };

  const environmentExists = status?.worker_environment_exists || false;
  const environmentState = status?.worker_environment_state || 'closed';
  const isExecuting = status?.manager_state === 'executing_queue';
  const isClosing = status?.manager_state === 'closing_environment';
  const isDestroying = status?.manager_state === 'destroying_environment';

  return (
    <div className="environment-controls" style={{
      padding: '12px',
      border: '1px solid #ddd',
      borderRadius: '6px',
      backgroundColor: '#f8f9fa'
    }}>
      <h6 style={{ margin: '0 0 12px 0', fontWeight: 'bold' }}>Environment Controls</h6>
      
      <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px' }}>
        {/* Open Environment */}
        <button
          style={getButtonStyle('primary')}
          onClick={() => handleAction('open environment', onOpenEnvironment)}
          disabled={disabled || loading !== null || environmentExists}
          title={
            environmentExists ? 'Environment is already open' : 'Open the Run Engine environment'
          }
        >
          {loading === 'open environment' ? '...' : '🔓 Open'}
        </button>

        {/* Close Environment */}
        <button
          style={getButtonStyle('secondary')}
          onClick={() => handleAction('close environment', onCloseEnvironment)}
          disabled={disabled || loading !== null || !environmentExists || isExecuting || isClosing}
          title={
            !environmentExists ? 'Environment is not open' :
            isExecuting ? 'Cannot close while executing plans' :
            isClosing ? 'Environment is already closing' :
            'Close the Run Engine environment'
          }
        >
          {loading === 'close environment' ? '...' : '🔒 Close'}
        </button>

        {/* Destroy Environment */}
        <button
          style={getButtonStyle('danger')}
          onClick={() => {
            if (window.confirm('Destroy will forcibly terminate the environment. Continue?')) {
              handleAction('destroy environment', onDestroyEnvironment);
            }
          }}
          disabled={disabled || loading !== null || !environmentExists || isDestroying}
          title={
            !environmentExists ? 'Environment is not open' :
            isDestroying ? 'Environment is already being destroyed' :
            'Forcibly destroy the Run Engine environment'
          }
        >
          {loading === 'destroy environment' ? '...' : '💥 Destroy'}
        </button>
      </div>

      {/* Environment Status Info */}
      <div style={{ 
        marginTop: '12px',
        padding: '8px',
        backgroundColor: environmentExists ? '#d4edda' : '#f8d7da',
        borderRadius: '4px',
        fontSize: '12px'
      }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '4px' }}>
          <span style={{ fontWeight: 'bold' }}>Environment Status:</span>
          <span style={{ 
            color: environmentExists ? '#155724' : '#721c24',
            fontWeight: 'bold'
          }}>
            {environmentExists ? 'OPEN' : 'CLOSED'}
          </span>
        </div>
        
        {environmentExists && (
          <div style={{ display: 'flex', justifyContent: 'space-between' }}>
            <span>State:</span>
            <span style={{ 
              color: environmentState === 'idle' ? '#155724' : '#856404',
              fontWeight: 'bold'
            }}>
              {environmentState.toUpperCase()}
            </span>
          </div>
        )}

        {status?.re_state && (
          <div style={{ display: 'flex', justifyContent: 'space-between' }}>
            <span>RE State:</span>
            <span>{status.re_state}</span>
          </div>
        )}
      </div>

      {/* Warning for destructive operations */}
      {(isClosing || isDestroying) && (
        <div style={{
          marginTop: '8px',
          padding: '6px',
          backgroundColor: '#fff3cd',
          borderRadius: '4px',
          fontSize: '11px',
          color: '#856404'
        }}>
          ⚠️ {isClosing ? 'Closing environment...' : 'Destroying environment...'}
        </div>
      )}
    </div>
  );
};

export default EnvironmentControls;
