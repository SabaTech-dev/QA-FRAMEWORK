# Browser-Use Integration - Implementation Plan

**Goal:** Integrar Browser-Use como motor de test automation con AI en QA-FRAMEWORK
**Design Doc:** `docs/specs/2026-03-25-browser-use-integration-design.md`
**Architecture:** FastAPI endpoints → BrowserUseService → Browser-Use Agent (Groq LLM + Playwright)
**Tech Stack:** browser-use, langchain-groq, FastAPI, Playwright
**Estimated Tasks:** 12 tasks (~2-5 min each)

---

## Task 1: Install Dependencies

**Files:**
- Modify: `dashboard/backend/requirements.txt`

### Steps

- [ ] **Step 1: Add browser-use dependencies**
Add to `dashboard/backend/requirements.txt`:
```
browser-use>=0.1.0
langchain-groq>=0.1.0
```

- [ ] **Step 2: Install dependencies**
Run: `cd /home/ubuntu/qa-framework/dashboard/backend && pip install -r requirements.txt --break-system-packages`
Expected: Successfully installed browser-use-X.X.X langchain-groq-X.X.X

- [ ] **Step 3: Verify installation**
Run: `python3 -c "from browser_use import Agent; from langchain_groq import ChatGroq; print('OK')"`
Expected: `OK`

---

## Task 2: Add Environment Variables

**Files:**
- Modify: `dashboard/backend/.env.example`
- Modify: `dashboard/backend/config.py`

### Steps

- [ ] **Step 1: Add GROQ_API_KEY to .env.example**
Add to `dashboard/backend/.env.example`:
```
# Browser-Use LLM Configuration
GROQ_API_KEY=your_groq_api_key_here
BROWSER_USE_LLM_PROVIDER=groq
BROWSER_USE_MODEL=llama-3.3-70b-versatile
```

- [ ] **Step 2: Add config fields to config.py**
Add to `dashboard/backend/config.py` (in the Settings class):
```python
    # Browser-Use Configuration
    GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "")
    BROWSER_USE_LLM_PROVIDER: str = os.getenv("BROWSER_USE_LLM_PROVIDER", "groq")
    BROWSER_USE_MODEL: str = os.getenv("BROWSER_USE_MODEL", "llama-3.3-70b-versatile")
```

- [ ] **Step 3: Verify config loads**
Run: `cd /home/ubuntu/qa-framework/dashboard/backend && python3 -c "from config import settings; print(f'LLM Provider: {settings.BROWSER_USE_LLM_PROVIDER}')"`
Expected: `LLM Provider: groq`

---

## Task 3: Create BrowserUseTask Model

**Files:**
- Create: `dashboard/backend/models/browser_use_task.py`
- Modify: `dashboard/backend/models/__init__.py`

### Steps

- [ ] **Step 1: Write failing test**
Create `dashboard/backend/tests/test_browser_use_task.py`:
```python
"""Tests for BrowserUseTask model."""
import pytest
from models.browser_use_task import BrowserUseTask, TaskStatus


def test_browser_use_task_creation():
    """Test creating a BrowserUseTask instance."""
    task = BrowserUseTask(
        task_id="bu_test123",
        prompt="Login to app",
        url="https://example.com",
        status=TaskStatus.PENDING,
        user_id=1
    )
    assert task.task_id == "bu_test123"
    assert task.status == TaskStatus.PENDING
```

- [ ] **Step 2: Verify test fails**
Run: `cd /home/ubuntu/qa-framework/dashboard/backend && python3 -m pytest tests/test_browser_use_task.py -v`
Expected: FAIL with "ModuleNotFoundError: No module named 'models.browser_use_task'"

