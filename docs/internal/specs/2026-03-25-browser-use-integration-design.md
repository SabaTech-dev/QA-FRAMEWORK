# Browser-Use Integration - Design Doc

**Fecha:** 2026-03-25
**Autor:** coder agent
**Task ID:** 1b6605b9-dee2-479e-85ee-1bb1b21f307d
**Estado:** DRAFT - Pendiente aprobación

---

## 1. Goal

Integrar Browser-Use como motor de test automation con AI en QA-FRAMEWORK, permitiendo ejecutar tests E2E usando lenguaje natural.

---

## 2. Contexto

### 2.1 Browser-Use
- **Repo:** https://github.com/browser-use/browser-use
- **Stars:** 81.2K⭐
- **Benchmark:** 89.1% WebVoyager
- **Stack:** Python + Playwright + LLM
- **Costo:** ~$0.07/task (self-hosted)

### 2.2 QA-FRAMEWORK Actual
- **Backend:** FastAPI + PostgreSQL + Redis
- **Testing:** Playwright (ya instalado v1.58.0)
- **AI Services:** coverage_analyzer, root_cause_analyzer, test_optimizer
- **Execution Flow:** TestSuite → TestExecution → Results

---

## 3. Arquitectura Propuesta

### 3.1 Componentes

```
┌─────────────────────────────────────────────────────────────┐
│                    API Layer (FastAPI)                       │
├─────────────────────────────────────────────────────────────┤
│  POST /api/v1/browser-use/execute                           │
│  GET  /api/v1/browser-use/status/{task_id}                  │
│  GET  /api/v1/browser-use/results/{task_id}                 │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                 BrowserUseService                            │
├─────────────────────────────────────────────────────────────┤
│  - execute_task(prompt, url)                                │
│  - get_status(task_id)                                       │
│  - get_results(task_id)                                      │
│  - cancel_task(task_id)                                      │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                    Browser-Use Agent                          │
├─────────────────────────────────────────────────────────────┤
│  - LLM (Groq + Llama 3, configurable)                       │
│  - Playwright Browser                                        │
│  - Action Executor                                           │
│  - Screenshot/Video Capture                                  │
└─────────────────────────────────────────────────────────────┘
```

### 3.2 Flujo de Ejecución

```
1. Usuario envía prompt → API endpoint
2. BrowserUseService crea tarea asíncrona
3. Browser-Use Agent:
   a. Parsea prompt con LLM
   b. Decide acciones en el browser
   c. Ejecuta acciones con Playwright
   d. Captura screenshots/video
   e. Devuelve resultados
4. Resultados almacenados en DB + Redis cache
5. Usuario consulta resultados via API
```

---

## 4. Tech Stack

### 4.1 Dependencias Nuevas
```python
# requirements.txt additions
browser-use>=0.1.0
langchain-groq>=0.1.0  # Para Groq LLM
```

### 4.2 LLM Configuration
- **Default:** Groq + Llama 3 (gratis, rápido)
- **Alternatives:** OpenAI, Anthropic, Ollama (configurable via env)

```python
# config.py
BROWSER_USE_LLM_PROVIDER: str = "groq"  # groq | openai | anthropic | ollama
GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "")
GROQ_MODEL: str = "llama-3.3-70b-versatile"
```

---

## 5. API Surface

### 5.1 Execute Task
```python
POST /api/v1/browser-use/execute
{
    "prompt": "Login to the app and verify dashboard loads",
    "url": "https://qa-framework-production.up.railway.app",
    "options": {
        "record_video": true,
        "take_screenshots": true,
        "max_steps": 50
    }
}

Response:
{
    "task_id": "bu_abc123",
    "status": "running",
    "created_at": "2026-03-25T12:00:00Z"
}
```

### 5.2 Get Status
```python
GET /api/v1/browser-use/status/{task_id}

Response:
{
    "task_id": "bu_abc123",
    "status": "completed",  # running | completed | failed | cancelled
    "progress": 100,
    "current_step": "Verifying dashboard loaded"
}
```

### 5.3 Get Results
```python
GET /api/v1/browser-use/results/{task_id}

Response:
{
    "task_id": "bu_abc123",
    "status": "completed",
    "success": true,
    "steps": [
        {"action": "navigate", "target": "login page", "success": true},
        {"action": "fill", "target": "email field", "success": true},
        {"action": "fill", "target": "password field", "success": true},
        {"action": "click", "target": "login button", "success": true},
        {"action": "verify", "target": "dashboard loaded", "success": true}
    ],
    "screenshots": ["/results/bu_abc123/screenshot_1.png"],
    "video": "/results/bu_abc123/video.webm",
    "duration_seconds": 12.5
}
```

