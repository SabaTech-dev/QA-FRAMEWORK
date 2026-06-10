# Third Party Notices

This project uses third-party software components. Below are the licenses for each component.

## Backend (Python)

### FastAPI & ASGI Stack
| Dependency | Version | License |
|---|---|---|
| fastapi | 0.115.4 | MIT |
| uvicorn | 0.32.0 | BSD-3-Clause |
| pydantic | 2.9.2 | MIT |
| pydantic-settings | 2.6.0 | MIT |
| starlette | (via fastapi) | BSD-3-Clause |

### Database & ORM
| Dependency | Version | License |
|---|---|---|
| sqlalchemy | 2.0.36 | MIT |
| asyncpg | 0.30.0 | Apache-2.0 |
| aiosqlite | 0.20.0 | MIT |
| alembic | 1.14.0 | MIT |
| psycopg2-binary | 2.9.10 | LGPL-3.0-only |

### Auth & Security
| Dependency | Version | License |
|---|---|---|
| python-jose | >=3.4.0 | MIT |
| passlib | 1.7.4 | BSD-3-Clause |
| bcrypt | 4.1.2 | Apache-2.0 |
| python-multipart | >=0.0.27 | Apache-2.0 |
| pyotp | 2.9.0 | MIT |
| qrcode[pil] | 7.4.2 | BSD-3-Clause |

### HTTP & APIs
| Dependency | Version | License |
|---|---|---|
| httpx | 0.27.2 | BSD-3-Clause |
| aiohttp | >=3.13.3 | Apache-2.0 |
| stripe | 10.12.0 | MIT |
| prometheus-client | 0.20.0 | Apache-2.0 |

### Caching & Task Queue
| Dependency | Version | License |
|---|---|---|
| redis | 5.2.0 | MIT |
| rq | 1.16.2 | BSD-2-Clause |
| celery | 5.4.0 | BSD-3-Clause |
| flower | 2.0.1 | BSD-3-Clause |

### Testing
| Dependency | Version | License |
|---|---|---|
| pytest | 8.3.3 | MIT |
| pytest-asyncio | 0.25.0 | Apache-2.0 |
| pytest-cov | 5.0.0 | MIT |
| pytest-playwright | 0.7.2 | Apache-2.0 |
| playwright | 1.58.0 | Apache-2.0 |
| allure-pytest | 2.13.5 | Apache-2.0 |
| locust | 2.20.0 | MIT |
| browser-use | >=0.1.0 | MIT |

### Utilities
| Dependency | Version | License |
|---|---|---|
| bleach | 6.2.0 | Apache-2.0 |
| email-validator | 2.2.0 | Unlicense |
| structlog | 24.4.0 | Apache-2.0 |
| python-dotenv | 1.0.1 | BSD-3-Clause |
| aiofiles | 24.1.0 | Apache-2.0 |
| websockets | 14.0 | BSD-3-Clause |

## Frontend (React/TypeScript)

| Dependency | Version | License |
|---|---|---|
| react | ^18.2.0 | MIT |
| react-dom | ^18.2.0 | MIT |
| react-router-dom | ~6.21.0 | MIT |
| @mui/material | ^5.15.0 | MIT |
| @mui/icons-material | ^5.15.0 | MIT |
| @emotion/react | ^11.11.0 | MIT |
| @emotion/styled | ^11.11.0 | MIT |
| axios | ^1.17.0 | MIT |
| react-query | ^3.39.3 | MIT |
| react-hook-form | ^7.48.0 | MIT |
| react-hot-toast | ^2.4.1 | MIT |
| chart.js | ^4.4.0 | MIT |
| react-chartjs-2 | ^5.2.0 | MIT |
| date-fns | ^2.30.0 | MIT |
| canvas-confetti | ^1.9.4 | MIT |
| vite | ^5.0.0 | MIT |
| vitest | ^1.0.0 | MIT |
| typescript | ^5.3.0 | Apache-2.0 |
| eslint | ^8.56.0 | MIT |
| playwright | ^1.40.0 | Apache-2.0 |

## Documentation & Tooling

| Tool | License |
|---|---|
| mkdocs | BSD-2-Clause |
| mkdocs-material | MIT |
| mkdocstrings[python] | MIT |
| trivy | Apache-2.0 |
| black | MIT |
| ruff | MIT |
| mypy | MIT |
| bandit | Apache-2.0 |
| isort | MIT |
| pip-audit | Apache-2.0 |

---

### MIT License

Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the "Software"), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

### BSD Licenses

Various components are distributed under BSD-2-Clause, BSD-3-Clause licenses. Redistribution and use in source and binary forms, with or without modification, are permitted provided that the conditions of the respective BSD license are met.

### Apache 2.0 License

Licensed under the Apache License, Version 2.0 (the "License"); you may not use this file except in compliance with the License. You may obtain a copy of the License at http://www.apache.org/licenses/LICENSE-2.0.
