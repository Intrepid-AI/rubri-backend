import { useState, useEffect, useRef, useCallback } from 'react';
import type { WebSocketMessage, ProgressUpdate } from '../types/api';
import { webSocketManager, type ConnectionStatus, type StreamEvent } from '../utils/WebSocketManager';

interface UseWebSocketProps {
  taskId?: string;
  enabled?: boolean;
  onProgressUpdate?: (progress: ProgressUpdate) => void;
  onTaskCompleted?: (data: any) => void;
  onError?: (error: string) => void;
  onStreamEvent?: (event: StreamEvent) => void;
  onStreamBatch?: (events: StreamEvent[]) => void;
}

interface UseWebSocketReturn {
  connectionStatus: ConnectionStatus;
  lastMessage: WebSocketMessage | null;
  sendMessage: (message: string) => void;
  disconnect: () => void;
  reconnect: () => void;
}

export const useWebSocket = ({
  taskId,
  enabled = true,
  onProgressUpdate,
  onTaskCompleted,
  onError,
  onStreamEvent,
  onStreamBatch
}: UseWebSocketProps): UseWebSocketReturn => {
  const [connectionStatus, setConnectionStatus] = useState<ConnectionStatus>('disconnected');
  const [lastMessage, setLastMessage] = useState<WebSocketMessage | null>(null);
  const currentTaskIdRef = useRef<string | null>(null);
  const isConnectingRef = useRef<boolean>(false);
  const callbacksRef = useRef({ onProgressUpdate, onTaskCompleted, onError, onStreamEvent, onStreamBatch });

  // Update callbacks ref when they change
  useEffect(() => {
    callbacksRef.current = { onProgressUpdate, onTaskCompleted, onError, onStreamEvent, onStreamBatch };
  }, [onProgressUpdate, onTaskCompleted, onError, onStreamEvent, onStreamBatch]);

  const sendMessage = useCallback((message: string) => {
    if (taskId) {
      webSocketManager.sendMessage(taskId, message);
    }
  }, [taskId]);

  const disconnect = useCallback(() => {
    if (currentTaskIdRef.current) {
      webSocketManager.disconnect(currentTaskIdRef.current);
      currentTaskIdRef.current = null;
    }
    isConnectingRef.current = false;
    setConnectionStatus('disconnected');
  }, []);

  const reconnect = useCallback(() => {
    if (taskId && enabled && !isConnectingRef.current) {
      disconnect();
      setTimeout(() => {
        if (taskId && !isConnectingRef.current) {
          currentTaskIdRef.current = taskId;
          isConnectingRef.current = true;
          webSocketManager.connect({
            taskId,
            onProgressUpdate: (progress) => {
              callbacksRef.current.onProgressUpdate?.(progress);
              setLastMessage({
                type: 'progress_update',
                task_id: taskId,
                data: progress
              });
            },
            onTaskCompleted: (data) => {
              callbacksRef.current.onTaskCompleted?.(data);
              setLastMessage({
                type: 'task_completed',
                task_id: taskId,
                data
              });
              isConnectingRef.current = false;
            },
            onError: (error) => {
              callbacksRef.current.onError?.(error);
              isConnectingRef.current = false;
            },
            onStreamEvent: (event) => {
              callbacksRef.current.onStreamEvent?.(event);
              setLastMessage({
                type: 'stream_event',
                task_id: taskId,
                data: null,
                event
              });
            },
            onStreamBatch: (events) => {
              callbacksRef.current.onStreamBatch?.(events);
              setLastMessage({
                type: 'stream_batch',
                task_id: taskId,
                data: null,
                events
              });
            },
            onStatusChange: setConnectionStatus
          });
        }
      }, 1000);
    }
  }, [taskId, enabled, disconnect]);

  // Main effect to manage connection - only depends on taskId and enabled
  useEffect(() => {
    if (taskId && enabled && !isConnectingRef.current) {
      // Only connect if not already connected to this task
      if (currentTaskIdRef.current !== taskId) {
        // Disconnect from previous task if any
        if (currentTaskIdRef.current) {
          webSocketManager.disconnect(currentTaskIdRef.current);
        }

        currentTaskIdRef.current = taskId;
        isConnectingRef.current = true;
        
        // Add small delay to ensure backend task is initialized
        setTimeout(() => {
          webSocketManager.connect({
            taskId,
            onProgressUpdate: (progress) => {
              callbacksRef.current.onProgressUpdate?.(progress);
              setLastMessage({
                type: 'progress_update',
                task_id: taskId,
                data: progress
              });
            },
            onTaskCompleted: (data) => {
              callbacksRef.current.onTaskCompleted?.(data);
              setLastMessage({
                type: 'task_completed',
                task_id: taskId,
                data
              });
              isConnectingRef.current = false;
            },
            onError: (error) => {
              callbacksRef.current.onError?.(error);
              isConnectingRef.current = false;
            },
            onStreamEvent: (event) => {
              callbacksRef.current.onStreamEvent?.(event);
              setLastMessage({
                type: 'stream_event',
                task_id: taskId,
                data: null,
                event
              });
            },
            onStreamBatch: (events) => {
              callbacksRef.current.onStreamBatch?.(events);
              setLastMessage({
                type: 'stream_batch',
                task_id: taskId,
                data: null,
                events
              });
            },
            onStatusChange: setConnectionStatus
          });
        }, 500); // 500ms delay to ensure backend is ready
      }
    } else if (!enabled) {
      disconnect();
    }

    // Cleanup on unmount
    return () => {
      if (currentTaskIdRef.current) {
        webSocketManager.disconnect(currentTaskIdRef.current);
        currentTaskIdRef.current = null;
      }
      isConnectingRef.current = false;
    };
  }, [taskId, enabled]); // Only taskId and enabled as dependencies

  return {
    connectionStatus,
    lastMessage,
    sendMessage,
    disconnect,
    reconnect
  };
};