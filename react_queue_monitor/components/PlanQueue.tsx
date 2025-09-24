/**
 * Plan Queue Component
 * 
 * Displays the current queue of plans waiting to be executed,
 * equivalent to QtRePlanQueue in the Qt version.
 */

import React from 'react';
import { QueueItem } from '../types/queueServerTypes';

interface PlanQueueProps {
  planQueue: QueueItem[];
  runningItemUid?: string | null;
  onItemSelect?: (item: QueueItem) => void;
  onItemEdit?: (item: QueueItem) => void;
  onItemRemove?: (uid: string) => void;
  onItemMove?: (uid: string, direction: 'up' | 'down') => void;
  readOnly?: boolean;
}

export const PlanQueue: React.FC<PlanQueueProps> = ({
  planQueue,
  runningItemUid,
  onItemSelect,
  onItemEdit,
  onItemRemove,
  onItemMove,
  readOnly = false
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

  const getItemStyle = (item: QueueItem) => ({
    padding: '8px 12px',
    border: '1px solid #ddd',
    borderRadius: '4px',
    marginBottom: '4px',
    backgroundColor: item.item_uid === runningItemUid ? '#e3f2fd' : '#fff',
    cursor: onItemSelect ? 'pointer' : 'default',
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center'
  });

  return (
    <div className="plan-queue" style={{
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
        fontSize: '14px',
        position: 'sticky',
        top: 0
      }}>
        Plan Queue ({planQueue.length} items)
      </div>

      {planQueue.length === 0 ? (
        <div style={{
          padding: '20px',
          textAlign: 'center',
          color: '#6c757d',
          fontStyle: 'italic'
        }}>
          No plans in queue
        </div>
      ) : (
        <div style={{ padding: '8px' }}>
          {planQueue.map((item, index) => (
            <div
              key={item.item_uid}
              style={getItemStyle(item)}
              onClick={() => onItemSelect?.(item)}
            >
              <div style={{ flex: 1 }}>
                <div style={{ fontWeight: 'bold', fontSize: '14px' }}>
                  {index + 1}. {item.name}
                </div>
                
                {(item.args.length > 0 || Object.keys(item.kwargs).length > 0) && (
                  <div style={{ fontSize: '12px', color: '#6c757d', marginTop: '2px' }}>
                    {formatArgs(item.args)}
                    {item.args.length > 0 && Object.keys(item.kwargs).length > 0 && ', '}
                    {formatKwargs(item.kwargs)}
                  </div>
                )}
                
                <div style={{ fontSize: '11px', color: '#868e96', marginTop: '2px' }}>
                  User: {item.user} | UID: {item.item_uid.slice(0, 8)}...
                </div>
              </div>

              {!readOnly && (
                <div style={{ display: 'flex', gap: '4px', marginLeft: '8px' }}>
                  {/* Move buttons */}
                  <button
                    style={{
                      padding: '2px 6px',
                      fontSize: '10px',
                      border: '1px solid #ccc',
                      borderRadius: '3px',
                      backgroundColor: '#fff',
                      cursor: 'pointer'
                    }}
                    onClick={(e) => {
                      e.stopPropagation();
                      onItemMove?.(item.item_uid, 'up');
                    }}
                    disabled={index === 0}
                    title="Move up"
                  >
                    ↑
                  </button>
                  <button
                    style={{
                      padding: '2px 6px',
                      fontSize: '10px',
                      border: '1px solid #ccc',
                      borderRadius: '3px',
                      backgroundColor: '#fff',
                      cursor: 'pointer'
                    }}
                    onClick={(e) => {
                      e.stopPropagation();
                      onItemMove?.(item.item_uid, 'down');
                    }}
                    disabled={index === planQueue.length - 1}
                    title="Move down"
                  >
                    ↓
                  </button>
                  
                  {/* Edit button */}
                  <button
                    style={{
                      padding: '2px 6px',
                      fontSize: '10px',
                      border: '1px solid #007bff',
                      borderRadius: '3px',
                      backgroundColor: '#007bff',
                      color: '#fff',
                      cursor: 'pointer'
                    }}
                    onClick={(e) => {
                      e.stopPropagation();
                      onItemEdit?.(item);
                    }}
                    title="Edit"
                  >
                    ✎
                  </button>
                  
                  {/* Remove button */}
                  <button
                    style={{
                      padding: '2px 6px',
                      fontSize: '10px',
                      border: '1px solid #dc3545',
                      borderRadius: '3px',
                      backgroundColor: '#dc3545',
                      color: '#fff',
                      cursor: 'pointer'
                    }}
                    onClick={(e) => {
                      e.stopPropagation();
                      if (window.confirm(`Remove plan "${item.name}" from queue?`)) {
                        onItemRemove?.(item.item_uid);
                      }
                    }}
                    title="Remove"
                  >
                    ✕
                  </button>
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

export default PlanQueue;
