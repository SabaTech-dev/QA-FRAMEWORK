// Frontend WebSocket client for real-time notifications.
import { useEffect, useRef, useState } from 'react';

interface Notification {
  id: string;
  type: string;
  title: string;
  message: string;
  data: any;
  read: boolean;
  created_at: string;
}

interface UseWebSocketOptions {
  token: string | null;
  onNotification?: (notification: Notification) => void;
  onConnect?: () => void;
  onDisconnect?: () => void;
  onError?: (error: Error) => void;
}

interface WebSocketMessage {
  type: string;
  [key: string]: any;
}

export function useNotificationsWebSocket({
  token,
  onNotification,
  onConnect,
  onDisconnect,
  onError,
}: UseWebSocketOptions) {
  const wsRef = useRef<WebSocket | null>(null);
  const [isConnected, setIsConnected] = useState(false);
  const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null);

  useEffect(() => {
    if (!token) {
      return;
    }

    const connect = () => {
      try {
        // Use wss:// for production, ws:// for development
        const wsUrl = import.meta.env.PROD
          ? `wss://${window.location.host}/api/v1/ws/notifications`
          : `ws://localhost:8000/api/v1/ws/notifications`;

        wsRef.current = new WebSocket(wsUrl);

        wsRef.current.onopen = async () => {
          console.log('WebSocket connected');

          // Send authentication
          wsRef.current?.send(JSON.stringify({
            type: 'auth',
            token: token,
          }));

          // Start keepalive ping
          const keepalive = setInterval(() => {
            if (wsRef.current?.readyState === WebSocket.OPEN) {
              wsRef.current?.send(JSON.stringify({ type: 'ping' }));
            }
          }, 30000); // Ping every 30 seconds

          // Store interval for cleanup
          wsRef.current.addEventListener('close', () => {
            clearInterval(keepalive);
          });
        };

        wsRef.current.onmessage = (event) => {
          const message: WebSocketMessage = JSON.parse(event.data);

          switch (message.type) {
            case 'connected':
              setIsConnected(true);
              onConnect?.();
              break;

            case 'notifications:new':
              if (message.notification) {
                onNotification?.(message.notification);
              }
              break;

            case 'pong':
              // Keepalive response
              break;

            case 'error':
              console.error('WebSocket error:', message.message);
              onError?.(new Error(message.message));
              break;

            default:
              console.log('Unknown WebSocket message:', message);
          }
        };

        wsRef.current.onerror = (error) => {
          console.error('WebSocket error:', error);
          onError?.(new Error('WebSocket connection error'));
        };

        wsRef.current.onclose = () => {
          console.log('WebSocket disconnected');
          setIsConnected(false);
          onDisconnect?.();

          // Attempt to reconnect after 5 seconds
          reconnectTimeoutRef.current = setTimeout(() => {
            console.log('Attempting to reconnect WebSocket...');
            connect();
          }, 5000);
        };

      } catch (error) {
        console.error('Failed to create WebSocket:', error);
        onError?.(error as Error);
      }
    };

    connect();

    // Cleanup on unmount
    return () => {
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
      }
      if (wsRef.current) {
        wsRef.current.close();
      }
    };
  }, [token, onNotification, onConnect, onDisconnect, onError]);

  const sendMessage = (message: WebSocketMessage) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify(message));
    }
  };

  const subscribe = (channel: string) => {
    sendMessage({ type: 'subscribe', channel });
  };

  return {
    isConnected,
    sendMessage,
    subscribe,
  };
}