- [ ] **Step 3: Create the model**
Create `dashboard/backend/models/browser_use_task.py`:
```python
"""Browser-Use Task Model."""
from sqlalchemy import Column, Integer, String, Text, Enum, DateTime, JSON
from sqlalchemy.sql import func
from database import Base
import enum


class TaskStatus(str, enum.Enum):
    """Task execution status."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class BrowserUseTask(Base):
    """Browser-Use task execution record."""
    __tablename__ = "browser_use_tasks"

    id = Column(Integer, primary_key=True, index=True)
    task_id = Column(String(50), unique=True, index=True, nullable=False)
    user_id = Column(Integer, index=True, nullable=False)
    prompt = Column(Text, nullable=False)
    url = Column(String(500), nullable=False)
    status = Column(Enum(TaskStatus), default=TaskStatus.PENDING, nullable=False)
    options = Column(JSON, nullable=True)
    result = Column(JSON, nullable=True)
    error_message = Column(Text, nullable=True)
    screenshots = Column(JSON, nullable=True)
    video_path = Column(String(500), nullable=True)
    duration_seconds = Column(Integer, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    completed_at = Column(DateTime(timezone=True), nullable=True)
```

- [ ] **Step 4: Export model**
Add to `dashboard/backend/models/__init__.py`:
```python
from models.browser_use_task import BrowserUseTask, TaskStatus
```

- [ ] **Step 5: Verify test passes**
Run: `cd /home/ubuntu/qa-framework/dashboard/backend && python3 -m pytest tests/test_browser_use_task.py -v`
Expected: PASS (1 passed)

---

## Task 4: Create BrowserUse Schemas

**Files:**
- Create: `dashboard/backend/schemas/browser_use.py`
- Modify: `dashboard/backend/schemas/__init__.py`

### Steps

- [ ] **Step 1: Write failing test**
Create `dashboard/backend/tests/test_browser_use_schemas.py`:
```python
"""Tests for BrowserUse schemas."""
import pytest
from schemas.browser_use import BrowserUseExecuteRequest, BrowserUseExecuteResponse


def test_execute_request_validation():
    """Test BrowserUseExecuteRequest validation."""
    request = BrowserUseExecuteRequest(
        prompt="Login to app",
        url="https://example.com"
    )
    assert request.prompt == "Login to app"
    assert request.url == "https://example.com"
    assert request.options is None


def test_execute_response():
    """Test BrowserUseExecuteResponse."""
    response = BrowserUseExecuteResponse(
        task_id="bu_test123",
        status="pending",
        message="Task created"
    )
    assert response.task_id == "bu_test123"
```

- [ ] **Step 2: Verify test fails**
Run: `cd /home/ubuntu/qa-framework/dashboard/backend && python3 -m pytest tests/test_browser_use_schemas.py -v`
Expected: FAIL with "ModuleNotFoundError"

- [ ] **Step 3: Create schemas**
Create `dashboard/backend/schemas/browser_use.py`:
```python
"""Browser-Use API Schemas."""
from pydantic import BaseModel, HttpUrl
from typing import Optional, List, Dict, Any
from datetime import datetime


class BrowserUseOptions(BaseModel):
    """Options for browser-use execution."""
    record_video: bool = False
    take_screenshots: bool = True
    max_steps: int = 50
    headless: bool = True


class BrowserUseExecuteRequest(BaseModel):
    """Request to execute a browser-use task."""
    prompt: str
    url: str
    options: Optional[BrowserUseOptions] = None


class BrowserUseExecuteResponse(BaseModel):
    """Response after creating a browser-use task."""
    task_id: str
    status: str
    message: str = "Task created successfully"
    created_at: Optional[datetime] = None


class BrowserUseStep(BaseModel):
    """Single step in browser-use execution."""
    action: str
    target: str
    success: bool
    timestamp: Optional[datetime] = None


class BrowserUseStatusResponse(BaseModel):
    """Response for task status."""
    task_id: str
    status: str
    progress: int = 0
    current_step: Optional[str] = None
    error: Optional[str] = None


class BrowserUseResultsResponse(BaseModel):
    """Response with full task results."""
    task_id: str
    status: str
    success: Optional[bool] = None
    steps: List[BrowserUseStep] = []
    screenshots: List[str] = []
    video: Optional[str] = None
    duration_seconds: Optional[float] = None
    error: Optional[str] = None
    completed_at: Optional[datetime] = None
```

