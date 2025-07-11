import type { WebSocketMessage, ProgressUpdate } from '../types/api';

export type ConnectionStatus = 'connecting' | 'connected' | 'disconnected' | 'error';

interface WebSocketConnectionOptions {
  taskId: string;
  onProgressUpdate?: (progress: ProgressUpdate) => void;
  onTaskCompleted?: (data: any) => void;
  onError?: (error: string) => void;
  onStatusChange?: (status: ConnectionStatus) => void;
}

class WebSocketManager {
  private connections: Map<string, WebSocket> = new Map();
  private callbacks: Map<string, WebSocketConnectionOptions> = new Map();
  private connectionAttempts: Map<string, number> = new Map();
  private reconnectTimeouts: Map<string, ReturnType<typeof setTimeout>> = new Map();

  private getWebSocketUrl(taskId: string): string {
    const baseUrl = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';
    const wsUrl = baseUrl.replace(/^http/, 'ws');
    return `${wsUrl}/ws/progress/${taskId}`;
  }

  connect(options: WebSocketConnectionOptions): void {
    const { taskId } = options;
    
    // If already connected or connecting, just update callbacks
    if (this.connections.has(taskId)) {
      this.callbacks.set(taskId, options);
      console.log(`🔌 WebSocket for task ${taskId} already exists, updating callbacks`);
      return;
    }

    // Prevent too frequent connection attempts - increased to 2 seconds
    const lastAttempt = this.connectionAttempts.get(taskId) || 0;
    const now = Date.now();
    if (now - lastAttempt < 2000) {
      console.log(`🔌 WebSocket connection for task ${taskId} attempted too soon (${now - lastAttempt}ms ago), skipping`);
      return;
    }

    // Check total connection count
    if (this.connections.size >= 10) {
      console.warn(`🔌 Too many WebSocket connections (${this.connections.size}), rejecting new connection for task ${taskId}`);
      options.onError?.('Too many active connections');
      return;
    }

    this.connectionAttempts.set(taskId, now);
    this.callbacks.set(taskId, options);

    try {
      const wsUrl = this.getWebSocketUrl(taskId);
      console.log(`🔌 Connecting to WebSocket: ${wsUrl}`);
      
      options.onStatusChange?.('connecting');
      
      const ws = new WebSocket(wsUrl);
      this.connections.set(taskId, ws);

      ws.onopen = () => {
        console.log(`✅ WebSocket connected for task ${taskId}`);
        options.onStatusChange?.('connected');
        
        // Send ping to keep connection alive
        if (ws.readyState === WebSocket.OPEN) {
          ws.send('ping');
        }
      };

      ws.onmessage = (event) => {
        this.handleMessage(taskId, event);
      };

      ws.onclose = (event) => {
        console.log(`🔌 WebSocket closed for task ${taskId}: Code ${event.code}, Reason: ${event.reason}`);
        this.connections.delete(taskId);
        options.onStatusChange?.('disconnected');

        // Attempt to reconnect if it wasn't a manual close
        if (event.code !== 1000 && event.code !== 4009) { // Don't reconnect if manually closed or limit reached
          this.scheduleReconnect(taskId);
        }
      };

      ws.onerror = (error) => {
        console.error(`❌ WebSocket error for task ${taskId}:`, error);
        options.onStatusChange?.('error');
        options.onError?.('WebSocket connection error');
      };

    } catch (error) {
      console.error(`❌ Failed to create WebSocket for task ${taskId}:`, error);
      options.onStatusChange?.('error');
      options.onError?.('Failed to create WebSocket connection');
    }
  }

  private handleMessage(taskId: string, event: MessageEvent): void {
    try {
      const message: WebSocketMessage = JSON.parse(event.data);
      const callbacks = this.callbacks.get(taskId);

      if (!callbacks) return;

      switch (message.type) {
        case 'progress_update':
          callbacks.onProgressUpdate?.(message.data as ProgressUpdate);
          break;
          
        case 'task_completed':
          callbacks.onTaskCompleted?.(message.data);
          // Auto-disconnect after task completion
          setTimeout(() => this.disconnect(taskId), 1000);
          break;
          
        case 'error':
          callbacks.onError?.(message.data.error || 'Unknown WebSocket error');
          break;
          
        default:
          console.log(`Unknown WebSocket message type for task ${taskId}:`, message.type);
      }
    } catch (error) {
      console.error(`Error parsing WebSocket message for task ${taskId}:`, error);
      const callbacks = this.callbacks.get(taskId);
      callbacks?.onError?.('Failed to parse WebSocket message');
    }
  }

  private scheduleReconnect(taskId: string): void {
    // Clear any existing reconnect timeout
    const existingTimeout = this.reconnectTimeouts.get(taskId);
    if (existingTimeout) {
      clearTimeout(existingTimeout);
    }

    // Schedule reconnect after 2 seconds
    const timeout = setTimeout(() => {
      const callbacks = this.callbacks.get(taskId);
      if (callbacks && !this.connections.has(taskId)) {
        console.log(`🔄 Attempting to reconnect WebSocket for task ${taskId}`);
        this.connect(callbacks);
      }
      this.reconnectTimeouts.delete(taskId);
    }, 2000);

    this.reconnectTimeouts.set(taskId, timeout);
  }

  disconnect(taskId: string): void {
    const ws = this.connections.get(taskId);
    const timeout = this.reconnectTimeouts.get(taskId);

    if (timeout) {
      clearTimeout(timeout);
      this.reconnectTimeouts.delete(taskId);
    }

    if (ws) {
      ws.close(1000, 'Manual disconnect');
      this.connections.delete(taskId);
    }

    this.callbacks.delete(taskId);
    this.connectionAttempts.delete(taskId);
    
    console.log(`🔌 Disconnected WebSocket for task ${taskId}`);
  }

  sendMessage(taskId: string, message: string): void {
    const ws = this.connections.get(taskId);
    if (ws && ws.readyState === WebSocket.OPEN) {
      ws.send(message);
    } else {
      console.warn(`WebSocket for task ${taskId} is not connected. Cannot send message:`, message);
    }
  }

  getConnectionStatus(taskId: string): ConnectionStatus {
    const ws = this.connections.get(taskId);
    if (!ws) return 'disconnected';

    switch (ws.readyState) {
      case WebSocket.CONNECTING:
        return 'connecting';
      case WebSocket.OPEN:
        return 'connected';
      case WebSocket.CLOSING:
      case WebSocket.CLOSED:
        return 'disconnected';
      default:
        return 'error';
    }
  }

  // Cleanup all connections
  disconnectAll(): void {
    const taskIds = Array.from(this.connections.keys());
    taskIds.forEach(taskId => this.disconnect(taskId));
  }
}

// Export singleton instance
export const webSocketManager = new WebSocketManager();