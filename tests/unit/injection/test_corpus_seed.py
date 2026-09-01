"""Tests for the seeded corpus (20 seed vectors Day 2 + nudge-003 repro Day 3)."""

import pytest

from src.core.injection.corpus.agentdojo_seed import SEED_VECTORS

EXPECTED_FAMILIES = {
    "indirect-injection",
    "direct-injection",
    "tool-transition-nudge",
    "payload-in-file",
    "import-shadowing",
    "exfiltration-passive",
    "multi-turn",
}


@pytest.mark.unit
class TestSeedCorpus:
    def test_corpus_has_twenty_seed_vectors_plus_embracethered_repro(self):
        # Day 2 AC: 20 seed vectors. Day 3 adds nudge-003 (embracethered
        # end-to-end detection repro, design doc section 6.3).
        assert len(SEED_VECTORS) == 21
        seed_sources = [v for v in SEED_VECTORS if v.id != "nudge-003"]
        assert len(seed_sources) == 20
        assert any(v.id == "nudge-003" for v in SEED_VECTORS)

    def test_first_vector_is_valid_scenario(self):
        from src.core.injection.models import Scenario

        scenario = SEED_VECTORS[0]
        assert isinstance(scenario, Scenario)
        assert scenario.id == "agentdojo-001"

    def test_corpus_covers_all_spec_section2_families(self):
        families = {v.family for v in SEED_VECTORS}
        assert EXPECTED_FAMILIES.issubset(families)

    def test_every_vector_has_inline_asset_content(self):
        for vector in SEED_VECTORS:
            assert vector.asset_content, f"vector {vector.id} has no asset_content"

    def test_every_vector_task_references_a_legitimate_goal(self):
        for vector in SEED_VECTORS:
            assert len(vector.task) > 20, f"vector {vector.id} task too generic"

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