- [ ] **Step 4: Export schemas**
Add to `dashboard/backend/schemas/__init__.py`:
```python
from schemas.browser_use import (
    BrowserUseOptions,
    BrowserUseExecuteRequest,
    BrowserUseExecuteResponse,
    BrowserUseStep,
    BrowserUseStatusResponse,
    BrowserUseResultsResponse,
)
```

- [ ] **Step 5: Verify test passes**
Run: `cd /home/ubuntu/qa-framework/dashboard/backend && python3 -m pytest tests/test_browser_use_schemas.py -v`
Expected: PASS (2 passed)

---

## Task 5: Create BrowserUseService (Core Logic)

**Files:**
- Create: `dashboard/backend/services/ai/browser_use_service.py`

### Steps

- [ ] **Step 1: Write failing test**
Create `dashboard/backend/tests/services/test_browser_use_service.py`:
```python
"""Tests for BrowserUseService."""
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from services.ai.browser_use_service import BrowserUseService


@pytest.fixture
def service():
    """Create BrowserUseService instance."""
    return BrowserUseService()


@pytest.mark.asyncio
async def test_service_initialization(service):
    """Test service initializes correctly."""
    assert service is not None
    assert hasattr(service, 'execute_task')
    assert hasattr(service, 'get_status')


@pytest.mark.asyncio
async def test_execute_task_returns_task_id(service):
    """Test execute_task returns a task ID."""
    task_id = await service.execute_task(
        prompt="Login to app",
        url="https://example.com",
        user_id=1,
        db=AsyncMock()
    )
    assert task_id.startswith("bu_")
    assert len(task_id) == 11  # "bu_" + 8 chars
```

- [ ] **Step 2: Verify test fails**
Run: `cd /home/ubuntu/qa-framework/dashboard/backend && python3 -m pytest tests/services/test_browser_use_service.py -v`
Expected: FAIL with "ModuleNotFoundError"

