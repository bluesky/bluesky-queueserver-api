/**
 * Execution Controls Component
 * 
 * Provides controls for managing plan execution (stop, abort, pause, resume),
 * equivalent to QtReExecutionControls in the Qt version.
 */

import React, { useState } from 'react';
import { ManagerStatus, RunningPlan } from '../types/queueServerTypes';

interface ExecutionControlsProps {
  status: ManagerStatus | null;
  runningPlan: RunningPlan | null;
  onStopPlan: (lockKey?: string) => Promise<void>;
  onAbortPlan: (lockKey?: string) => Promise<void>;
  onHaltPlan: (lockKey?: string) => Promise<void>;
  onPausePlan: (option?: string, lockKey?: string) => Promise<void>;
  onResumePlan: (lockKey?: string) => Promise<void>;
  disabled?: boolean;
}

export const ExecutionControls: React.FC<ExecutionControlsProps> = ({
  status,
  runningPlan,
  onStopPlan,
  onAbortPlan,
  onHaltPlan,
  onPausePlan,
  onResumePlan,
  disabled = false
}) => {
  const [loading, setLoading] = useState<string | null>(null);
  const [pauseOption, setPauseOption] = useState<string>('deferred');

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

  const isExecuting = status?.worker_environment_state === 'executing_plan';
  const isPaused = status?.re_state === 'paused';
  const canControl = isExecuting || isPaused;

  return (
    <div className="execution-controls" style={{
      padding: '12px',
      border: '1px solid #ddd',
      borderRadius: '6px',
      backgroundColor: '#f8f9fa'
    }}>
      <h6 style={{ margin: '0 0 12px 0', fontWeight: 'bold' }}>Execution Controls</h6>
      
      {/* Plan Control Buttons */}
      <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px', marginBottom: '12px' }}>
        {/* Stop Plan */}
        <button
          style={getButtonStyle('secondary')}
          onClick={() => handleAction('stop plan', onStopPlan)}
          disabled={disabled || loading !== null || !isExecuting}
          title={isExecuting ? 'Stop plan after current step' : 'No plan is executing'}
        >
          {loading === 'stop plan' ? '...' : '⏹ Stop'}
        </button>

        {/* Abort Plan */}
        <button
          style={getButtonStyle('danger')}
          onClick={() => {
            if (window.confirm('Abort will immediately terminate the current plan. Continue?')) {
              handleAction('abort plan', onAbortPlan);
            }
          }}
          disabled={disabled || loading !== null || !isExecuting}
          title={isExecuting ? 'Immediately abort current plan' : 'No plan is executing'}
        >
          {loading === 'abort plan' ? '...' : '🛑 Abort'}
        </button>

        {/* Halt Plan */}
        <button
          style={getButtonStyle('danger')}
          onClick={() => {
            if (window.confirm('Halt will immediately stop all execution. Continue?')) {
              handleAction('halt plan', onHaltPlan);
            }
          }}
          disabled={disabled || loading !== null || !canControl}
          title={canControl ? 'Immediately halt all execution' : 'No plan is executing'}
        >
          {loading === 'halt plan' ? '...' : '🚫 Halt'}
        </button>

        {/* Pause/Resume */}
        {isPaused ? (
          <button
            style={getButtonStyle('primary')}
            onClick={() => handleAction('resume plan', onResumePlan)}
            disabled={disabled || loading !== null}
            title="Resume paused plan"
          >
            {loading === 'resume plan' ? '...' : '▶ Resume'}
          </button>
        ) : (
          <button
            style={getButtonStyle('warning')}
            onClick={() => handleAction('pause plan', () => onPausePlan(pauseOption))}
            disabled={disabled || loading !== null || !isExecuting}
            title={isExecuting ? 'Pause current plan' : 'No plan is executing'}
          >
            {loading === 'pause plan' ? '...' : '⏸ Pause'}
          </button>
        )}
      </div>

      {/* Pause Options */}
      {isExecuting && (
        <div style={{
          marginBottom: '12px',
          padding: '8px',
          backgroundColor: '#e9ecef',
          borderRadius: '4px'
        }}>
          <div style={{ fontSize: '12px', fontWeight: 'bold', marginBottom: '6px' }}>
            Pause Option:
          </div>
          <div style={{ display: 'flex', gap: '12px', fontSize: '11px' }}>
            <label style={{ display: 'flex', alignItems: 'center', cursor: 'pointer' }}>
              <input
                type="radio"
                value="deferred"
                checked={pauseOption === 'deferred'}
                onChange={(e) => setPauseOption(e.target.value)}
                style={{ marginRight: '4px' }}
              />
              Deferred (after current step)
            </label>
            <label style={{ display: 'flex', alignItems: 'center', cursor: 'pointer' }}>
              <input
                type="radio"
                value="immediate"
                checked={pauseOption === 'immediate'}
                onChange={(e) => setPauseOption(e.target.value)}
                style={{ marginRight: '4px' }}
              />
              Immediate
            </label>
          </div>
        </div>
      )}

      {/* Current Plan Info */}
      {runningPlan && (
        <div style={{
          padding: '8px',
          backgroundColor: '#d1ecf1',
          borderRadius: '4px',
          fontSize: '12px'
        }}>
          <div style={{ fontWeight: 'bold', marginBottom: '4px' }}>
            Executing: {runningPlan.name}
          </div>
          <div style={{ color: '#0c5460' }}>
            User: {runningPlan.user} | 
            Scan ID: {runningPlan.scan_id || 'N/A'} |
            UID: {runningPlan.item_uid.slice(0, 8)}...
          </div>
        </div>
      )}

      {/* Execution Status */}
      <div style={{
        marginTop: '8px',
        fontSize: '11px',
        color: '#6c757d',
        display: 'flex',
        justifyContent: 'space-between'
      }}>
        <span>Environment: {status?.worker_environment_state || 'unknown'}</span>
        {status?.re_state && (
          <span>RE State: {status.re_state}</span>
        )}
      </div>

      {/* Status indicators */}
      {isPaused && (
        <div style={{
          marginTop: '8px',
          padding: '6px',
          backgroundColor: '#fff3cd',
          borderRadius: '4px',
          fontSize: '11px',
          color: '#856404'
        }}>
          ⏸️ Plan execution is paused
        </div>
      )}
    </div>
  );
};

export default ExecutionControls;
