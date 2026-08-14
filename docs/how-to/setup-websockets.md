# QA-FRAMEWORK - WebSocket Setup Guide

**Created:** 2026-03-10 07:47 UTC
**Status:** ✅ READY

---

## Overview

Real-time notifications using WebSocket for instant updates when:
- Test suite completes
- Test execution fails
- New test suite created
- Billing events occur
- System notifications

---

## Backend Implementation

### 1. WebSocket Manager
**File:** `dashboard/backend/websocket/manager.py`
**Features:**
- Connection management per user
- Broadcast to all users
- Personal messages
- Auto-reconnect handling

### 2. WebSocket Endpoint
**File:** `dashboard/backend/api/v1/websocket.py`
**Endpoint:** `/api/v1/ws/notifications`
**Protocol:**
```json
// Client → Server (Auth)
{
  "type": "auth",
  "token": "jwt_token_here"
}

// Server → Client (Connected)
{
  "type": "connected",
  "message": "WebSocket connected successfully",
  "user_id": 123
}

// Server → Client (New Notification)
{
  "type": "notifications:new",
  "notification": {
    "id": "uuid",
    "type": "test_completed",
    "title": "...",
    "message": "...",
    "data": {},
    "created_at": "..."
  }
}

// Client → Server (Keepalive)
{
  "type": "ping"
}

// Server → Client (Keepalive Response)
{
  "type": "pong"
}
```

---

## Frontend Implementation

### 1. WebSocket Hook
**File:** `dashboard/frontend/src/hooks/useNotificationsWebSocket.ts`
**Usage:**
```tsx
import { useNotificationsWebSocket } from '../hooks/useNotificationsWebSocket';

function App() {
  const { isConnected } = useNotificationsWebSocket({
    token: userToken,
    onNotification: (notification) => {
      // Show toast or update UI
      toast.success(notification.title);
    },
    onConnect: () => {
      console.log('WebSocket connected');
    },
    onDisconnect: () => {
      console.log('WebSocket disconnected');
    },
  });

  return (
    <div>
      {isConnected ? '🟢 Connected' : '🔴 Disconnected'}
    </div>
  );
}
```

### 2. Integration in NotificationDropdown
```tsx
// In NotificationDropdown component
const { isConnected } = useNotificationsWebSocket({
  token: authStore.token,
  onNotification: (notification) => {
    // Add to notifications list
    setNotifications(prev => [notification, ...prev]);

    // Show toast
    toast.custom((t) => (
      <div onClick={() => toast.dismiss(t.id)}>
        <strong>{notification.title}</strong>
        <p>{notification.message}</p>
      </div>
    ));
  },
});
```

---

## Sending Notifications from Backend

### Example: Test Suite Completed
```python
from websocket.manager import manager
from services.notification_service import NotificationService

async def on_test_suite_completed(
    db: AsyncSession,
    user_id: int,
    suite_name: str,
    suite_id: int,
    execution_id: int,
    pass_rate: float
):
    # Create notification in DB
    notification = await NotificationService.create_test_completed_notification(
        db=db,
        user_id=user_id,
        suite_name=suite_name,
        suite_id=suite_id,
        execution_id=execution_id,
        pass_rate=pass_rate
    )

    # Send real-time notification via WebSocket
    await manager.send_notification(
        user_id=user_id,
        notification=notification.to_dict()
    )
```

---

## Testing WebSocket

### 1. Manual Testing with wscat
```bash
# Install wscat
npm install -g wscat

# Connect
wscat -c ws://localhost:8000/api/v1/ws/notifications

# Send auth message
> {"type":"auth","token":"your_jwt_token"}

# Receive notifications
< {"type":"connected","message":"...","user_id":1}
< {"type":"notifications:new","notification":{...}}
```

### 2. Testing in Browser Console
```javascript
const ws = new WebSocket('ws://localhost:8000/api/v1/ws/notifications');

ws.onopen = () => {
  console.log('Connected');
  ws.send(JSON.stringify({
    type: 'auth',
    token: 'your_jwt_token'
  }));
};

ws.onmessage = (event) => {
  console.log('Message:', JSON.parse(event.data));
};
```

---

## Production Considerations

### 1. Scaling WebSockets
For multi-instance deployments:
- Use Redis Pub/Sub for cross-instance messaging
- Each instance subscribes to Redis channel
- When notification created, publish to Redis
- All instances receive and send to connected clients

**Implementation:**
```python
import redis.asyncio as redis

redis_client = redis.from_url("redis://localhost:6379")

async def publish_notification(user_id: int, notification: dict):
    await redis_client.publish(
        f"notifications:{user_id}",
        json.dumps(notification)
    )

async def subscribe_to_notifications():
    pubsub = redis_client.pubsub()
    await pubsub.subscribe("notifications:*")

    async for message in pubsub.listen():
        if message["type"] == "message":
            data = json.loads(message["data"])
            user_id = extract_user_id(message["channel"])
            await manager.send_notification(user_id, data)
```

### 2. Security
- Always authenticate WebSocket connections
- Validate JWT token before accepting connection
- Rate limit messages
- Sanitize all incoming data

### 3. Monitoring
- Log connection counts
- Monitor message throughput
- Alert on connection failures
- Track reconnection rates

---

## Deployment Checklist

- [ ] Enable WebSocket support in load balancer (sticky sessions)
- [ ] Configure CORS for WebSocket
- [ ] Set up Redis for multi-instance support
- [ ] Add WebSocket monitoring
- [ ] Test with production-like load
- [ ] Document WebSocket endpoints in API docs

---

## Status

- ✅ Backend WebSocket manager created
- ✅ Backend WebSocket endpoint created
- ✅ Frontend hook created
- ⏳ Integration in NotificationDropdown (pending by subagent)
- ⏳ Redis Pub/Sub (optional for scaling)
- ⏳ Production deployment (pending)

---

*Implementation guide by Alfred (CEO Agent)*
*Date: 2026-03-10 07:47 UTC*
