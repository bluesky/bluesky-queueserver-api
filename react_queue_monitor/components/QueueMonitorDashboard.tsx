/**
 * Queue Monitor Dashboard
 * 
 * Main dashboard component that combines all queue monitoring and control components,
 * replicating the functionality of the Qt-based queue monitor.
 */

import React, { useState } from 'react';
import useQueueServerSocket from '../hooks/useQueueServerSocket';
import { QueueItem } from '../types/queueServerTypes';

// Import all components
import StatusMonitor from './StatusMonitor';
import PlanQueue from './PlanQueue';
import RunningPlanComponent from './RunningPlan';
import ConsoleMonitor from './ConsoleMonitor';
import QueueControls from './QueueControls';
import EnvironmentControls from './EnvironmentControls';  
import ExecutionControls from './ExecutionControls';
import PlanEditor from './PlanEditor';

interface QueueMonitorDashboardProps {
  wsUrl?: string;
  httpUrl?: string;
  apiKey?: string;
  layout?: 'monitor' | 'editor' | 'split';
}

export const QueueMonitorDashboard: React.FC<QueueMonitorDashboardProps> = ({
  wsUrl,
  httpUrl,
  apiKey,
  layout = 'split'
}) => {
  // State for UI
  const [activeTab, setActiveTab] = useState<'monitor' | 'editor'>('monitor');
  const [editorVisible, setEditorVisible] = useState(false);
  const [editingItem, setEditingItem] = useState<QueueItem | null>(null);
  const [lockKey, setLockKey] = useState<string>('');

  // Queue Server WebSocket hook
  const {
    // State
    status,
    queueStatus,
    runningPlan,
    planQueue,
    planHistory,
    consoleOutput,
    availablePlans,
    availableDevices,
    connected,
    connecting,
    error,
    lockInfo,
    
    // Actions
    connect,
    disconnect,
    startQueue,
    stopQueue,
    pauseQueue,
    resumeQueue,
    clearQueue,
    haltQueue,
    openEnvironment,
    closeEnvironment,
    destroyEnvironment,
    addPlan,
    updatePlan,
    removePlan,
    movePlan,
    stopPlan,
    abortPlan,
    haltPlan,
    pausePlan,
    resumePlan,
    refreshStatus,
    refreshQueue,
    refreshHistory,
  } = useQueueServerSocket({ wsUrl, httpUrl, apiKey });

  // Helper functions for actions with lock key
  const withLockKey = (actionFn: (lockKey?: string) => Promise<any>) => {
    return () => actionFn(lockKey || undefined);
  };

  // Plan queue event handlers
  const handleItemSelect = (item: QueueItem) => {
    console.log('Selected item:', item);
  };

  const handleItemEdit = (item: QueueItem) => {
    setEditingItem(item);
    setEditorVisible(true);
  };

  const handleItemRemove = async (uid: string) => {
    try {
      await removePlan(uid, lockKey || undefined);
    } catch (error) {
      alert(`Failed to remove plan: ${error}`);
    }
  };

  const handleItemMove = async (uid: string, direction: 'up' | 'down') => {
    const currentIndex = planQueue.findIndex(item => item.item_uid === uid);
    if (currentIndex === -1) return;
    
    const newIndex = direction === 'up' ? currentIndex - 1 : currentIndex + 1;
    if (newIndex < 0 || newIndex >= planQueue.length) return;
    
    try {
      await movePlan(uid, newIndex, lockKey || undefined);
    } catch (error) {
      alert(`Failed to move plan: ${error}`);
    }
  };

  // Plan editor handlers
  const handleAddPlan = async (plan: Partial<QueueItem>, position?: number) => {
    await addPlan(plan, position, lockKey || undefined);
  };

  const handleUpdatePlan = async (plan: QueueItem) => {
    await updatePlan(plan, lockKey || undefined);
  };

  const handleEditorCancel = () => {
    setEditorVisible(false);
    setEditingItem(null);
  };

  // Styles
  const containerStyle = {
    fontFamily: 'Arial, sans-serif',
    height: '100vh',
    display: 'flex',
    flexDirection: 'column' as const,
    backgroundColor: '#f5f5f5'
  };

  const headerStyle = {
    padding: '12px 16px',
    backgroundColor: '#343a40',
    color: '#fff',
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center'
  };

  const tabBarStyle = {
    padding: '0',
    backgroundColor: '#fff',
    borderBottom: '1px solid #ddd',
    display: 'flex'
  };

  const tabStyle = (active: boolean) => ({
    padding: '12px 24px',
    backgroundColor: active ? '#007bff' : '#f8f9fa',
    color: active ? '#fff' : '#495057',
    border: 'none',
    cursor: 'pointer',
    fontSize: '14px',
    fontWeight: 'bold' as const
  });

  const contentStyle = {
    flex: 1,
    overflow: 'auto',
    padding: '16px'
  };

  const gridStyle = {
    display: 'grid',
    gap: '16px',
    height: '100%'
  };

  // Layout configurations
  const layouts = {
    monitor: {
      gridTemplateColumns: '1fr 2fr',
      gridTemplateRows: 'auto 1fr 1fr auto',
      gridTemplateAreas: `
        "status status"
        "running queue"
        "history queue"
        "console console"
      `
    },
    editor: {
      gridTemplateColumns: '300px 1fr 1fr',
      gridTemplateRows: 'auto auto 1fr auto',
      gridTemplateAreas: `
        "env-controls queue-controls exec-controls"
        "status status status"
        "queue running history"
        "console console console"
      `
    },
    split: {
      gridTemplateColumns: '280px 1fr 1fr 280px',
      gridTemplateRows: 'auto auto 1fr auto',
      gridTemplateAreas: `
        "env-controls status status exec-controls"
        "queue-controls running running queue-controls"
        "queue queue history history"
        "console console console console"
      `
    }
  };

  const currentLayout = layouts[layout] || layouts.split;

  return (
    <div style={containerStyle}>
      {/* Header */}
      <div style={headerStyle}>
        <h4 style={{ margin: 0 }}>Bluesky Queue Monitor</h4>
        <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
          {/* Lock Key Input */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <label style={{ fontSize: '12px' }}>Lock Key:</label>
            <input
              type="text"
              value={lockKey}
              onChange={(e) => setLockKey(e.target.value)}
              placeholder="Optional"
              style={{
                padding: '4px 8px',
                fontSize: '12px',
                border: '1px solid #ccc',
                borderRadius: '4px',
                width: '120px'
              }}
            />
          </div>
          
          {/* Connection controls */}
          <div style={{ display: 'flex', gap: '8px' }}>
            <button
              onClick={connect}
              disabled={connected || connecting}
              style={{
                padding: '4px 8px',
                fontSize: '12px',
                backgroundColor: '#28a745',
                color: '#fff',
                border: 'none',
                borderRadius: '4px',
                cursor: connected || connecting ? 'not-allowed' : 'pointer',
                opacity: connected || connecting ? 0.6 : 1
              }}
            >
              {connecting ? 'Connecting...' : 'Connect'}
            </button>
            <button
              onClick={disconnect}
              disabled={!connected}
              style={{
                padding: '4px 8px',
                fontSize: '12px',
                backgroundColor: '#dc3545',
                color: '#fff',
                border: 'none',
                borderRadius: '4px',
                cursor: !connected ? 'not-allowed' : 'pointer',
                opacity: !connected ? 0.6 : 1
              }}
            >
              Disconnect
            </button>
          </div>
        </div>
      </div>

      {/* Tab Bar */}
      {layout === 'split' && (
        <div style={tabBarStyle}>
          <button
            style={tabStyle(activeTab === 'monitor')}
            onClick={() => setActiveTab('monitor')}
          >
            Monitor Queue
          </button>
          <button
            style={tabStyle(activeTab === 'editor')}
            onClick={() => setActiveTab('editor')}
          >
            Edit and Control Queue
          </button>
        </div>
      )}

      {/* Main Content */}
      <div style={contentStyle}>
        <div style={{ ...gridStyle, ...currentLayout }}>
          {/* Status Monitor */}
          <div style={{ gridArea: 'status' }}>
            <StatusMonitor status={status} connected={connected} error={error} />
          </div>

          {/* Environment Controls */}
          {(layout === 'editor' || (layout === 'split' && activeTab === 'editor')) && (
            <div style={{ gridArea: 'env-controls' }}>
              <EnvironmentControls
                status={status}
                onOpenEnvironment={withLockKey(openEnvironment)}
                onCloseEnvironment={withLockKey(closeEnvironment)}
                onDestroyEnvironment={withLockKey(destroyEnvironment)}
              />
            </div>
          )}

          {/* Queue Controls */}
          <div style={{ gridArea: 'queue-controls' }}>
            <QueueControls
              status={status}
              onStartQueue={withLockKey(startQueue)}
              onStopQueue={withLockKey(stopQueue)}
              onPauseQueue={withLockKey(pauseQueue)}
              onResumeQueue={withLockKey(resumeQueue)}
              onClearQueue={withLockKey(clearQueue)}
              onHaltQueue={withLockKey(haltQueue)}
            />
          </div>

          {/* Execution Controls */}
          {(layout === 'editor' || (layout === 'split' && activeTab === 'editor')) && (
            <div style={{ gridArea: 'exec-controls' }}>
              <ExecutionControls
                status={status}
                runningPlan={runningPlan}
                onStopPlan={withLockKey(stopPlan)}
                onAbortPlan={withLockKey(abortPlan)}
                onHaltPlan={withLockKey(haltPlan)}
                onPausePlan={(option?: string) => pausePlan(option, lockKey || undefined)}
                onResumePlan={withLockKey(resumePlan)}
              />
            </div>
          )}

          {/* Running Plan */}
          <div style={{ gridArea: 'running' }}>
            <RunningPlanComponent runningPlan={runningPlan} />
          </div>

          {/* Plan Queue */}
          <div style={{ gridArea: 'queue' }}>
            <PlanQueue
              planQueue={planQueue}
              runningItemUid={runningPlan?.item_uid}
              onItemSelect={handleItemSelect}
              onItemEdit={handleItemEdit}
              onItemRemove={handleItemRemove}
              onItemMove={handleItemMove}
              readOnly={layout === 'monitor'}
            />
            
            {(layout === 'editor' || (layout === 'split' && activeTab === 'editor')) && (
              <div style={{ marginTop: '8px', textAlign: 'center' }}>
                <button
                  onClick={() => setEditorVisible(true)}
                  style={{
                    padding: '8px 16px',
                    fontSize: '12px',
                    backgroundColor: '#007bff',
                    color: '#fff',
                    border: 'none',
                    borderRadius: '4px',
                    cursor: 'pointer'
                  }}
                >
                  + Add Plan
                </button>
              </div>
            )}
          </div>

          {/* Plan History */}
          {(layout === 'monitor' || layout === 'split') && (
            <div style={{ gridArea: 'history' }}>
              <div style={{
                border: '1px solid #ddd',
                borderRadius: '6px',
                backgroundColor: '#fff',
                height: '300px',
                overflow: 'auto'
              }}>
                <div style={{
                  padding: '8px 12px',
                  borderBottom: '1px solid #eee',
                  backgroundColor: '#f8f9fa',
                  fontWeight: 'bold',
                  fontSize: '14px'
                }}>
                  Plan History ({planHistory.length} items)
                </div>
                <div style={{ padding: '8px' }}>
                  {planHistory.slice(-20).reverse().map((item, index) => (
                    <div key={item.item_uid} style={{
                      padding: '6px',
                      borderBottom: '1px solid #f0f0f0',
                      fontSize: '12px'
                    }}>
                      <div style={{ fontWeight: 'bold' }}>
                        {item.name} - {item.exit_status}
                      </div>
                      <div style={{ color: '#6c757d', fontSize: '11px' }}>
                        {item.time_start} - {item.time_stop}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}

          {/* Console Output */}
          <div style={{ gridArea: 'console' }}>
            <ConsoleMonitor consoleOutput={consoleOutput} />
          </div>
        </div>
      </div>

      {/* Plan Editor Modal */}
      <PlanEditor
        availablePlans={availablePlans}
        availableDevices={availableDevices}
        editingItem={editingItem}
        onAddPlan={handleAddPlan}
        onUpdatePlan={handleUpdatePlan}
        onCancel={handleEditorCancel}
        visible={editorVisible}
      />
    </div>
  );
};

export default QueueMonitorDashboard;
