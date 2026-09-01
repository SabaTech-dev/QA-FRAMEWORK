"""Tests for the seeded AgentDojo corpus (20 vectors planned; >=1 required on Day 1)."""

import pytest

from src.core.injection.corpus.agentdojo_seed import SEED_VECTORS


@pytest.mark.unit
class TestSeedCorpus:
    def test_corpus_has_at_least_one_vector(self):
        assert len(SEED_VECTORS) >= 1

    def test_first_vector_is_valid_scenario(self):
        from src.core.injection.models import Scenario

        scenario = SEED_VECTORS[0]
        assert isinstance(scenario, Scenario)
        assert scenario.id == "agentdojo-001"

    def test_all_vectors_map_to_owasp_llm01(self):
        assert all(v.owasp_ref == "LLM01" for v in SEED_VECTORS)

    def test_all_vectors_have_security_and_utility_criteria(self):
        for vector in SEED_VECTORS:
            assert vector.security_property
            assert vector.utility_criterion
            assert vector.forbidden_tool_patterns or vector.forbidden_paths

    def test_vector_ids_are_unique(self):
        ids = [v.id for v in SEED_VECTORS]
        assert len(ids) == len(set(ids))

    def test_poisoned_asset_contains_injection_payload(self):
        from src.core.injection.corpus.agentdojo_seed import POISONED_DOCUMENT

        assert "disregard" in POISONED_DOCUMENT.lower()
        assert "curl" in POISONED_DOCUMENT.lower()
