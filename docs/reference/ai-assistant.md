# QA-FRAMEWORK - AI Assistant API

**Created:** 2026-03-10 07:42 UTC
**Status:** ✅ READY

---

## API Endpoints

### POST /api/v1/ai/chat
**Description:** Send message to AI assistant
**Auth:** Required
**Body:**
```json
{
  "message": "Generate a test for login page",
  "context": {
    "suite_id": 123,
    "test_type": "e2e"
  }
}
```

**Response:**
```json
{
  "response": "I'll help you create a login page test...",
  "suggestions": [
    {
      "type": "test_code",
      "language": "typescript",
      "code": "test('login flow', async () => { ... })"
    }
  ],
  "conversation_id": "uuid"
}
```

### POST /api/v1/ai/generate-test
**Description:** Generate test from description
**Auth:** Required
**Body:**
```json
{
  "description": "Test user can login with valid credentials",
  "framework": "playwright",
  "suite_id": 123
}
```

**Response:**
```json
{
  "test": {
    "name": "User Login Test",
    "code": "...",
    "language": "typescript",
    "framework": "playwright"
  }
}
```

### POST /api/v1/ai/analyze-failure
**Description:** Analyze test failure and suggest fixes
**Auth:** Required
**Body:**
```json
{
  "execution_id": 456,
  "error_message": "Element not found: #username",
  "stack_trace": "..."
}
```

**Response:**
```json
{
  "analysis": "The username selector has changed",
  "suggestions": [
    {
      "type": "selector_fix",
      "old_selector": "#username",
      "new_selector": "input[name='username']",
      "confidence": 0.95
    }
  ]
}
```

---

## Implementation Notes

- Use OpenAI API or local LLM (Ollama)
- Store conversation history in Redis
- Rate limit: 50 requests/hour per user
- Cache common responses
- Streaming responses for long generations

---

## Implementation Ready
- ✅ API endpoints defined
- ⏳ Backend implementation pending
- ⏳ LLM integration pending