- [ ] **Step 3: Create the service**
Create `dashboard/backend/services/ai/browser_use_service.py`:
```python
"""Browser-Use Service - AI-Powered Test Automation."""
import asyncio
from typing import Optional, Dict, Any
from uuid import uuid4
from datetime import datetime
import json

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from models.browser_use_task import BrowserUseTask, TaskStatus
from config import settings
from core.logging_config import get_logger

logger = get_logger(__name__)


class BrowserUseService:
    """Service for executing browser-use tasks."""
    
    def __init__(self):
        self.active_tasks: Dict[str, asyncio.Task] = {}
        self._llm = None
    
    def _get_llm(self):
        """Get LLM instance based on configuration."""
        if self._llm is None:
            if settings.BROWSER_USE_LLM_PROVIDER == "groq":
                from langchain_groq import ChatGroq
                self._llm = ChatGroq(
                    model=settings.BROWSER_USE_MODEL,
                    api_key=settings.GROQ_API_KEY
                )
            else:
                raise ValueError(f"Unsupported LLM provider: {settings.BROWSER_USE_LLM_PROVIDER}")
        return self._llm
    
    async def execute_task(
        self,
        prompt: str,
        url: str,
        user_id: int,
        db: AsyncSession,
        options: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Execute a browser-use task asynchronously.
        
        Args:
            prompt: Natural language task description
            url: Target URL
            user_id: User ID executing the task
            db: Database session
            options: Optional execution options
        
        Returns:
            Task ID
        """
        task_id = f"bu_{uuid4().hex[:8]}"
        
        # Create task record
        db_task = BrowserUseTask(
            task_id=task_id,
            user_id=user_id,
            prompt=prompt,
            url=url,
            status=TaskStatus.PENDING,
            options=options or {}
        )
        db.add(db_task)
        await db.commit()
        
        logger.info("Created browser-use task", task_id=task_id, prompt=prompt, url=url)
        
        # Start background execution
        async_task = asyncio.create_task(
            self._execute_browser_agent(task_id, prompt, url, db, options)
        )
        self.active_tasks[task_id] = async_task
        
        return task_id
    
    async def _execute_browser_agent(
        self,
        task_id: str,
        prompt: str,
        url: str,
        db: AsyncSession,
        options: Optional[Dict[str, Any]] = None
    ):
        """Execute browser-use agent in background."""
        try:
            # Update status to running
            await self._update_task_status(db, task_id, TaskStatus.RUNNING)
            
            # Import browser-use here to avoid import errors if not installed
            from browser_use import Agent
            
            llm = self._get_llm()
            options = options or {}
            
            agent = Agent(
                task=prompt,
                llm=llm,
                browser_config={
                    "headless": options.get("headless", True),
                }
            )
            
            start_time = datetime.utcnow()
            
            # Run the agent
            result = await agent.run(url)
            
            duration = (datetime.utcnow() - start_time).total_seconds()
            
            # Update task with results
            await self._update_task_result(
                db, task_id, TaskStatus.COMPLETED,
                result=self._parse_result(result),
                duration_seconds=int(duration)
            )
            
            logger.info("Browser-use task completed", task_id=task_id, duration=duration)
            
        except Exception as e:
            logger.error("Browser-use task failed", task_id=task_id, error=str(e))
            await self._update_task_result(
                db, task_id, TaskStatus.FAILED,
                error_message=str(e)
            )
    
    def _parse_result(self, result: Any) -> Dict:
        """Parse browser-use result into dict."""
        if isinstance(result, dict):
            return result
        return {"raw_result": str(result)}
    
    async def _update_task_status(
        self,
        db: AsyncSession,
        task_id: str,
        status: TaskStatus
    ):
        """Update task status in database."""
        result = await db.execute(
            select(BrowserUseTask).where(BrowserUseTask.task_id == task_id)
        )
        task = result.scalar_one_or_none()
        if task:
            task.status = status
            await db.commit()
    
    async def _update_task_result(
        self,
        db: AsyncSession,
        task_id: str,
        status: TaskStatus,
        result: Optional[Dict] = None,
        error_message: Optional[str] = None,
        duration_seconds: Optional[int] = None
    ):
        """Update task with final results."""
        result_obj = await db.execute(
            select(BrowserUseTask).where(BrowserUseTask.task_id == task_id)
        )
        task = result_obj.scalar_one_or_none()
        if task:
            task.status = status
            if result:
                task.result = result
            if error_message:
                task.error_message = error_message
            if duration_seconds:
                task.duration_seconds = duration_seconds
            task.completed_at = datetime.utcnow()
            await db.commit()
    
    async def get_status(
        self,
        task_id: str,
        db: AsyncSession
    ) -> Optional[Dict[str, Any]]:
        """Get task status."""
        result = await db.execute(
            select(BrowserUseTask).where(BrowserUseTask.task_id == task_id)
        )
        task = result.scalar_one_or_none()
        if not task:
            return None
        
        return {
            "task_id": task.task_id,
            "status": task.status.value,
            "progress": 100 if task.status == TaskStatus.COMPLETED else 0,
            "error": task.error_message
        }
    
    async def get_results(
        self,
        task_id: str,
        db: AsyncSession
    ) -> Optional[Dict[str, Any]]:
        """Get full task results."""
        result = await db.execute(
            select(BrowserUseTask).where(BrowserUseTask.task_id == task_id)
        )
        task = result.scalar_one_or_none()
        if not task:
            return None
        
        return {
            "task_id": task.task_id,
            "status": task.status.value,
            "success": task.status == TaskStatus.COMPLETED,
            "steps": task.result.get("steps", []) if task.result else [],
            "screenshots": task.screenshots or [],
            "video": task.video_path,
            "duration_seconds": task.duration_seconds,
            "error": task.error_message,
            "completed_at": task.completed_at.isoformat() if task.completed_at else None
        }
```

