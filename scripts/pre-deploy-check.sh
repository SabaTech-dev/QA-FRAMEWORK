#!/bin/bash
# scripts/pre-deploy-check.sh - Validación automática pre-deploy
# Uso: ./scripts/pre-deploy-check.sh [--env staging|production]

set -e

ENV="${1:-production}"
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

ERRORS=0
WARNINGS=0

echo "🔍 QA-FRAMEWORK Pre-Deploy Check"
echo "Environment: $ENV"
echo "========================================"
echo ""

# Funciones auxiliares
pass() {
    echo -e "${GREEN}✅${NC} $1"
}

fail() {
    echo -e "${RED}❌${NC} $1"
    ((ERRORS++))
}

warn() {
    echo -e "${YELLOW}⚠️${NC} $1"
    ((WARNINGS++))
}

# ============================================
# CHECKS CRÍTICOS
# ============================================

echo "📋 Critical Checks"
echo "------------------"

# Check 1: Secrets not in git
echo "Checking for secrets in git history..."
if git log --all --full-history -- '*.env' '*.pem' '*secret*' '*.key' 2>/dev/null | grep -q .; then
    fail "Secrets found in git history!"
    echo "  Run: git filter-branch or BFG Repo-Cleaner"
else
    pass "No secrets in git history"
fi

# Check 2: Required environment variables
echo "Checking required environment variables..."
REQUIRED_VARS=("JWT_SECRET_KEY" "DATABASE_URL" "REDIS_URL")
for var in "${REQUIRED_VARS[@]}"; do
    if [ -z "${!var}" ]; then
        fail "Missing required env var: $var"
    else
        pass "$var is set"
    fi
done

