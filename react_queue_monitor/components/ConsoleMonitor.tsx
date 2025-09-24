/**
 * Console Monitor Component
 * 
 * Displays real-time console output from the Queue Server,
 * equivalent to QtReConsoleMonitor in the Qt version.
 */

import React, { useEffect, useRef } from 'react';
import { ConsoleOutput } from '../types/queueServerTypes';

interface ConsoleMonitorProps {
  consoleOutput: ConsoleOutput[];
  maxLines?: number;
  autoScroll?: boolean;
}

export const ConsoleMonitor: React.FC<ConsoleMonitorProps> = ({ 
  consoleOutput, 
  maxLines = 1000,
  autoScroll = true
}) => {
  const containerRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to bottom when new messages arrive
  useEffect(() => {
    if (autoScroll && containerRef.current) {
      containerRef.current.scrollTop = containerRef.current.scrollHeight;
    }
  }, [consoleOutput, autoScroll]);

  const getMessageStyle = (msgType: string) => {
    const baseStyle = {
      fontSize: '12px',
      fontFamily: 'monospace',
      padding: '2px 4px',
      margin: '1px 0',
      whiteSpace: 'pre-wrap' as const,
      wordBreak: 'break-word' as const
    };

    switch (msgType) {
      case 'ERROR':
        return { ...baseStyle, color: '#dc3545', backgroundColor: '#f8d7da' };
      case 'WARNING':
        return { ...baseStyle, color: '#856404', backgroundColor: '#fff3cd' };
      case 'INFO':
        return { ...baseStyle, color: '#0c5460', backgroundColor: '#d1ecf1' };
      default:
        return { ...baseStyle, color: '#495057' };
    }
  };

  const formatTime = (timeStr: string): string => {
    try {
      return new Date(timeStr).toLocaleTimeString([], { 
        hour12: false, 
        hour: '2-digit', 
        minute: '2-digit', 
        second: '2-digit' 
      });
    } catch {
      return timeStr;
    }
  };

  // Limit the number of displayed messages for performance
  const displayedMessages = consoleOutput.slice(-maxLines);

  return (
    <div className="console-monitor" style={{
      border: '1px solid #ddd',
      borderRadius: '6px',
      backgroundColor: '#fff',
      height: '200px',
      display: 'flex',
      flexDirection: 'column'
    }}>
      <div style={{
        padding: '8px 12px',
        borderBottom: '1px solid #eee',
        backgroundColor: '#f8f9fa',
        fontWeight: 'bold',
        fontSize: '14px',
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center'
      }}>
        <span>Console Output</span>
        <div style={{ fontSize: '12px', fontWeight: 'normal', color: '#6c757d' }}>
          {displayedMessages.length} / {maxLines} lines
        </div>
      </div>

      <div 
        ref={containerRef}
        style={{
          flex: 1,
          overflow: 'auto',
          padding: '4px',
          backgroundColor: '#f9f9f9'
        }}
      >
        {displayedMessages.length === 0 ? (
          <div style={{
            padding: '20px',
            textAlign: 'center',
            color: '#6c757d',
            fontStyle: 'italic'
          }}>
            No console output
          </div>
        ) : (
          displayedMessages.map((output, index) => (
            <div key={index} style={getMessageStyle(output.msg_type)}>
              <span style={{ 
                color: '#6c757d', 
                marginRight: '8px',
                fontSize: '10px'
              }}>
                [{formatTime(output.time)}]
              </span>
              {output.msg_type !== 'PRINT' && (
                <span style={{ 
                  fontWeight: 'bold',
                  marginRight: '8px'
                }}>
                  {output.msg_type}:
                </span>
              )}
              <span>{output.msg}</span>
            </div>
          ))
        )}
      </div>

      {/* Control bar */}
      <div style={{
        padding: '4px 8px',
        borderTop: '1px solid #eee',
        backgroundColor: '#f8f9fa',
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center'
      }}>
        <div style={{ fontSize: '11px', color: '#6c757d' }}>
          Auto-scroll: {autoScroll ? 'ON' : 'OFF'}
        </div>
        <div style={{ display: 'flex', gap: '4px' }}>
          <button
            style={{
              padding: '2px 8px',
              fontSize: '10px',
              border: '1px solid #ccc',
              borderRadius: '3px',
              backgroundColor: '#fff',
              cursor: 'pointer'
            }}
            onClick={() => {
              if (containerRef.current) {
                containerRef.current.scrollTop = containerRef.current.scrollHeight;
              }
            }}
            title="Scroll to bottom"
          >
            ⬇
          </button>
          <button
            style={{
              padding: '2px 8px',
              fontSize: '10px',
              border: '1px solid #ccc',
              borderRadius: '3px',
              backgroundColor: '#fff',
              cursor: 'pointer'
            }}
            onClick={() => {
              // This would be handled by parent component
              console.log('Clear console output');
            }}
            title="Clear output"
          >
            🗑
          </button>
        </div>
      </div>
    </div>
  );
};

export default ConsoleMonitor;
