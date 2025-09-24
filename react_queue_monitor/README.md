# React Queue Monitor

A comprehensive React component library for monitoring and controlling Bluesky Queue Server operations. This library provides React equivalents to the Qt-based queue monitor widgets, enabling web-based queue management interfaces.

## Overview

This package provides:
- **QueueMonitorDashboard**: Complete dashboard with all monitoring and control features
- **Individual Components**: Modular components for specific functionality
- **WebSocket Hook**: `useQueueServerSocket` for real-time communication
- **TypeScript Support**: Complete type definitions for queue server operations

## Components

### QueueMonitorDashboard
Main dashboard component that combines all queue monitoring and control features.

```tsx
import { QueueMonitorDashboard } from './react_queue_monitor';

function App() {
  return (
    <QueueMonitorDashboard
      wsUrl="ws://localhost:60610"
      httpUrl="http://localhost:60610"
      apiKey="your-api-key"
      layout="split"
    />
  );
}
```

### Individual Components

- **StatusMonitor**: Displays queue server status and connection state
- **PlanQueue**: Shows queued plans with editing capabilities
- **RunningPlan**: Displays currently executing plan details
- **ConsoleMonitor**: Shows real-time console output
- **QueueControls**: Start, stop, pause, resume queue operations
- **EnvironmentControls**: Open, close, destroy RE environment
- **ExecutionControls**: Stop, abort, halt, pause, resume plan execution
- **PlanEditor**: Add and edit plans with parameter validation

```tsx
import { 
  StatusMonitor,
  PlanQueue,
  QueueControls,
  useQueueServerSocket 
} from './react_queue_monitor';

function CustomQueueInterface() {
  const { status, planQueue, startQueue, stopQueue } = useQueueServerSocket();
  
  return (
    <div>
      <StatusMonitor status={status} />
      <PlanQueue planQueue={planQueue} />
      <QueueControls 
        status={status}
        onStartQueue={startQueue}
        onStopQueue={stopQueue}
      />
    </div>
  );
}
```

## Hook Usage

### useQueueServerSocket

The main hook for WebSocket communication with the queue server:

```tsx
import { useQueueServerSocket } from './react_queue_monitor';

function MyComponent() {
  const {
    // Connection state
    connected,
    connecting,
    error,
    
    // Queue state
    status,
    planQueue,
    runningPlan,
    consoleOutput,
    
    // Actions
    connect,
    disconnect,
    startQueue,
    stopQueue,
    addPlan,
    removePlan,
  } = useQueueServerSocket({
    wsUrl: 'ws://localhost:60610',
    httpUrl: 'http://localhost:60610',
    apiKey: 'your-api-key'
  });
  
  // Use the state and actions in your component
}
```

## TypeScript Types

Complete type definitions are provided for all queue server operations:

```tsx
import { 
  QueueItem,
  RunningPlan,
  ManagerStatus,
  QueueServerHookReturn 
} from './react_queue_monitor';

// Example: Custom plan creation
const newPlan: Partial<QueueItem> = {
  name: 'count',
  item_type: 'plan',
  parameters: {
    detectors: ['det1'],
    num: 10
  }
};
```

## Installation & Setup

1. **Install Dependencies**:
```bash
npm install react react-dom @types/react @types/react-dom
# or
yarn add react react-dom @types/react @types/react-dom
```

2. **Copy Components**: Copy the `react_queue_monitor` folder to your project

3. **Import and Use**:
```tsx
import { QueueMonitorDashboard } from './react_queue_monitor';

// Full dashboard
<QueueMonitorDashboard 
  wsUrl="ws://localhost:60610"
  httpUrl="http://localhost:60610"
/>

// Or individual components
import { useQueueServerSocket, StatusMonitor } from './react_queue_monitor';
```

## Configuration

### WebSocket Connection
```tsx
const config = {
  wsUrl: 'ws://localhost:60610',     // WebSocket URL
  httpUrl: 'http://localhost:60610', // HTTP API URL  
  apiKey: 'your-api-key',            // Optional API key
  autoConnect: true,                 // Auto-connect on mount
  reconnectInterval: 3000,           // Reconnection interval (ms)
  maxReconnectAttempts: 5            // Max reconnection attempts
};
```

### Dashboard Layouts
- **`monitor`**: Read-only monitoring layout
- **`editor`**: Full editing and control layout  
- **`split`**: Tabbed interface with both modes

## API Reference

### QueueMonitorDashboard Props
```tsx
interface QueueMonitorDashboardProps {
  wsUrl?: string;           // WebSocket URL
  httpUrl?: string;         // HTTP API URL
  apiKey?: string;          // API key for authentication
  layout?: 'monitor' | 'editor' | 'split'; // Dashboard layout
}
```

### useQueueServerSocket Options
```tsx
interface UseQueueServerSocketOptions {
  wsUrl?: string;
  httpUrl?: string;
  apiKey?: string;
  autoConnect?: boolean;
  reconnectInterval?: number;
  maxReconnectAttempts?: number;
}
```