- [ ] **Step 4: Verify test passes**
Run: `cd /home/ubuntu/qa-framework/dashboard/backend && python3 -m pytest tests/services/test_browser_use_service.py -v`
Expected: PASS (2 passed)

---

## Task 6: Create API Routes

**Files:**
- Create: `dashboard/backend/api/v1/browser_use_routes.py`
- Modify: `dashboard/backend/api/v1/__init__.py`

### Steps

- [ ] **Step 1: Create the routes file**
Create `dashboard/backend/api/v1/browser_use_routes.py`:
```python
"""Browser-Use API Routes."""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db_session
from services.auth_service import get_current_user
from services.ai.browser_use_service import BrowserUseService
from schemas.browser_use import (
    BrowserUseExecuteRequest,
    BrowserUseExecuteResponse,
    BrowserUseStatusResponse,
    BrowserUseResultsResponse,
)
from models import User
from core.logging_config import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/browser-use", tags=["browser-use"])

# Service singleton
_browser_use_service = None


def get_browser_use_service() -> BrowserUseService:
    """Get BrowserUseService singleton."""
    global _browser_use_service
    if _browser_use_service is None:
        _browser_use_service = BrowserUseService()
    return _browser_use_service


@router.post("/execute", response_model=BrowserUseExecuteResponse)
async def execute_browser_task(
    request: BrowserUseExecuteRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
    service: BrowserUseService = Depends(get_browser_use_service)
):
    """
    Execute a browser-use task.
    
    The task runs asynchronously. Use the returned task_id to check status.
    """
    logger.info(
        "Browser-use execute request",
        user_id=current_user.id,
        prompt=request.prompt,
        url=request.url
    )
    
    try:
        task_id = await service.execute_task(
            prompt=request.prompt,
            url=request.url,
            user_id=current_user.id,
            db=db,
            options=request.options.model_dump() if request.options else None
        )
        
        return BrowserUseExecuteResponse(
            task_id=task_id,
            status="pending",
            message="Task created successfully"
        )
    except Exception as e:
        logger.error("Failed to create browser-use task", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create task: {str(e)}"
        )


@router.get("/status/{task_id}", response_model=BrowserUseStatusResponse)
async def get_task_status(
    task_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
    service: BrowserUseService = Depends(get_browser_use_service)
):
    """Get browser-use task status."""
    result = await service.get_status(task_id, db)
    
    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found"
        )
    
    return BrowserUseStatusResponse(**result)


@router.get("/results/{task_id}", response_model=BrowserUseResultsResponse)
async def get_task_results(
    task_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
    service: BrowserUseService = Depends(get_browser_use_service)
):
    """Get browser-use task results."""
    result = await service.get_results(task_id, db)
    
    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found"
        )
    
    return BrowserUseResultsResponse(**result)
```

- [ ] **Step 2: Register router in __init__.py**
Add to `dashboard/backend/api/v1/__init__.py`:
```python
from api.v1.browser_use_routes import router as browser_use_router
# ... in the router includes ...
api_router.include_router(browser_use_router)
```

- [ ] **Step 3: Verify routes are registered**
Run: `cd /home/ubuntu/qa-framework/dashboard/backend && python3 -c "from api.v1 import api_router; print([r.path for r in api_router.routes if 'browser' in r.path])"`
Expected: `['/browser-use/execute', '/browser-use/status/{task_id}', '/browser-use/results/{task_id}']`

---

## Task 7: Create Database Migration

**Files:**
- Create: migration via alembic

### Steps

