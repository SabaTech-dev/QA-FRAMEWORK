# Getting Started

## Prerequisites

Before you begin, ensure you have the following installed:

- **Python 3.11+**: [Download Python](https://www.python.org/downloads/)
- **Node.js 18+**: [Download Node.js](https://nodejs.org/) (for frontend)
- **Docker**: [Install Docker](https://docs.docker.com/get-docker/) (optional but recommended)
- **PostgreSQL 14+**: [Install PostgreSQL](https://www.postgresql.org/download/) (or use Docker)
- **Redis 7+**: [Install Redis](https://redis.io/download) (or use Docker)

## Quick Start with Docker (Recommended)

The fastest way to get started is using Docker Compose:

```bash
# Clone the repository
git clone https://github.com/llllJokerllll/QA-FRAMEWORK.git
cd QA-FRAMEWORK

# Start all services
docker-compose up -d

# Access the application
# Frontend: http://localhost:3000
# Backend API: http://localhost:8000
# API Docs: http://localhost:8000/docs
```

That's it! The framework is now running with:
- Backend API (FastAPI)
- Frontend Dashboard (React)
- PostgreSQL Database
- Redis Cache
- Test Execution Workers

## Manual Installation

If you prefer to run without Docker, follow these steps:

### 1. Clone Repository

```bash
git clone https://github.com/llllJokerllll/QA-FRAMEWORK.git
cd QA-FRAMEWORK
```

### 2. Backend Setup

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Set up environment variables
cp .env.example .env
# Edit .env with your configuration

# Initialize database
python scripts/init_db.py

# Run backend server
uvicorn src.presentation.api.main:app --reload
```

### 3. Frontend Setup

```bash
# Navigate to frontend directory
cd dashboard/frontend

# Install dependencies
npm install

# Set up environment variables
cp .env.example .env
# Edit .env with your configuration

# Run development server
npm run dev
```

### 4. Database Setup

```bash
# Create PostgreSQL database
createdb qa_framework

# Run migrations
alembic upgrade head

# Seed initial data (optional)
python scripts/seed_db.py
```

## Configuration

### Environment Variables

Create a `.env` file in the root directory:

```bash
# Application
ENVIRONMENT=development
DEBUG=true
SECRET_KEY=your-secret-key-here
JWT_SECRET_KEY=your-jwt-secret-here

# Database
DATABASE_URL=postgresql://user:password@localhost:5432/qa_framework

# Redis
REDIS_HOST=localhost
REDIS_PORT=6379

# Email (optional)
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@gmail.com
SMTP_PASSWORD=your-password

# Integrations (optional)
JIRA_URL=https://yourcompany.atlassian.net
JIRA_USER=your-email@company.com
JIRA_API_TOKEN=your-api-token
```

### Database Configuration

Edit `alembic.ini` for database migrations:

```ini
[alembic]
script_location = migrations
sqlalchemy.url = postgresql://user:password@localhost/qa_framework
```

## First Steps

### 1. Create a Test Suite

Using the API:

```bash
curl -X POST http://localhost:8000/api/v1/suites \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d '{
    "name": "My First Test Suite",
    "description": "A sample test suite",
    "tags": ["smoke", "regression"]
  }'
```

Or using the Web UI:
1. Navigate to http://localhost:3000
2. Click "New Suite"
3. Fill in the details
4. Click "Create"

### 2. Add Test Cases

```bash
curl -X POST http://localhost:8000/api/v1/suites/{suite_id}/cases \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d '{
    "name": "Login Test",
    "description": "Verify user can login",
    "steps": [
      "Navigate to login page",
      "Enter username",
      "Enter password",
      "Click login button",
      "Verify user is logged in"
    ],
    "expected_result": "User successfully logged in"
  }'
```

### 3. Run Tests

```bash
curl -X POST http://localhost:8000/api/v1/suites/{suite_id}/run \
  -H "Authorization: Bearer YOUR_TOKEN"
```

### 4. View Results

Navigate to http://localhost:3000/results to see test execution results.

## Project Structure

```
qa-framework/
├── src/
│   ├── domain/           # Business logic
│   ├── application/      # Use cases
│   ├── infrastructure/   # External integrations
│   └── presentation/     # API, CLI, Web UI
├── tests/
│   ├── unit/             # Unit tests
│   ├── integration/      # Integration tests
│   └── e2e/              # End-to-end tests
├── dashboard/
│   ├── backend/          # FastAPI backend
│   └── frontend/         # React frontend
├── docs/                 # Documentation
├── scripts/              # Utility scripts
└── .github/workflows/    # CI/CD
```

## Running Tests

### Unit Tests

```bash
pytest tests/unit/ -v
```

### Integration Tests

```bash
pytest tests/integration/ -v
```

### All Tests with Coverage

```bash
pytest --cov=src --cov-report=html
```

## Development Workflow

### 1. Create a Feature Branch

```bash
git checkout -b feature/my-new-feature
```

### 2. Make Changes

Edit files, add tests, update documentation.

### 3. Run Tests

```bash
pytest
```

### 4. Commit Changes

```bash
git add .
git commit -m "feat: add new feature"
```

### 5. Push and Create PR

```bash
git push origin feature/my-new-feature
```

Create a pull request on GitHub.

## Common Issues

### Database Connection Error

**Problem:** `psycopg2.OperationalError: could not connect to server`

**Solution:**
1. Ensure PostgreSQL is running: `sudo systemctl start postgresql`
2. Check connection string in `.env`
3. Verify database exists: `psql -l | grep qa_framework`

### Redis Connection Error

**Problem:** `redis.exceptions.ConnectionError`

**Solution:**
1. Ensure Redis is running: `sudo systemctl start redis`
2. Check Redis configuration in `.env`
3. Test connection: `redis-cli ping`

### Frontend Build Error

**Problem:** `Module not found: Error: Can't resolve...`

**Solution:**
1. Clear node modules: `rm -rf node_modules package-lock.json`
2. Reinstall: `npm install`
3. Rebuild: `npm run build`

### Import Errors

**Problem:** `ModuleNotFoundError: No module named 'src'`

**Solution:**
1. Ensure you're in the project root
2. Install in development mode: `pip install -e .`
3. Check PYTHONPATH: `export PYTHONPATH="${PYTHONPATH}:$(pwd)"`

## Next Steps

- Read the [Architecture Guide](explanation/architecture.md) to understand the system design
- Check the [API Reference](reference/api.md) for detailed API documentation
- Learn about [Contributing](contributing.md) to the project

## Getting Help

- **Documentation**: Browse the `docs/` directory
- **Issues**: [GitHub Issues](https://github.com/llllJokerllll/QA-FRAMEWORK/issues)
- **Discussions**: [GitHub Discussions](https://github.com/llllJokerllll/QA-FRAMEWORK/discussions)
- **Email**: support@qa-framework.com

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