### Hook Return Value
```tsx
interface QueueServerHookReturn {
  // Connection State
  connected: boolean;
  connecting: boolean;
  error: string | null;
  
  // Queue State  
  status: ManagerStatus | null;
  queueStatus: any;
  runningPlan: RunningPlan | null;
  planQueue: QueueItem[];
  planHistory: QueueItem[];
  consoleOutput: string[];
  availablePlans: Record<string, any>;
  availableDevices: Record<string, any>;
  lockInfo: any;
  
  // Connection Actions
  connect: () => void;
  disconnect: () => void;
  
  // Queue Control Actions
  startQueue: (lockKey?: string) => Promise<any>;
  stopQueue: (lockKey?: string) => Promise<any>;
  pauseQueue: (lockKey?: string) => Promise<any>;
  resumeQueue: (lockKey?: string) => Promise<any>;
  clearQueue: (lockKey?: string) => Promise<any>;
  haltQueue: (lockKey?: string) => Promise<any>;
  
  // Environment Actions
  openEnvironment: (lockKey?: string) => Promise<any>;
  closeEnvironment: (lockKey?: string) => Promise<any>;
  destroyEnvironment: (lockKey?: string) => Promise<any>;
  
  // Plan Management Actions
  addPlan: (plan: Partial<QueueItem>, position?: number, lockKey?: string) => Promise<any>;
  updatePlan: (plan: QueueItem, lockKey?: string) => Promise<any>;
  removePlan: (uid: string, lockKey?: string) => Promise<any>;
  movePlan: (uid: string, newIndex: number, lockKey?: string) => Promise<any>;
  
  // Execution Control Actions
  stopPlan: (lockKey?: string) => Promise<any>;
  abortPlan: (lockKey?: string) => Promise<any>;
  haltPlan: (lockKey?: string) => Promise<any>;
  pausePlan: (option?: string, lockKey?: string) => Promise<any>;
  resumePlan: (lockKey?: string) => Promise<any>;
  
  // Refresh Actions
  refreshStatus: () => Promise<any>;
  refreshQueue: () => Promise<any>;
  refreshHistory: () => Promise<any>;
}
```

## Examples

### Basic Queue Monitor
```tsx
import React from 'react';
import { QueueMonitorDashboard } from './react_queue_monitor';

function App() {
  return (
    <div className="App">
      <QueueMonitorDashboard 
        wsUrl="ws://localhost:60610"
        httpUrl="http://localhost:60610" 
        layout="monitor"
      />
    </div>
  );
}
```

### Custom Interface with Individual Components
```tsx
import React from 'react';
import { 
  useQueueServerSocket,
  StatusMonitor,
  QueueControls,
  PlanQueue
} from './react_queue_monitor';

function CustomInterface() {
  const queueServer = useQueueServerSocket({
    wsUrl: 'ws://localhost:60610',
    httpUrl: 'http://localhost:60610'
  });

  return (
    <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px' }}>
      <div>
        <StatusMonitor 
          status={queueServer.status} 
          connected={queueServer.connected}
          error={queueServer.error}
        />
        <QueueControls
          status={queueServer.status}
          onStartQueue={queueServer.startQueue}
          onStopQueue={queueServer.stopQueue}
          onPauseQueue={queueServer.pauseQueue}
          onResumeQueue={queueServer.resumeQueue}
        />
      </div>
      <div>
        <PlanQueue
          planQueue={queueServer.planQueue}
          runningItemUid={queueServer.runningPlan?.item_uid}
          onItemRemove={queueServer.removePlan}
        />
      </div>
    </div>
  );
}
```

### Adding Plans Programmatically
```tsx
import { useQueueServerSocket } from './react_queue_monitor';

function PlanManager() {
  const { addPlan, availablePlans } = useQueueServerSocket();
  
  const addCountPlan = async () => {
    await addPlan({
      name: 'count',
      item_type: 'plan',
      parameters: {
        detectors: ['det1', 'det2'],
        num: 10
      }
    });
  };
  
  const addScanPlan = async () => {
    await addPlan({
      name: 'scan',
      item_type: 'plan', 
      parameters: {
        detectors: ['det1'],
        motor: 'motor1',
        start: -1,
        stop: 1,
        num: 21
      }
    });
  };
  
  return (
    <div>
      <button onClick={addCountPlan}>Add Count Plan</button>
      <button onClick={addScanPlan}>Add Scan Plan</button>
    </div>
  );
}
```

## Architecture

This component library mirrors the architecture of the Qt-based queue monitor:

- **StatusMonitor** ↔ `QtReStatusMonitor`
- **PlanQueue** ↔ `QtRePlanQueue` 
- **RunningPlan** ↔ `QtReRunningPlan`
- **ConsoleMonitor** ↔ `QtReConsoleMonitor`
- **QueueControls** ↔ Queue control buttons
- **EnvironmentControls** ↔ Environment management buttons
- **ExecutionControls** ↔ Execution control buttons
- **PlanEditor** ↔ Plan editing dialogs

The WebSocket communication uses the same API endpoints as the Qt widgets, ensuring compatibility and consistent behavior.

## Development

### Building the Components
```bash
# Install dependencies
npm install

# Type checking
npx tsc --noEmit

# Linting
npx eslint . --ext .ts,.tsx
```

### Testing with Queue Server
1. Start the Bluesky Queue Server:
```bash
start-re-manager --zmq-publish-console=ON
```

2. Start the HTTP/WebSocket server:
```bash  
uvicorn bluesky_queueserver.server.server:app --host localhost --port 60610
```

3. Use the components in your React application

## License

This project follows the same license as the main bluesky-queueserver-api project.
