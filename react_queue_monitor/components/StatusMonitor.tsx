/**
 * Status Monitor Component
 * 
 * Displays the current status of the Queue Server manager and environment,
 * equivalent to QtReStatusMonitor in the Qt version.
 */

import React from 'react';
import { ManagerStatus } from '../types/queueServerTypes';

interface StatusMonitorProps {
  status: ManagerStatus | null;
  connected: boolean;
  error: string | null;
}

export const StatusMonitor: React.FC<StatusMonitorProps> = ({ status, connected, error }) => {
  const getStatusColor = (state: string) => {
    switch (state) {
      case 'idle': return '#28a745'; // green
      case 'executing_queue': return '#007bff'; // blue  
      case 'paused': return '#ffc107'; // yellow
      case 'closing_environment':
      case 'destroying_environment': return '#fd7e14'; // orange
      default: return '#6c757d'; // gray
    }
  };

  const getEnvironmentColor = (state: string, exists: boolean) => {
    if (!exists) return '#dc3545'; // red
    switch (state) {
      case 'idle': return '#28a745'; // green
      case 'executing_plan': return '#007bff'; // blue
      case 'executing_task': return '#17a2b8'; // cyan
      default: return '#6c757d'; // gray
    }
  };

  return (
    <div className="status-monitor" style={{
      padding: '12px',
      border: '1px solid #ddd',
      borderRadius: '6px',
      backgroundColor: '#f8f9fa',
      minWidth: '300px'
    }}>
      <h6 style={{ margin: '0 0 10px 0', fontWeight: 'bold' }}>Queue Server Status</h6>
      
      {/* Connection Status */}
      <div style={{ marginBottom: '8px' }}>
        <span style={{
          display: 'inline-block',
          width: '12px',
          height: '12px',
          borderRadius: '50%',
          backgroundColor: connected ? '#28a745' : '#dc3545',
          marginRight: '8px'
        }}></span>
        <span style={{ fontSize: '14px' }}>
          {connected ? 'Connected' : 'Disconnected'}
        </span>
        {error && (
          <div style={{ color: '#dc3545', fontSize: '12px', marginTop: '4px' }}>
            {error}
          </div>
        )}
      </div>

      {status && (
        <>
          {/* Manager Status */}
          <div style={{ marginBottom: '8px' }}>
            <span style={{ fontSize: '14px', fontWeight: '500' }}>Manager: </span>
            <span style={{
              color: getStatusColor(status.manager_state),
              fontWeight: 'bold',
              fontSize: '14px'
            }}>
              {status.manager_state.replace('_', ' ').toUpperCase()}
            </span>
          </div>

          {/* Environment Status */}
          <div style={{ marginBottom: '8px' }}>
            <span style={{ fontSize: '14px', fontWeight: '500' }}>Environment: </span>
            <span style={{
              color: getEnvironmentColor(status.worker_environment_state, status.worker_environment_exists),
              fontWeight: 'bold',
              fontSize: '14px'
            }}>
              {status.worker_environment_exists 
                ? status.worker_environment_state.replace('_', ' ').toUpperCase()
                : 'CLOSED'
              }
            </span>
          </div>

          {/* Queue Info */}
          <div style={{ fontSize: '13px', color: '#6c757d' }}>
            <div>Queue Items: {status.items_in_queue}</div>
            <div>History Items: {status.items_in_history}</div>
            {status.queue_autostart_enabled && (
              <div style={{ color: '#007bff' }}>Autostart: ON</div>
            )}
            {status.queue_stop_pending && (
              <div style={{ color: '#ffc107' }}>Stop Pending</div>
            )}
          </div>

          {status.msg && (
            <div style={{
              marginTop: '8px',
              padding: '6px',
              backgroundColor: '#e9ecef',
              borderRadius: '4px',
              fontSize: '12px',
              color: '#495057'
            }}>
              {status.msg}
            </div>
          )}
        </>
      )}
    </div>
  );
};

export default StatusMonitor;