- [ ] **Step 1: Create migration**
Run: `cd /home/ubuntu/qa-framework/dashboard/backend && alembic revision --autogenerate -m "Add browser_use_tasks table"`
Expected: New migration file created in `alembic/versions/`

- [ ] **Step 2: Apply migration**
Run: `cd /home/ubuntu/qa-framework/dashboard/backend && alembic upgrade head`
Expected: `Running upgrade -> new_revision, Add browser_use_tasks table`

---

## Task 8: Write Integration Tests

**Files:**
- Create: `dashboard/backend/tests/integration/test_browser_use_api.py`

### Steps

- [ ] **Step 1: Create integration test**
Create `dashboard/backend/tests/integration/test_browser_use_api.py`:
```python
"""Integration tests for Browser-Use API."""
import pytest
from httpx import AsyncClient
from unittest.mock import patch, AsyncMock


@pytest.mark.asyncio
async def test_execute_endpoint(client: AsyncClient, auth_headers: dict):
    """Test POST /browser-use/execute endpoint."""
    response = await client.post(
        "/api/v1/browser-use/execute",
        json={
            "prompt": "Login to app",
            "url": "https://example.com"
        },
        headers=auth_headers
    )
    
    assert response.status_code == 200
    data = response.json()
    assert "task_id" in data
    assert data["status"] == "pending"


@pytest.mark.asyncio
async def test_status_endpoint(client: AsyncClient, auth_headers: dict):
    """Test GET /browser-use/status/{task_id} endpoint."""
    # First create a task
    create_response = await client.post(
        "/api/v1/browser-use/execute",
        json={
            "prompt": "Test task",
            "url": "https://example.com"
        },
        headers=auth_headers
    )
    task_id = create_response.json()["task_id"]
    
    # Then check status
    response = await client.get(
        f"/api/v1/browser-use/status/{task_id}",
        headers=auth_headers
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["task_id"] == task_id


@pytest.mark.asyncio
async def test_results_endpoint_not_found(client: AsyncClient, auth_headers: dict):
    """Test GET /browser-use/results/{task_id} returns 404 for non-existent task."""
    response = await client.get(
        "/api/v1/browser-use/results/bu_nonexistent",
        headers=auth_headers
    )
    
    assert response.status_code == 404
```

- [ ] **Step 2: Run integration tests**
Run: `cd /home/ubuntu/qa-framework/dashboard/backend && python3 -m pytest tests/integration/test_browser_use_api.py -v`
Expected: PASS (3 passed) or skip if fixtures not available

---

## Task 9: Update Documentation

**Files:**
- Modify: `README.md`
- Create: `docs/browser-use-usage.md`

### Steps

- [ ] **Step 1: Add to README.md**
Add section to `README.md`:
```markdown
### Browser-Use Integration

AI-powered test automation using natural language:

```bash
# Execute a test
curl -X POST https://qa-framework-production.up.railway.app/api/v1/browser-use/execute \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"prompt": "Login and verify dashboard loads", "url": "https://example.com"}'

# Check status
curl https://qa-framework-production.up.railway.app/api/v1/browser-use/status/bu_abc123 \
  -H "Authorization: Bearer YOUR_TOKEN"
```
```

- [ ] **Step 2: Create usage doc**
Create `docs/browser-use-usage.md`:
```markdown
# Browser-Use Usage Guide

## Overview
Browser-Use allows executing tests using natural language prompts.

## Prerequisites
- GROQ_API_KEY environment variable set
- Valid authentication token

## API Endpoints

### Execute Task
POST /api/v1/browser-use/execute

Request body:
```json
{
  "prompt": "Natural language description of the test",
  "url": "https://target-url.com",
  "options": {
    "record_video": true,
    "take_screenshots": true,
    "max_steps": 50
  }
}
```

### Check Status
GET /api/v1/browser-use/status/{task_id}

### Get Results
GET /api/v1/browser-use/results/{task_id}

## Examples

### Login Flow
```bash
curl -X POST /api/v1/browser-use/execute \
  -d '{"prompt": "Login with email test@example.com and password test123, then verify dashboard loads"}'
