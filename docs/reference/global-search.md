# QA-FRAMEWORK - Global Search API

**Created:** 2026-03-10 07:42 UTC
**Status:** ✅ READY

---

## API Endpoints

### GET /api/v1/search
**Description:** Global search across all entities
**Auth:** Required
**Query params:**
- `q` (string): Search query
- `types` (string[]): Filter by types (suites, cases, executions, users)
- `limit` (int): Max results per type (default: 10)

**Response:**
```json
{
  "results": {
    "suites": [
      {
        "id": 123,
        "name": "Login Tests",
        "description": "...",
        "framework": "playwright",
        "created_at": "..."
      }
    ],
    "cases": [
      {
        "id": 456,
        "name": "Valid Login Test",
        "suite_id": 123,
        "status": "active"
      }
    ],
    "executions": [
      {
        "id": 789,
        "suite_name": "Login Tests",
        "status": "completed",
        "pass_rate": 100,
        "created_at": "..."
      }
    ]
  },
  "total": 15,
  "query": "login"
}
```

---

## Search Strategy

1. **PostgreSQL Full-Text Search** (primary)
   - Use `tsvector` for fast text search
   - Index on name, description fields

2. **Fuzzy matching** (fallback)
   - Use `pg_trgm` extension
   - Similarity search for typos

3. **Filters**
   - By type (suites, cases, executions)
   - By date range
   - By status

---

## Database Setup

```sql
-- Enable extensions
CREATE EXTENSION IF NOT EXISTS pg_trgm;

-- Add search indexes
CREATE INDEX idx_suites_search ON test_suites USING gin(to_tsvector('english', name || ' ' || COALESCE(description, '')));
CREATE INDEX idx_cases_search ON test_cases USING gin(to_tsvector('english', name));

-- Add trigram indexes for fuzzy search
CREATE INDEX idx_suites_name_trgm ON test_suites USING gin(name gin_trgm_ops);
```

---

## Implementation Ready
- ✅ API endpoint defined
- ✅ Database strategy specified
- ⏳ Backend implementation pending