# Check 3: JWT_SECRET_KEY strength
if [ -n "$JWT_SECRET_KEY" ]; then
    if [ ${#JWT_SECRET_KEY} -lt 32 ]; then
        fail "JWT_SECRET_KEY too short (min 32 chars, got ${#JWT_SECRET_KEY})"
    else
        pass "JWT_SECRET_KEY length OK (${#JWT_SECRET_KEY} chars)"
    fi
fi

# Check 4: Database URL uses SSL
if [ -n "$DATABASE_URL" ]; then
    if [[ "$DATABASE_URL" == *"sslmode=require"* ]] || [[ "$DATABASE_URL" == *"ssl=true"* ]]; then
        pass "Database connection uses SSL"
    else
        warn "Database URL doesn't explicitly require SSL"
        echo "  Consider adding: ?sslmode=require"
    fi
fi

# Check 5: No hardcoded passwords in code
echo "Checking for hardcoded secrets in code..."
if grep -r "password\s*=\s*['\"]" src/ --include="*.py" 2>/dev/null | grep -v "test" | grep -v "# "; then
    fail "Hardcoded passwords found in source code!"
else
    pass "No hardcoded passwords in source"
fi

if grep -r "api_key\s*=\s*['\"]sk_" src/ --include="*.py" 2>/dev/null | grep -v "test"; then
    fail "Hardcoded API keys found in source code!"
else
    pass "No hardcoded API keys in source"
fi

echo ""

# ============================================
# CHECKS DE CÓDIGO
# ============================================

echo "📝 Code Quality Checks"
echo "----------------------"

# Check 6: Dockerfile exists
if [ -f "Dockerfile" ]; then
    pass "Dockerfile exists"
else
    fail "Dockerfile not found"
fi

# Check 7: docker-compose for production
if [ -f "docker-compose.prod.yml" ] || [ -f "docker-compose.railway.yml" ]; then
    pass "Production docker-compose exists"
else
    warn "Production docker-compose not found"
fi

# Check 8: .dockerignore exists
if [ -f ".dockerignore" ]; then
    pass ".dockerignore exists"
else
    warn ".dockerignore not found (slower builds)"
fi

# Check 9: .gitignore has sensitive patterns
if grep -E '\.env|\.pem|secret|\.key' .gitignore > /dev/null 2>&1; then
    pass ".gitignore has sensitive patterns"
else
    fail ".gitignore missing sensitive patterns (.env, .pem, etc.)"
fi

echo ""

# ============================================
# CHECKS DE TESTS
# ============================================

echo "🧪 Test Checks"
echo "--------------"

# Check 10: Unit tests pass
echo "Running unit tests..."
if pytest tests/unit -q --tb=no 2>/dev/null; then
    pass "Unit tests passed"
else
    if command -v pytest &> /dev/null; then
        fail "Unit tests failed"
    else
        warn "pytest not installed, skipping tests"
    fi
fi

# Check 11: Health endpoint exists
if grep -r "/health" src/ --include="*.py" > /dev/null 2>&1; then
    pass "Health endpoint configured"
else
    warn "Health endpoint not found"
fi

echo ""

# ============================================
# CHECKS DE SEGURIDAD
# ============================================

echo "🔒 Security Checks"
echo "------------------"

# Check 12: CORS configuration
if grep -r "CORSMiddleware" src/ --include="*.py" > /dev/null 2>&1; then
    pass "CORS middleware configured"
else
    warn "CORS middleware not found"
fi

# Check 13: Rate limiting
if grep -r "rate_limit\|RateLimiter" src/ --include="*.py" > /dev/null 2>&1; then
    pass "Rate limiting configured"
else
    warn "Rate limiting not found"
fi

# Check 14: Dependencies vulnerabilities (if pip-audit available)
if command -v pip-audit &> /dev/null; then
    echo "Checking dependencies for vulnerabilities..."
    if pip-audit --format=brief 2>/dev/null | grep -q "No known vulnerabilities"; then
        pass "No dependency vulnerabilities"
    else
        warn "Dependency vulnerabilities found (run: pip-audit)"
    fi
else
    warn "pip-audit not installed, skipping vulnerability check"
fi

# Check 15: RATE_LIMIT_FAIL_MODE fail-fast (card 5221c63f)
# Invalid values silently fall back to open in the middleware — block here.
echo "Validating RATE_LIMIT_FAIL_MODE in tracked compose files..."
if python3 scripts/validate_rate_limit_fail_mode.py; then
    pass "RATE_LIMIT_FAIL_MODE valid"
else
    fail "Invalid RATE_LIMIT_FAIL_MODE in compose files (see error above)"
fi

echo ""

# ============================================
# CHECKS DE DOCUMENTACIÓN
# ============================================

echo "📚 Documentation Checks"
echo "-----------------------"

# Check 16: README exists
if [ -f "README.md" ]; then
    pass "README.md exists"
else
    warn "README.md not found"
fi

# Check 17: .env.example exists
if [ -f ".env.example" ]; then
    pass ".env.example exists"
else
    warn ".env.example not found"
fi

# Check 18: Deployment docs exist
if [ -f "docs/deployment/DEPLOYMENT.md" ] || [ -f "DEPLOYMENT.md" ]; then
    pass "Deployment documentation exists"
else
    warn "Deployment documentation not found"
fi

echo ""

# ============================================
# RESUMEN
# ============================================

echo "========================================"
echo "📊 Summary"
echo "========================================"
echo -e "Errors:   ${RED}$ERRORS${NC}"
echo -e "Warnings: ${YELLOW}$WARNINGS${NC}"
echo ""

if [ $ERRORS -gt 0 ]; then
    echo -e "${RED}❌ DEPLOY BLOCKED${NC}"
    echo "Fix the errors above before deploying."
    exit 1
elif [ $WARNINGS -gt 0 ]; then
    echo -e "${YELLOW}⚠️  DEPLOY WITH CAUTION${NC}"
    echo "Review the warnings above. Deploy allowed but not recommended."
    exit 0
else
    echo -e "${GREEN}✅ ALL CHECKS PASSED${NC}"
    echo "Ready to deploy to $ENV!"
    exit 0
fi
