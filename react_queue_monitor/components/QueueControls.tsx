/**
 * Queue Controls Component
 * 
 * Provides controls for queue operations (start, stop, pause, clear, etc.),
 * equivalent to QtReQueueControls in the Qt version.
 */

import React, { useState } from 'react';
import { ManagerStatus } from '../types/queueServerTypes';

interface QueueControlsProps {
  status: ManagerStatus | null;
  onStartQueue: (lockKey?: string) => Promise<void>;
  onStopQueue: (lockKey?: string) => Promise<void>;
  onPauseQueue: (lockKey?: string) => Promise<void>;
  onResumeQueue: (lockKey?: string) => Promise<void>;
  onClearQueue: (lockKey?: string) => Promise<void>;
  onHaltQueue: (lockKey?: string) => Promise<void>;
  disabled?: boolean;
}

export const QueueControls: React.FC<QueueControlsProps> = ({
  status,
  onStartQueue,
  onStopQueue,
  onPauseQueue,
  onResumeQueue,
  onClearQueue,
  onHaltQueue,
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

  const getButtonStyle = (variant: 'primary' | 'secondary' | 'danger' | 'warning' = 'secondary') => {
    const baseStyle = {
      padding: '6px 12px',
      fontSize: '12px',
      fontWeight: 'bold' as const,
      border: 'none',
      borderRadius: '4px',
      cursor: disabled ? 'not-allowed' : 'pointer',
      opacity: disabled ? 0.6 : 1,
      minWidth: '70px',
      height: '32px'
    };

    const variants = {
      primary: { backgroundColor: '#007bff', color: '#fff' },
      secondary: { backgroundColor: '#6c757d', color: '#fff' },
      danger: { backgroundColor: '#dc3545', color: '#fff' },
      warning: { backgroundColor: '#ffc107', color: '#212529' }
    };

    return { ...baseStyle, ...variants[variant] };
  };

  const isExecuting = status?.manager_state === 'executing_queue';
  const isPaused = status?.manager_state === 'paused';
  const hasItems = (status?.items_in_queue || 0) > 0;
  const environmentExists = status?.worker_environment_exists || false;

  return (
    <div className="queue-controls" style={{
      padding: '12px',
      border: '1px solid #ddd',
      borderRadius: '6px',
      backgroundColor: '#f8f9fa'
    }}>
      <h6 style={{ margin: '0 0 12px 0', fontWeight: 'bold' }}>Queue Controls</h6>
      
      <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px' }}>
        {/* Start Queue */}
        <button
          style={getButtonStyle('primary')}
          onClick={() => handleAction('start queue', onStartQueue)}
          disabled={disabled || loading !== null || isExecuting || !hasItems || !environmentExists}
          title={
            !environmentExists ? 'Environment must be open' :
            !hasItems ? 'No items in queue' :
            isExecuting ? 'Queue is already running' :
            'Start executing the queue'
          }
        >
          {loading === 'start queue' ? '...' : '▶ Start'}
        </button>

        {/* Stop Queue */}
        <button
          style={getButtonStyle('secondary')}
          onClick={() => handleAction('stop queue', onStopQueue)}
          disabled={disabled || loading !== null || !isExecuting}
          title={isExecuting ? 'Stop queue execution after current plan' : 'Queue is not running'}
        >
          {loading === 'stop queue' ? '...' : '⏹ Stop'}
        </button>

        {/* Pause/Resume Queue */}
        {isPaused ? (
          <button
            style={getButtonStyle('warning')}
            onClick={() => handleAction('resume queue', onResumeQueue)}
            disabled={disabled || loading !== null}
            title="Resume paused queue"
          >
            {loading === 'resume queue' ? '...' : '▶ Resume'}
          </button>
        ) : (
          <button
            style={getButtonStyle('warning')}
            onClick={() => handleAction('pause queue', onPauseQueue)}
            disabled={disabled || loading !== null || !isExecuting}
            title={isExecuting ? 'Pause queue execution' : 'Queue is not running'}
          >
            {loading === 'pause queue' ? '...' : '⏸ Pause'}
          </button>
        )}

        {/* Halt Queue */}
        <button
          style={getButtonStyle('danger')}
          onClick={() => {
            if (window.confirm('Halt will immediately stop queue execution. Continue?')) {
              handleAction('halt queue', onHaltQueue);
            }
          }}
          disabled={disabled || loading !== null || !isExecuting}
          title={isExecuting ? 'Immediately halt queue execution' : 'Queue is not running'}
        >
          {loading === 'halt queue' ? '...' : '🛑 Halt'}
        </button>

        {/* Clear Queue */}
        <button
          style={getButtonStyle('danger')}
          onClick={() => {
            if (window.confirm(`Clear all ${status?.items_in_queue || 0} items from queue?`)) {
              handleAction('clear queue', onClearQueue);
            }
          }}
          disabled={disabled || loading !== null || !hasItems || isExecuting}
          title={
            isExecuting ? 'Cannot clear queue while executing' :
            !hasItems ? 'Queue is already empty' :
            'Remove all items from queue'
          }
        >
          {loading === 'clear queue' ? '...' : '🗑 Clear'}
        </button>
      </div>

      {/* Queue Status Info */}
      <div style={{ 
        marginTop: '8px', 
        fontSize: '11px', 
        color: '#6c757d',
        display: 'flex',
        justifiContent: 'space-between'
      }}>
        <span>Items: {status?.items_in_queue || 0}</span>
        <span>State: {status?.manager_state || 'unknown'}</span>
        {status?.queue_stop_pending && (
          <span style={{ color: '#ffc107' }}>Stop Pending</span>
        )}
        {status?.queue_autostart_enabled && (
          <span style={{ color: '#28a745' }}>Autostart</span>
        )}
      </div>
    </div>
  );
};

export default QueueControls;
