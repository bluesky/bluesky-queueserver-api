/**
 * React Hook for Bluesky Queue Server WebSocket Communication
 * 
 * This hook provides real-time communication with the Bluesky Queue Server
 * via WebSocket, replicating the functionality of the Qt-based queue monitor.
 */

import { useState, useRef, useEffect, useCallback } from 'react';
import {
  QueueServerState,
  QueueServerActions,
  QueueServerHookReturn,
  WebSocketMessage,
  SubscriptionMessage,
  ApiResponse,
  QueueItem,
  ManagerStatus,
  QueueStatus,
  ConsoleOutput,
  PlanHistoryItem,
  PlanInfo,
  DeviceInfo,
  LockInfo,
} from '../types/queueServerTypes';

interface UseQueueServerSocketOptions {
  wsUrl?: string;
  httpUrl?: string;
  apiKey?: string;
  autoConnect?: boolean;
  reconnectAttempts?: number;
  reconnectDelay?: number;
}

export default function useQueueServerSocket(options: UseQueueServerSocketOptions = {}): QueueServerHookReturn {
  // Default configuration
  const {
    wsUrl = process.env.REACT_APP_QUEUE_SERVER_WS_URL || 'ws://localhost:60610/ws',
    httpUrl = process.env.REACT_APP_QUEUE_SERVER_HTTP_URL || 'http://localhost:60610',
    apiKey,
    autoConnect = true,
    reconnectAttempts = 5,
    reconnectDelay = 3000,
  } = options;

  // WebSocket reference
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const pendingRequestsRef = useRef<Map<string, (response: ApiResponse) => void>>(new Map());
  const reconnectCountRef = useRef(0);

  // State
  const [state, setState] = useState<QueueServerState>({
    // Status
    status: null,
    queueStatus: null,
    runningPlan: null,
    
    // Data
    planQueue: [],
    planHistory: [],
    consoleOutput: [],
    availablePlans: [],
    availableDevices: [],
    
    // Connection
    connected: false,
    connecting: false,
    error: null,
    
    // Lock status
    lockInfo: null,
  });

  // Generate unique request ID
  const generateRequestId = useCallback(() => {
    return `req_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
  }, []);

  // Send WebSocket message
  const sendMessage = useCallback(async (message: WebSocketMessage): Promise<ApiResponse> => {
    return new Promise((resolve, reject) => {
      if (!wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) {
        reject(new Error('WebSocket not connected'));
        return;
      }

      const requestId = message.id || generateRequestId();
      const messageWithId = { ...message, id: requestId };

      // Store promise resolver for response
      pendingRequestsRef.current.set(requestId, resolve);

      // Set timeout for request
      setTimeout(() => {
        if (pendingRequestsRef.current.has(requestId)) {
          pendingRequestsRef.current.delete(requestId);
          reject(new Error('Request timeout'));
        }
      }, 30000); // 30 second timeout

      try {
        wsRef.current.send(JSON.stringify(messageWithId));
      } catch (error) {
        pendingRequestsRef.current.delete(requestId);
        reject(error);
      }
    });
  }, [generateRequestId]);

  // Handle incoming WebSocket messages
  const handleMessage = useCallback((event: MessageEvent) => {
    try {
      const message = JSON.parse(event.data);

      // Handle subscription messages (real-time updates)
      if (message.topic) {
        const subscriptionMsg = message as SubscriptionMessage;
        
        switch (subscriptionMsg.topic) {
          case 'queue_status':
            setState(prev => ({
              ...prev,
              queueStatus: subscriptionMsg.data as QueueStatus,
              planQueue: subscriptionMsg.data.items || [],
              runningPlan: subscriptionMsg.data.running_item,
            }));
            break;
            
          case 'manager_status':
            setState(prev => ({
              ...prev,
              status: subscriptionMsg.data as ManagerStatus,
            }));
            break;
            
          case 'console_output':
            setState(prev => ({
              ...prev,
              consoleOutput: [...prev.consoleOutput.slice(-999), subscriptionMsg.data as ConsoleOutput],
            }));
            break;
            
          case 'plan_history':
            setState(prev => ({
              ...prev,
              planHistory: subscriptionMsg.data as PlanHistoryItem[],
            }));
            break;
            
          case 'lock_info':
            setState(prev => ({
              ...prev,
              lockInfo: subscriptionMsg.data as LockInfo,
            }));
            break;
        }
      }
      // Handle API response messages
      else if (message.id && pendingRequestsRef.current.has(message.id)) {
        const resolver = pendingRequestsRef.current.get(message.id);
        if (resolver) {
          resolver(message as ApiResponse);
          pendingRequestsRef.current.delete(message.id);
        }
      }
      // Handle server info and other messages
      else if (message.msg) {
        console.log('Queue Server message:', message.msg);
      }
      
    } catch (error) {
      console.error('Error parsing WebSocket message:', error, event.data);
    }
  }, []);

  // WebSocket connection management
  const connect = useCallback(async (): Promise<void> => {
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      return;
    }

    setState(prev => ({ ...prev, connecting: true, error: null }));

    try {
      const ws = new WebSocket(wsUrl);
      wsRef.current = ws;

      ws.onopen = async () => {
        console.log('Connected to Queue Server WebSocket');
        setState(prev => ({ ...prev, connected: true, connecting: false, error: null }));
        reconnectCountRef.current = 0;

        // Subscribe to real-time updates
        try {
          await sendMessage({ method: 'subscribe', params: { topic: 'queue_status' } });
          await sendMessage({ method: 'subscribe', params: { topic: 'manager_status' } });
          await sendMessage({ method: 'subscribe', params: { topic: 'console_output' } });
          await sendMessage({ method: 'subscribe', params: { topic: 'plan_history' } });
          await sendMessage({ method: 'subscribe', params: { topic: 'lock_info' } });
        } catch (error) {
          console.error('Failed to subscribe to topics:', error);
        }

        // Load initial data
        await refreshStatus();
        await refreshQueue();
        await refreshPlans();
        await refreshDevices();
      };

      ws.onmessage = handleMessage;

      ws.onclose = () => {
        console.log('Queue Server WebSocket disconnected');
        setState(prev => ({ ...prev, connected: false, connecting: false }));
        
        // Attempt reconnection if not manually closed
        if (reconnectCountRef.current < reconnectAttempts) {
          reconnectCountRef.current++;
          console.log(`Reconnecting... attempt ${reconnectCountRef.current}/${reconnectAttempts}`);
          
          reconnectTimeoutRef.current = setTimeout(() => {
            connect();
          }, reconnectDelay);
        }
      };

      ws.onerror = (error) => {
        console.error('Queue Server WebSocket error:', error);
        setState(prev => ({ 
          ...prev, 
          error: 'WebSocket connection error', 
          connecting: false 
        }));
      };

    } catch (error) {
      setState(prev => ({ 
        ...prev, 
        error: `Failed to connect: ${error}`, 
        connecting: false 
      }));
    }
  }, [wsUrl, handleMessage, sendMessage, reconnectAttempts, reconnectDelay]);

  const disconnect = useCallback(async (): Promise<void> => {
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
    }
    
    if (wsRef.current) {
      wsRef.current.close();
      wsRef.current = null;
    }
    
    setState(prev => ({ ...prev, connected: false, connecting: false }));
  }, []);

  // Queue control actions
  const startQueue = useCallback(async (lockKey?: string): Promise<ApiResponse> => {
    return sendMessage({
      method: 'queue_start',
      params: lockKey ? { lock_key: lockKey } : {}
    });
  }, [sendMessage]);

  const stopQueue = useCallback(async (lockKey?: string): Promise<ApiResponse> => {
    return sendMessage({
      method: 'queue_stop',
      params: lockKey ? { lock_key: lockKey } : {}
    });
  }, [sendMessage]);

  const pauseQueue = useCallback(async (lockKey?: string): Promise<ApiResponse> => {
    return sendMessage({
      method: 'queue_pause',
      params: lockKey ? { lock_key: lockKey } : {}
    });
  }, [sendMessage]);

  const resumeQueue = useCallback(async (lockKey?: string): Promise<ApiResponse> => {
    return sendMessage({
      method: 'queue_resume',
      params: lockKey ? { lock_key: lockKey } : {}
    });
  }, [sendMessage]);

  const clearQueue = useCallback(async (lockKey?: string): Promise<ApiResponse> => {
    return sendMessage({
      method: 'queue_clear',
      params: lockKey ? { lock_key: lockKey } : {}
    });
  }, [sendMessage]);

  const haltQueue = useCallback(async (lockKey?: string): Promise<ApiResponse> => {
    return sendMessage({
      method: 'queue_halt',
      params: lockKey ? { lock_key: lockKey } : {}
    });
  }, [sendMessage]);

  // Environment control actions
  const openEnvironment = useCallback(async (lockKey?: string): Promise<ApiResponse> => {
    return sendMessage({
      method: 'environment_open',
      params: lockKey ? { lock_key: lockKey } : {}
    });
  }, [sendMessage]);

  const closeEnvironment = useCallback(async (lockKey?: string): Promise<ApiResponse> => {
    return sendMessage({
      method: 'environment_close',
      params: lockKey ? { lock_key: lockKey } : {}
    });
  }, [sendMessage]);

  const destroyEnvironment = useCallback(async (lockKey?: string): Promise<ApiResponse> => {
    return sendMessage({
      method: 'environment_destroy',
      params: lockKey ? { lock_key: lockKey } : {}
    });
  }, [sendMessage]);

  // Plan management actions
  const addPlan = useCallback(async (plan: Partial<QueueItem>, pos?: number, lockKey?: string): Promise<ApiResponse> => {
    const params: any = { ...plan };
    if (pos !== undefined) params.pos = pos;
    if (lockKey) params.lock_key = lockKey;
    
    return sendMessage({
      method: 'queue_item_add',
      params
    });
  }, [sendMessage]);

  const updatePlan = useCallback(async (plan: QueueItem, lockKey?: string): Promise<ApiResponse> => {
    const params: any = { ...plan };
    if (lockKey) params.lock_key = lockKey;
    
    return sendMessage({
      method: 'queue_item_update',
      params
    });
  }, [sendMessage]);

  const removePlan = useCallback(async (uid: string, lockKey?: string): Promise<ApiResponse> => {
    return sendMessage({
      method: 'queue_item_remove',
      params: { uid, ...(lockKey ? { lock_key: lockKey } : {}) }
    });
  }, [sendMessage]);

  const movePlan = useCallback(async (uid: string, pos: number, lockKey?: string): Promise<ApiResponse> => {
    return sendMessage({
      method: 'queue_item_move',
      params: { uid, pos, ...(lockKey ? { lock_key: lockKey } : {}) }
    });
  }, [sendMessage]);

  // Execution control actions
  const stopPlan = useCallback(async (lockKey?: string): Promise<ApiResponse> => {
    return sendMessage({
      method: 're_stop',
      params: lockKey ? { lock_key: lockKey } : {}
    });
  }, [sendMessage]);

  const abortPlan = useCallback(async (lockKey?: string): Promise<ApiResponse> => {
    return sendMessage({
      method: 're_abort',
      params: lockKey ? { lock_key: lockKey } : {}
    });
  }, [sendMessage]);

  const haltPlan = useCallback(async (lockKey?: string): Promise<ApiResponse> => {
    return sendMessage({
      method: 're_halt',
      params: lockKey ? { lock_key: lockKey } : {}
    });
  }, [sendMessage]);

  const pausePlan = useCallback(async (option?: string, lockKey?: string): Promise<ApiResponse> => {
    return sendMessage({
      method: 're_pause',
      params: { 
        ...(option ? { option } : {}),
        ...(lockKey ? { lock_key: lockKey } : {})
      }
    });
  }, [sendMessage]);

  const resumePlan = useCallback(async (lockKey?: string): Promise<ApiResponse> => {
    return sendMessage({
      method: 're_resume',
      params: lockKey ? { lock_key: lockKey } : {}
    });
  }, [sendMessage]);

  // Locking actions
  const lockEnvironment = useCallback(async (note?: string): Promise<ApiResponse> => {
    return sendMessage({
      method: 'lock',
      params: { 
        environment: true,
        ...(note ? { note } : {})
      }
    });
  }, [sendMessage]);

  const lockQueue = useCallback(async (note?: string): Promise<ApiResponse> => {
    return sendMessage({
      method: 'lock',
      params: { 
        queue: true,
        ...(note ? { note } : {})
      }
    });
  }, [sendMessage]);

  const unlockEnvironment = useCallback(async (lockKey?: string): Promise<ApiResponse> => {
    return sendMessage({
      method: 'unlock',
      params: { 
        environment: true,
        ...(lockKey ? { lock_key: lockKey } : {})
      }
    });
  }, [sendMessage]);

  const unlockQueue = useCallback(async (lockKey?: string): Promise<ApiResponse> => {
    return sendMessage({
      method: 'unlock',
      params: { 
        queue: true,
        ...(lockKey ? { lock_key: lockKey } : {})
      }
    });
  }, [sendMessage]);

  // Data refresh actions
  const refreshStatus = useCallback(async (): Promise<void> => {
    try {
      const response = await sendMessage({ method: 'status' });
      if (response.success) {
        setState(prev => ({ ...prev, status: response.results as ManagerStatus }));
      }
    } catch (error) {
      console.error('Failed to refresh status:', error);
    }
  }, [sendMessage]);

  const refreshQueue = useCallback(async (): Promise<void> => {
    try {
      const response = await sendMessage({ method: 'queue_get' });
      if (response.success) {
        const queueData = response.results as QueueStatus;
        setState(prev => ({ 
          ...prev, 
          queueStatus: queueData,
          planQueue: queueData.items || [],
          runningPlan: queueData.running_item
        }));
      }
    } catch (error) {
      console.error('Failed to refresh queue:', error);
    }
  }, [sendMessage]);

  const refreshHistory = useCallback(async (): Promise<void> => {
    try {
      const response = await sendMessage({ method: 'history_get' });
      if (response.success) {
        setState(prev => ({ ...prev, planHistory: response.results as PlanHistoryItem[] }));
      }
    } catch (error) {
      console.error('Failed to refresh plan history:', error);
    }
  }, [sendMessage]);

  const refreshPlans = useCallback(async (): Promise<void> => {
    try {
      const response = await sendMessage({ method: 'plans_allowed' });
      if (response.success) {
        setState(prev => ({ ...prev, availablePlans: response.results as PlanInfo[] }));
      }
    } catch (error) {
      console.error('Failed to refresh available plans:', error);
    }
  }, [sendMessage]);

  const refreshDevices = useCallback(async (): Promise<void> => {
    try {
      const response = await sendMessage({ method: 'devices_allowed' });
      if (response.success) {
        setState(prev => ({ ...prev, availableDevices: response.results as DeviceInfo[] }));
      }
    } catch (error) {
      console.error('Failed to refresh available devices:', error);
    }
  }, [sendMessage]);

  // Auto-connect on mount
  useEffect(() => {
    if (autoConnect) {
      connect();
    }

    return () => {
      disconnect();
    };
  }, [autoConnect, connect, disconnect]);

  // Return state and actions
  return {
    // State
    ...state,
    
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
    lockEnvironment,
    lockQueue,
    unlockEnvironment,
    unlockQueue,
    refreshStatus,
    refreshQueue,
    refreshHistory,
    refreshPlans,
    refreshDevices,
  };
}
