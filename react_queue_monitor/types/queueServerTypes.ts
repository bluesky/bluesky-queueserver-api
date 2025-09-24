/**
 * TypeScript types for Bluesky Queue Server API
 * Based on bluesky_queueserver_api functionality
 */

export interface QueueItem {
  name: string;
  args: any[];
  kwargs: Record<string, any>;
  item_uid: string;
  user: string;
  item_type: 'plan' | 'instruction';
  user_group: string;
  meta?: Record<string, any>;
}

export interface RunningPlan {
  name: string;
  args: any[];
  kwargs: Record<string, any>;
  item_uid: string;
  user: string;
  user_group: string;
  scan_id: number | null;
  plan_uid: string | null;
  time_start: string | null;
  meta?: Record<string, any>;
}

export interface PlanHistoryItem {
  name: string;
  args: any[];
  kwargs: Record<string, any>;
  item_uid: string;
  user: string;
  user_group: string;
  scan_id: number | null;
  plan_uid: string | null;
  time_start: string;
  time_stop: string;
  exit_status: 'completed' | 'stopped' | 'aborted' | 'failed';
  result?: Record<string, any>;
  traceback?: string;
  meta?: Record<string, any>;
}

export interface QueueStatus {
  items: QueueItem[];
  running_item: RunningPlan | null;
  plan_queue_uid: string;
  worker_environment_exists: boolean;
  worker_environment_state: 'closed' | 'idle' | 'executing_plan' | 'executing_task';
  manager_state: 'initializing' | 'idle' | 'paused' | 'executing_queue' | 'closing_environment' | 'destroying_environment';
  queue_stop_pending: boolean;
  queue_autostart_enabled: boolean;
  plan_history_uid: string;
  devices_existing_uid: string;
  plans_existing_uid: string;
  devices_allowed_uid: string;
  plans_allowed_uid: string;
}

export interface ManagerStatus {
  manager_state: string;
  worker_environment_exists: boolean;
  worker_environment_state: string;
  queue_autostart_enabled: boolean;
  re_state: string | null;
  queue_stop_pending: boolean;
  running_item_uid: string | null;
  msg: string;
  items_in_queue: number;
  items_in_history: number;
  plan_history_uid: string;
  plan_queue_uid: string;
}

export interface ConsoleOutput {
  time: string;
  msg: string;
  msg_type: 'PRINT' | 'ERROR' | 'WARNING' | 'INFO';
}

export interface DeviceInfo {
  name: string;
  classname: string;
  module: string;
  is_device: boolean;
  is_pseudo_device: boolean;
  is_ophyd_device: boolean;
  is_flyable: boolean;
  is_readable: boolean;
  is_movable: boolean;
}

export interface PlanInfo {
  name: string;
  module: string;
  description: string;
  parameters: PlanParameter[];
  user_group: string;
}

export interface PlanParameter {
  name: string;
  kind: 'POSITIONAL_ONLY' | 'POSITIONAL_OR_KEYWORD' | 'VAR_POSITIONAL' | 'KEYWORD_ONLY' | 'VAR_KEYWORD';
  default?: any;
  annotation?: string;
  description?: string;
}

export interface WebSocketMessage {
  method?: string;
  params?: Record<string, any>;
  id?: string;
  success?: boolean;
  msg?: string;
  time_start?: string;
  task_uid?: string;
  results?: any;
}

export interface SubscriptionMessage {
  topic: string;
  data: any;
  timestamp: string;
}

export interface LockInfo {
  environment: boolean;
  queue: boolean;
  note?: string;
  user?: string;
  time?: string;
  lock_key?: string;
}

export interface ApiResponse<T = any> {
  success: boolean;
  msg: string;
  time_start?: string;
  task_uid?: string;
  lock_key?: string;
  results?: T;
}

// Hook return types
export interface QueueServerState {
  // Status
  status: ManagerStatus | null;
  queueStatus: QueueStatus | null;
  runningPlan: RunningPlan | null;
  
  // Data
  planQueue: QueueItem[];
  planHistory: PlanHistoryItem[];
  consoleOutput: ConsoleOutput[];
  availablePlans: PlanInfo[];
  availableDevices: DeviceInfo[];
  
  // Connection
  connected: boolean;
  connecting: boolean;
  error: string | null;
  
  // Lock status
  lockInfo: LockInfo | null;
}

export interface QueueServerActions {
  // Connection
  connect: () => Promise<void>;
  disconnect: () => Promise<void>;
  
  // Queue control
  startQueue: (lockKey?: string) => Promise<ApiResponse>;
  stopQueue: (lockKey?: string) => Promise<ApiResponse>;
  pauseQueue: (lockKey?: string) => Promise<ApiResponse>;
  resumeQueue: (lockKey?: string) => Promise<ApiResponse>;
  clearQueue: (lockKey?: string) => Promise<ApiResponse>;
  haltQueue: (lockKey?: string) => Promise<ApiResponse>;
  
  // Environment control
  openEnvironment: (lockKey?: string) => Promise<ApiResponse>;
  closeEnvironment: (lockKey?: string) => Promise<ApiResponse>;
  destroyEnvironment: (lockKey?: string) => Promise<ApiResponse>;
  
  // Plan management
  addPlan: (plan: Partial<QueueItem>, pos?: number, lockKey?: string) => Promise<ApiResponse>;
  updatePlan: (plan: QueueItem, lockKey?: string) => Promise<ApiResponse>;
  removePlan: (uid: string, lockKey?: string) => Promise<ApiResponse>;
  movePlan: (uid: string, pos: number, lockKey?: string) => Promise<ApiResponse>;
  
  // Execution control  
  stopPlan: (lockKey?: string) => Promise<ApiResponse>;
  abortPlan: (lockKey?: string) => Promise<ApiResponse>;
  haltPlan: (lockKey?: string) => Promise<ApiResponse>;
  pausePlan: (option?: string, lockKey?: string) => Promise<ApiResponse>;
  resumePlan: (lockKey?: string) => Promise<ApiResponse>;
  
  // Locking
  lockEnvironment: (note?: string) => Promise<ApiResponse>;
  lockQueue: (note?: string) => Promise<ApiResponse>;
  unlockEnvironment: (lockKey?: string) => Promise<ApiResponse>;
  unlockQueue: (lockKey?: string) => Promise<ApiResponse>;
  
  // Data refresh
  refreshStatus: () => Promise<void>;
  refreshQueue: () => Promise<void>;
  refreshHistory: () => Promise<void>;
  refreshPlans: () => Promise<void>;
  refreshDevices: () => Promise<void>;
}

export type QueueServerHookReturn = QueueServerState & QueueServerActions;
