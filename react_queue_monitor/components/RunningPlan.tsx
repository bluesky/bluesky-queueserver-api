/**
 * Running Plan Component
 * 
 * Displays the currently executing plan with progress information,
 * equivalent to QtReRunningPlan in the Qt version.
 */

import React from 'react';
import { RunningPlan } from '../types/queueServerTypes';

interface RunningPlanProps {
  runningPlan: RunningPlan | null;
  executionStatus?: any; // Could be extended with more specific typing
}

export const RunningPlanComponent: React.FC<RunningPlanProps> = ({ 
  runningPlan, 
  executionStatus 
}) => {
  const formatArgs = (args: any[]): string => {
    if (!args || args.length === 0) return '';
    return args.map(arg => 
      typeof arg === 'string' ? `"${arg}"` : JSON.stringify(arg)
    ).join(', ');
  };

  const formatKwargs = (kwargs: Record<string, any>): string => {
    if (!kwargs || Object.keys(kwargs).length === 0) return '';
    return Object.entries(kwargs)
      .map(([key, value]) => `${key}=${JSON.stringify(value)}`)
      .join(', ');
  };

  const formatTime = (timeStr: string | null): string => {
    if (!timeStr) return 'N/A';
    try {
      return new Date(timeStr).toLocaleTimeString();
    } catch {
      return timeStr;
    }
  };

  const getElapsedTime = (startTime: string | null): string => {
    if (!startTime) return 'N/A';
    try {
      const start = new Date(startTime);
      const now = new Date();
      const elapsed = Math.floor((now.getTime() - start.getTime()) / 1000);
      const minutes = Math.floor(elapsed / 60);
      const seconds = elapsed % 60;
      return `${minutes}:${seconds.toString().padStart(2, '0')}`;
    } catch {
      return 'N/A';
    }
  };

  return (
    <div className="running-plan" style={{
      border: '1px solid #ddd',
      borderRadius: '6px',
      backgroundColor: '#fff',
      height: '150px'
    }}>
      <div style={{
        padding: '8px 12px',
        borderBottom: '1px solid #eee',
        backgroundColor: '#f8f9fa',
        fontWeight: 'bold',
        fontSize: '14px'
      }}>
        Currently Running Plan
      </div>

      {!runningPlan ? (
        <div style={{
          padding: '20px',
          textAlign: 'center',
          color: '#6c757d',
          fontStyle: 'italic'
        }}>
          No plan currently executing
        </div>
      ) : (
        <div style={{ padding: '12px' }}>
          {/* Plan Name and Status */}
          <div style={{ marginBottom: '8px' }}>
            <span style={{ fontWeight: 'bold', fontSize: '16px', color: '#007bff' }}>
              {runningPlan.name}
            </span>
            {executionStatus && (
              <span style={{
                marginLeft: '10px',
                padding: '2px 6px',
                backgroundColor: '#28a745',
                color: '#fff',
                borderRadius: '3px',
                fontSize: '11px'
              }}>
                RUNNING
              </span>
            )}
          </div>

          {/* Parameters */}
          {(runningPlan.args.length > 0 || Object.keys(runningPlan.kwargs).length > 0) && (
            <div style={{ fontSize: '12px', color: '#6c757d', marginBottom: '8px' }}>
              {formatArgs(runningPlan.args)}
              {runningPlan.args.length > 0 && Object.keys(runningPlan.kwargs).length > 0 && ', '}
              {formatKwargs(runningPlan.kwargs)}
            </div>
          )}

          {/* Plan Info */}
          <div style={{ fontSize: '11px', color: '#868e96' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '2px' }}>
              <span>User: {runningPlan.user}</span>
              <span>Group: {runningPlan.user_group}</span>
            </div>
            
            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '2px' }}>
              <span>Scan ID: {runningPlan.scan_id || 'N/A'}</span>
              <span>Started: {formatTime(runningPlan.time_start)}</span>
            </div>
            
            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '2px' }}>
              <span>Plan UID: {runningPlan.plan_uid?.slice(0, 8) || 'N/A'}...</span>
              <span>Elapsed: {getElapsedTime(runningPlan.time_start)}</span>
            </div>
            
            <div style={{ marginTop: '4px' }}>
              Item UID: {runningPlan.item_uid.slice(0, 8)}...
            </div>
          </div>

          {/* Progress bar placeholder - could be enhanced with actual progress data */}
          {executionStatus && (
            <div style={{ marginTop: '8px' }}>
              <div style={{
                height: '4px',
                backgroundColor: '#e9ecef',
                borderRadius: '2px',
                overflow: 'hidden'
              }}>
                <div style={{
                  height: '100%',
                  backgroundColor: '#007bff',
                  width: '100%', // This could be dynamic based on actual progress
                  animation: 'pulse 2s infinite'
                }}></div>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default RunningPlanComponent;