```

### Form Submission
```bash
curl -X POST /api/v1/browser-use/execute \
  -d '{"prompt": "Fill the contact form with test data and submit"}'
```
```

---

## Task 10: Run Full Test Suite

### Steps

- [ ] **Step 1: Run all tests**
Run: `cd /home/ubuntu/qa-framework/dashboard/backend && python3 -m pytest tests/ -v --cov=services/ai/browser_use_service --cov-report=term-missing`
Expected: All tests pass, coverage >80%

- [ ] **Step 2: Check coverage report**
Verify browser_use_service.py has >80% coverage

---

## Task 11: Create Demo Script

**Files:**
- Create: `scripts/demo_browser_use.py`

### Steps

- [ ] **Step 1: Create demo script**
Create `scripts/demo_browser_use.py`:
```python
#!/usr/bin/env python3
"""Demo script for Browser-Use integration."""
import asyncio
import httpx
import os

API_BASE = os.getenv("API_BASE", "http://localhost:8000/api/v1")
TOKEN = os.getenv("AUTH_TOKEN", "")


async def demo():
    """Run browser-use demo."""
    headers = {"Authorization": f"Bearer {TOKEN}"}
    
    async with httpx.AsyncClient() as client:
        # Execute task
        print("🚀 Executing browser-use task...")
        response = await client.post(
            f"{API_BASE}/browser-use/execute",
            json={
                "prompt": "Navigate to the login page and verify it loads correctly",
                "url": "https://example.com",
                "options": {"take_screenshots": True}
            },
            headers=headers
        )
        
        if response.status_code != 200:
            print(f"❌ Error: {response.text}")
            return
        
        task_id = response.json()["task_id"]
        print(f"✅ Task created: {task_id}")
        
        # Poll for status
        print("⏳ Waiting for completion...")
        for _ in range(30):
            await asyncio.sleep(2)
            status_response = await client.get(
                f"{API_BASE}/browser-use/status/{task_id}",
                headers=headers
            )
            status = status_response.json()["status"]
            print(f"  Status: {status}")
            
            if status in ["completed", "failed"]:
                break
        
        # Get results
        results = await client.get(
            f"{API_BASE}/browser-use/results/{task_id}",
            headers=headers
        )
        
        print("\n📊 Results:")
        print(f"  Success: {results.json()['success']}")
        print(f"  Duration: {results.json()['duration_seconds']}s")


if __name__ == "__main__":
    asyncio.run(demo())
```

- [ ] **Step 2: Make executable**
Run: `chmod +x scripts/demo_browser_use.py`

---

## Task 12: Commit and Create PR

### Steps

- [ ] **Step 1: Stage changes**
Run: `cd /home/ubuntu/qa-framework && git add -A`

- [ ] **Step 2: Commit**
Run: `git commit -m "feat: integrate Browser-Use for AI-powered test automation

- Add BrowserUseService with Groq LLM support
- Create API endpoints: /execute, /status, /results
- Add BrowserUseTask model and schemas
- Add integration tests
- Update documentation

Closes: #1b6605b9-dee2-479e-85ee-1bb1b21f307d"`

- [ ] **Step 3: Push and create PR**
Run: `git push origin feature/browser-use-integration`
Expected: Branch pushed, create PR via GitHub UI

---

## Verification Checklist

After completing all tasks:

- [ ] `POST /api/v1/browser-use/execute` returns task_id
- [ ] `GET /api/v1/browser-use/status/{task_id}` returns status
- [ ] `GET /api/v1/browser-use/results/{task_id}` returns results
- [ ] Tests pass with >80% coverage
- [ ] Demo script works
- [ ] Documentation updated
- [ ] PR created and ready for review
