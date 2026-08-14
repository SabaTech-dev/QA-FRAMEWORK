# QA-FRAMEWORK - Notification System API

**Created:** 2026-03-10 07:42 UTC
**Status:** ✅ READY

---

## API Endpoints

### GET /api/v1/notifications
**Description:** Get all notifications for current user
**Auth:** Required
**Query params:**
- `unread_only` (bool): Filter unread notifications
- `limit` (int): Max results (default: 50)
- `offset` (int): Pagination offset

**Response:**
```json
{
  "notifications": [
    {
      "id": "uuid",
      "type": "test_completed" | "test_failed" | "suite_created" | "billing" | "system",
      "title": "Test Suite Completed",
      "message": "Login Flow Test completed with 100% pass rate",
      "data": {
        "suite_id": 123,
        "execution_id": 456
      },
      "read": false,
      "created_at": "2026-03-10T07:00:00Z"
    }
  ],
  "total": 10,
  "unread_count": 3
}
```

### POST /api/v1/notifications/:id/read
**Description:** Mark notification as read
**Auth:** Required

**Response:**
```json
{
  "success": true
}
```

### POST /api/v1/notifications/read-all
**Description:** Mark all notifications as read
**Auth:** Required

**Response:**
```json
{
  "updated_count": 5
}
```

### DELETE /api/v1/notifications/:id
**Description:** Delete notification
**Auth:** Required

**Response:**
```json
{
  "success": true
}
```

---

## WebSocket Events

### notifications:new
**Payload:**
```json
{
  "notification": {
    "id": "uuid",
    "type": "test_completed",
    "title": "...",
    "message": "...",
    "data": {},
    "created_at": "..."
  }
}
```

---

## Database Schema

```sql
CREATE TABLE notifications (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    type VARCHAR(50) NOT NULL,
    title VARCHAR(255) NOT NULL,
    message TEXT NOT NULL,
    data JSONB DEFAULT '{}',
    read BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_notifications_user_id ON notifications(user_id);
CREATE INDEX idx_notifications_read ON notifications(user_id, read);
CREATE INDEX idx_notifications_created ON notifications(created_at DESC);
```

---

## Implementation Ready
- ✅ API endpoints defined
- ✅ Database schema ready
- ✅ WebSocket events specified
- ⏳ Backend implementation pending
