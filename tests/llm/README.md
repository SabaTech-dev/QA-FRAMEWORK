# DeepEval LLM Testing — QA-FRAMEWORK

## Overview

This directory contains pytest-style LLM evaluation tests using [DeepEval](https://docs.confident-ai.com/) (v4.0.6).
Tests evaluate LLM outputs across multiple quality dimensions.

## Metrics

| Metric | What It Measures | Default Threshold |
|--------|-----------------|-------------------|
| **Answer Relevancy** | Is the answer relevant to the question? | 0.7 |
| **Faithfulness** | Is the answer grounded in the context? (no hallucinations) | 0.7 |
| **Toxicity** | Does the response contain harmful content? (lower = better) | 0.5 |
| **GEval** | Custom criteria defined in natural language | 0.7 |

## Quick Start

```bash
# Activate the venv
cd /home/joker/repos/QA-FRAMEWORK
source .venv/bin/activate

# Run LLM tests with isolated config
pytest tests/llm/ -c tests/llm/pytest.ini --rootdir=tests/llm -v

# Run specific metric tests
pytest tests/llm/ -c tests/llm/pytest.ini --rootdir=tests/llm -v -m llm_answer_relevancy
pytest tests/llm/ -c tests/llm/pytest.ini --rootdir=tests/llm -v -m llm_faithfulness

# Run integration tests (requires live LLM)
DEEPEVAL_RUN_LIVE=1 pytest tests/llm/ -c tests/llm/pytest.ini --rootdir=tests/llm -v -m llm_integration

# Collect only (no execution)
pytest tests/llm/ -c tests/llm/pytest.ini --rootdir=tests/llm --collect-only
```

## Configuration

Set via environment variables or `.env` file:

| Variable | Default | Description |
|----------|---------|-------------|
| `DEEPEVAL_MODEL` | `gpt-4o-mini` | Model used by DeepEval judge (needs API key) |
| `DEEPEVAL_CUSTOM_MODEL` | None | Custom model name for judge |
| `DEEPEVAL_CUSTOM_BASE_URL` | None | Base URL for local/custom judge endpoint |
| `OPENAI_API_KEY` | Required | API key for the judge model |
| `DEEPEVAL_THRESHOLD_ANSWER_RELEVANCY` | `0.7` | Answer relevancy threshold |
| `DEEPEVAL_THRESHOLD_FAITHFULNESS` | `0.7` | Faithfulness threshold |
| `DEEPEVAL_THRESHOLD_TOXICITY` | `0.5` | Toxicity threshold |
| `DEEPEVAL_THRESHOLD_GEVAL` | `0.7` | GEval threshold |
| `DEEPEVAL_RUN_LIVE` | `0` | Set to `1` to run live LLM integration tests |
| `LLM_BASE_URL` | `http://192.168.1.39:8001/v1` | LLM endpoint for integration tests |
| `LLM_MODEL_NAME` | `qwen3.6` | Model name for integration tests |

### Using local llama.cpp as judge

```bash
export DEEPEVAL_MODEL="qwen3.6"
export DEEPEVAL_CUSTOM_BASE_URL="http://192.168.1.39:8001/v1"
export OPENAI_API_KEY="not-needed"  # llama.cpp doesn't check
```

## File Structure

```
tests/llm/
├── pytest.ini              # Isolated pytest config (avoids root conftest deps)
├── conftest.py              # Fixtures, metrics config, LLM client
├── __init__.py              # Marker registration
├── test_answer_relevancy.py # Answer Relevancy metric tests (4 tests)
├── test_faithfulness.py     # Faithfulness metric tests (4 tests)
├── test_toxicity.py         # Toxicity metric tests (3 tests)
├── test_geval.py            # GEval custom criteria tests (3 tests)
├── test_llm_integration.py  # Full pipeline integration tests (4 tests, live LLM)
└── README.md                # This file
```

## Test Summary

| File | Tests | Type | Requires API |
|------|-------|------|-------------|
| test_answer_relevancy.py | 4 | Answer Relevancy | ✅ |
| test_faithfulness.py | 4 | Faithfulness | ✅ |
| test_toxicity.py | 3 | Toxicity | ✅ |
| test_geval.py | 3 | GEval | ✅ |
| test_llm_integration.py | 4 | Integration | ✅ (live LLM) |
| **Total** | **18** | | |

## Architecture

- **Isolated pytest config** (`tests/llm/pytest.ini`) — LLM tests don't depend on the main test suite's heavy plugins (playwright, selenium, etc.)
- **Configurable thresholds** — each metric threshold is env-configurable for different quality levels
- **Live integration** — `DEEPEVAL_RUN_LIVE=1` enables end-to-end tests against the self-hosted LLM
- **Negative tests** — includes tests that verify the metrics catch bad outputs (irrelevant answers, hallucinations)