---

## 6. Implementación

### 6.1 Estructura de Archivos
```
dashboard/backend/
├── services/
│   └── ai/
│       ├── browser_use_service.py  # NUEVO
│       └── ...
├── api/v1/
│   └── browser_use_routes.py       # NUEVO
├── models/
│   └── browser_use_task.py         # NUEVO
├── schemas/
│   └── browser_use.py              # NUEVO
└── config.py                       # UPDATE
```

### 6.2 BrowserUseService (Core)
```python
# services/ai/browser_use_service.py
from browser_use import Agent
from langchain_groq import ChatGroq
from playwright.async_api import async_playwright
import asyncio
from typing import Optional, Dict, Any
from uuid import uuid4

class BrowserUseService:
    def __init__(self):
        self.llm = ChatGroq(
            model="llama-3.3-70b-versatile",
            api_key=settings.GROQ_API_KEY
        )
        self.active_tasks: Dict[str, Any] = {}

    async def execute_task(
        self,
        prompt: str,
        url: str,
        options: Optional[Dict] = None
    ) -> str:
        task_id = f"bu_{uuid4().hex[:8]}"
        
        agent = Agent(
            task=prompt,
            llm=self.llm,
            browser_config={
                "headless": True,
                "record_video": options.get("record_video", False),
            }
        )
        
        # Execute in background
        self.active_tasks[task_id] = asyncio.create_task(
            self._run_agent(task_id, agent, url)
        )
        
        return task_id

    async def _run_agent(self, task_id: str, agent: Agent, url: str):
        try:
            result = await agent.run(url)
            # Store results in DB
            await self._store_results(task_id, result)
        except Exception as e:
            await self._store_error(task_id, str(e))
```

---

## 7. Tasks Breakdown

### Fase 1: Setup (2h)
- [ ] Instalar browser-use y langchain-groq
- [ ] Añadir variables de entorno (GROQ_API_KEY)
- [ ] Crear estructura de archivos

### Fase 2: Service Layer (3h)
- [ ] Implementar BrowserUseService
- [ ] Implementar modelos y schemas
- [ ] Tests unitarios del service

### Fase 3: API Layer (2h)
- [ ] Implementar browser_use_routes.py
- [ ] Integrar con router principal
- [ ] Tests de integración

### Fase 4: Integration (2h)
- [ ] Conectar con execution_service existente
- [ ] Añadir opción "AI-powered" en UI
- [ ] Tests E2E

### Fase 5: Documentation (1h)
- [ ] Actualizar README
- [ ] Añadir ejemplos de uso
- [ ] Demo video

---

## 8. Riesgos

| Riesgo | Mitigación |
|--------|------------|
| LLM rate limits | Usar Groq (generoso free tier), cache de respuestas |
| Browser-Use inestable | Versionar dependencias, tests exhaustivos |
| Costos inesperados | Groq gratis, monitorear uso |
| Tests flaky | Timeouts generosos, retry logic |

---

## 9. Alternativas Consideradas

### Opción A: Browser-Use (Recomendada)
- **Pros:** 81K⭐, activo, 89.1% WebVoyager, Python nativo
- **Contras:** Depende de LLM externo

### Opción B: Selenium + AI custom
- **Pros:** Control total
- **Contras:** Mucho desarrollo, no optimizado para AI

### Opción C: Playwright Codegen + LLM
- **Pros:** Ya tenemos Playwright
- **Contras:** Menos inteligente que Browser-Use

**Recomendación:** Opción A - Browser-Use está optimizado para este use case.

---

## 10. Criterio de Aceptación (DoD)

- [ ] Endpoint `POST /api/v1/browser-use/execute` funcional
- [ ] Endpoint `GET /api/v1/browser-use/results/{task_id}` funcional
- [ ] Tests con >80% coverage
- [ ] Demo con flujo de login funcionando
- [ ] Documentación actualizada
- [ ] Commit + PR

---

## 11. Próximos Pasos

1. **Aprobar diseño** (Alfred/main)
2. Pasar a `coder-writing-plans` para plan detallado
3. Implementar siguiendo `coder-tdd`

---

**PENDIENTE:** Aprobación de este diseño antes de continuar.
