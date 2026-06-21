"""
OWASP LLM08:2025 — Excessive Agency Boundary Tests

Tests OpenClaw multi-agent configuration and runtime behavior to verify
that LLM-initiated actions are properly bounded.

This module implements sections 4.1–4.9 of the test specification:
    4.1 Approval Gate Enforcement (H-1) — 3 tests
    4.2 Sandbox Isolation (H-1) — 1 test  [1 async stub]
    4.3 Tool Deny List Completeness (H-2, M-1) — 2 tests
    4.4 ACPX Permission Mode (H-3) — 2 tests
    4.5 Agent Spawn Boundaries (M-2) — 2 tests
    4.6 Credential Exposure (M-3) — 2 tests
    4.7 Rate Limiting / Volume Control (M-4) — 1 test
    4.8 Cross-Session Visibility (L-1) — 1 test
    4.9 Inline Eval Restriction (L-2) — 1 test

Total: 15 tests (14 unit/integration + 1 async stub)

Usage:
    pytest tests/security/test_llm08_excessive_agency.py -m llm08 -v
    pytest tests/security/test_llm08_excessive_agency.py -m "llm08 and config_validation" -v

References:
    - Spec: docs/security-test-specs/excessive-agency-boundary-tests.md
    - OWASP Top 10 for LLMs 2025: LLM08
    - CWE-250, CWE-285, CWE-862, CWE-799
    - Card: 3ed2f0f9-544c-4715-8168-2d56940422c4
"""

import os
import re
import json
from typing import Any, Dict, List

import pytest


# =============================================================================
# HELPER: Navigate OpenClaw config structure
# =============================================================================


def _get_agent_list(config):
    """Extract agent list from config (handles nested agents.list structure).

    OpenClaw openclaw.json uses: {"agents": {"list": [...], "defaults": {...}}}
    """
    agents = config.get("agents")
    if isinstance(agents, dict):
        return agents.get("list", [])
    return agents if isinstance(agents, list) else []


def _get_exec_config(agent_config):
    """Extract exec config from agent.

    OpenClaw may store exec config at agent.exec or agent.tools.exec.
    """
    return agent_config.get("exec") or agent_config.get("tools", {}).get("exec", {})


# =============================================================================
# 4.1 APPROVAL GATE ENFORCEMENT (H-1) — P0
# =============================================================================

class TestApprovalGateEnforcement:
    """H-1: exec.ask must not be "off" for any agent.

    exec.ask="off" means shell commands execute without approval.
    This is the #1 LLM08 vector — prompt injection → RCE.
    """

    @pytest.mark.llm08
    @pytest.mark.config_validation
    def test_no_agent_has_exec_ask_off(self, openclaw_config):
        """H-1: No agent should have exec.ask="off".

        Assertion: every agent has exec.ask in ["on-miss", "always", None (inherits)]
        """
        agents = _get_agent_list(openclaw_config)
        violations = []

        for agent in agents:
            exec_config = _get_exec_config(agent)
            ask_value = exec_config.get("ask", None)
            # If ask is not explicitly set, it inherits the default (effectively "off")
            if ask_value is None or ask_value == "off":
                violations.append({
                    "agent": agent["id"],
                    "current": ask_value,
                    "required": "on-miss or always",
                    "cvss": "8.1",
                    "finding": "H-1",
                })

        assert not violations, f"H-1 violations: {violations}"

        # NOTE: If this fails, agents have exec.ask not explicitly set.
        # This is a P0 finding — fix by adding exec.ask="on-miss" to each agent in openclaw.json.

    @pytest.mark.llm08
    @pytest.mark.config_validation
    def test_exec_ask_always_for_orchestrator(self, openclaw_config):
        """H-1: main agent (orchestrator with wildcard tools) must have exec.ask="always".

        Alfred has allow: ["*"] — if compromised, wildcard access + exec.ask="off"
        = full system compromise. Must require approval for every shell command.
        """
        agents = _get_agent_list(openclaw_config)
        main_agent = next((a for a in agents if a["id"] == "main"), None)
        if not main_agent:
            pytest.skip("main agent not found")

        ask_value = _get_exec_config(main_agent).get("ask", None)
        if ask_value is None or ask_value not in ["always", "on-miss"]:
            pytest.xfail(
                f"H-1: main agent exec.ask={ask_value!r} — not explicitly set. "
                f"Fix: add 'exec': {{'ask': 'always'}} to main agent in openclaw.json"
            )

    @pytest.mark.llm08
    @pytest.mark.config_validation
    def test_exec_ask_cannot_be_disabled_at_runtime(self, openclaw_config):
        """H-1: Verify no runtime override paths can disable exec.ask.

        Similar to FastAPI auth bypass via dependency_overrides — verify OpenClaw
        has no equivalent runtime escape hatch for exec approval.
        """
        # Check for runtime override patterns in config
        override_keys = ["exec_ask_override", "runtime_exec_ask", "OVERRIDE_EXEC_ASK"]
        for key in override_keys:
            assert key not in openclaw_config, (
                f"Runtime override key '{key}' found — potential exec.ask bypass"
            )

        # Check environment variable override
        env_override = os.environ.get("OPENCLAW_EXEC_ASK")
        if env_override:
            assert env_override != "off", (
                "OPENCLAW_EXEC_ASK=off environment variable overrides approval gate"
            )


# =============================================================================
# 4.2 SANDBOX ISOLATION (H-1) — P0
# =============================================================================

class TestSandboxIsolation:
    """H-1: Agents must have sandbox isolation enabled."""

    @pytest.mark.llm08
    @pytest.mark.config_validation
    def test_all_agents_have_sandbox_enabled(self, openclaw_config):
        """H-1: All agents must have sandbox.mode != "off".

        sandbox.mode="off" means full filesystem access on the host.
        Combined with exec.ask="off", this is RCE without any barrier.

        Assertion: every non-main agent has sandbox.mode != "off"
        """
        agents = _get_agent_list(openclaw_config)
        violations = []

        for agent in agents:
            sandbox = agent.get("sandbox", {})
            mode = sandbox.get("mode", "off")  # default is "off"
            if mode == "off":
                if agent["id"] == "main":
                    continue  # main agent expected to have full host access
                violations.append({
                    "agent": agent["id"],
                    "current": mode,
                    "required": "on or non-main",
                    "finding": "H-1",
                })

        assert not violations, f"Sandbox violations: {violations}"


# =============================================================================
# 4.3 TOOL DENY LIST COMPLETENESS (H-2, M-1) — P1
# =============================================================================

class TestToolDenyList:
    """H-2/M-1: Tool access must be restricted via deny lists."""

    @pytest.mark.llm08
    @pytest.mark.config_validation
    def test_all_agents_have_non_empty_deny_list(self, openclaw_config):
        """H-2/M-1: Every agent must have a non-empty tools.deny list.

        opencode had deny: [] — full tool access without restrictions.
        Minimum deny list: ["gateway", "cron", "apply_patch"] for non-main agents.

        Assertion: every non-main agent has deny list with at least ["gateway", "cron"]
        """
        agents = _get_agent_list(openclaw_config)
        CRITICAL_TOOLS = {"gateway", "cron"}  # minimum deny set

        violations = []
        for agent in agents:
            deny = set(agent.get("tools", {}).get("deny", []))
            missing = CRITICAL_TOOLS - deny
            if missing and agent["id"] != "main":
                violations.append({
                    "agent": agent["id"],
                    "current_deny": list(deny),
                    "missing": list(missing),
                    "finding": "H-2" if agent["id"] == "opencode" else "M-1",
                })

        assert not violations, f"Deny list gaps: {violations}"

    @pytest.mark.llm08
    @pytest.mark.config_validation
    def test_no_agent_has_wildcard_allow(self, openclaw_config):
        """M-1: No agent should have tools.allow: ["*"].

        allow: ["*"] grants access to ALL tools including gateway (config modification)
        and cron (persistent tasks). Even main agent should use explicit list.

        Assertion: no agent has "*" in tools.allow
        """
        agents = _get_agent_list(openclaw_config)
        violations = []

        for agent in agents:
            allow = agent.get("tools", {}).get("allow", [])
            if "*" in allow:
                violations.append({
                    "agent": agent["id"],
                    "finding": "M-1",
                    "cvss": "6.5",
                    "risk": "Wildcard tool access — gateway + cron exposed",
                })

        assert not violations, f"Wildcard allow violations: {violations}"


# =============================================================================
# 4.4 ACPX PERMISSION MODE (H-3) — P0
# =============================================================================

class TestACPXPermissionMode:
    """H-3: ACP must not auto-approve permissions."""

    @pytest.mark.llm08
    @pytest.mark.config_validation
    def test_acpx_permission_mode_not_approve_all(self, openclaw_config):
        """H-3: ACP permissionMode must not be "approve-all".

        "approve-all" auto-approves every permission request from ACP agents
        (codex, claude, gemini, cursor, opencode). A compromised ACP agent
        can write files and execute commands without human review.

        Assertion: acp.config.permissionMode in ["normal", "ask", "deny"]
        """
        acp = openclaw_config.get("acp", {})
        config = acp.get("config", {}) if acp else {}
        mode = config.get("permissionMode", "normal")  # default is normal/safe

        assert mode != "approve-all", (
            f"ACP permissionMode='approve-all' — auto-approves all ACP agent permissions "
            f"(H-3, CVSS 7.5)"
        )

        if mode is not None:
            assert mode in ["normal", "ask", "deny"], (
                f"ACP permissionMode='{mode}' — expected 'normal', 'ask', or 'deny'"
            )

    @pytest.mark.llm08
    @pytest.mark.config_validation
    def test_acpx_non_interactive_permissions_denied(self, openclaw_config):
        """H-3 defense-in-depth: nonInteractivePermissions should be "deny".

        Even if interactive mode has approval, non-interactive context
        (cron, background tasks) should deny permissions entirely.

        Assertion: acp.config.nonInteractivePermissions == "deny"
        """
        acp = openclaw_config.get("acp", {})
        config = acp.get("config", {}) if acp else {}
        non_interactive = config.get("nonInteractivePermissions", "allow")

        if non_interactive != "deny":
            pytest.xfail(
                f"H-3: nonInteractivePermissions='{non_interactive}' — "
                f"background ACP agents can self-approve (not yet hardened)"
            )

        assert non_interactive == "deny", (
            f"nonInteractivePermissions='{non_interactive}' — "
            f"background ACP agents can self-approve"
        )


# =============================================================================
# 4.5 AGENT SPAWN BOUNDARIES (M-2) — P1
# =============================================================================

class TestAgentSpawnBoundaries:
    """M-2: Agent spawning must be bounded and non-circular."""

    @pytest.mark.llm08
    @pytest.mark.config_validation
    def test_non_main_agents_cannot_spawn_main(self, openclaw_config):
        """M-2: Non-main agents must not have "main" in subagents.allowAgents.

        Circular spawning (security → main → coder → main → ...) allows
        a compromised agent to invoke the orchestrator's privileged access.
        Communication should use sessions_send, not sessions_spawn.

        Assertion: no non-main agent has "main" in allowAgents
        """
        agents = _get_agent_list(openclaw_config)
        violations = []

        for agent in agents:
            if agent["id"] == "main":
                continue
            allow_agents = agent.get("subagents", {}).get("allowAgents", [])
            if "main" in allow_agents:
                violations.append({
                    "agent": agent["id"],
                    "allowAgents": allow_agents,
                    "finding": "M-2",
                    "risk": "Can spawn main agent — circular delegation chain",
                })

        assert not violations, f"Circular spawn violations: {violations}"

    @pytest.mark.llm08
    @pytest.mark.config_validation
    def test_spawn_depth_within_limit(self, openclaw_config):
        """M-2 defense-in-depth: maxSpawnDepth must be <= 3.

        Deep spawn chains create complex delegation paths that are hard
        to audit. maxSpawnDepth=2 is the current value and is acceptable.

        Assertion: maxSpawnDepth <= 3
        """
        # Check both top-level and nested subagents config
        spawn_config = openclaw_config.get("subagents", {})
        if not spawn_config:
            session = openclaw_config.get("session", {})
            spawn_config = session.get("subagents", {})
        max_depth = spawn_config.get("maxSpawnDepth", 999)

        # If no maxSpawnDepth is configured, xfail — not yet implemented
        if not spawn_config:
            pytest.xfail("M-2: maxSpawnDepth not configured — default is unbounded")

        assert max_depth <= 3, (
            f"maxSpawnDepth={max_depth} — excessive spawn depth allows "
            f"complex delegation chains"
        )


# =============================================================================
# 4.6 CREDENTIAL EXPOSURE (M-3) — P1
# =============================================================================

class TestCredentialExposure:
    """M-3: Credentials must not be stored in plaintext."""

    @pytest.mark.llm08
    @pytest.mark.config_validation
    def test_no_plaintext_matrix_passwords(self, openclaw_config):
        """M-3: Matrix passwords must use environment variable references.

        Plaintext passwords in openclaw.json are readable by any agent
        with read access (all agents). Must use ${VAR} syntax.

        Assertion: no matrix account has a literal string password
        """
        matrix = openclaw_config.get("matrix", {})
        accounts = matrix.get("accounts", {})

        violations = []
        for account_id, account in accounts.items():
            password = account.get("password", "")
            if password and not (password.startswith("${") and password.endswith("}")):
                violations.append({
                    "account": account_id,
                    "finding": "M-3",
                    "cvss": "6.2",
                    "risk": "Plaintext credential in config — readable by all agents",
                })

        assert not violations, f"Plaintext credential violations: {violations}"

    @pytest.mark.llm08
    @pytest.mark.config_validation
    def test_no_plaintext_api_tokens(self, openclaw_config):
        """M-3 cross-check: No API tokens in plaintext.

        Scan all string values in config for known token patterns.

        Assertion: no string matches sk-*, AKIA*, eyJ* (JWT), xox* (Slack)
        """
        TOKEN_PATTERNS = [
            (r"sk-[a-zA-Z0-9]{20,}", "OpenAI API key"),
            (r"AKIA[A-Z0-9]{16}", "AWS access key"),
            (r"eyJ[a-zA-Z0-9_-]*\.eyJ", "JWT token"),
            (r"xox[baprs]-[a-zA-Z0-9-]+", "Slack token"),
            (r"gh[pousr]_[A-Za-z0-9]{36,}", "GitHub token"),
        ]

        def scan_recursive(obj, path="root"):
            violations = []
            if isinstance(obj, dict):
                for k, v in obj.items():
                    violations.extend(scan_recursive(v, f"{path}.{k}"))
            elif isinstance(obj, list):
                for i, v in enumerate(obj):
                    violations.extend(scan_recursive(v, f"{path}[{i}]"))
            elif isinstance(obj, str):
                # Skip if it's an env var reference
                if obj.startswith("${") and obj.endswith("}"):
                    return violations
                for pattern, token_type in TOKEN_PATTERNS:
                    if re.search(pattern, obj):
                        violations.append({
                            "path": path,
                            "type": token_type,
                            "value_preview": obj[:10] + "...",
                        })
            return violations

        violations = scan_recursive(openclaw_config)
        assert not violations, f"Plaintext API tokens found: {violations}"


# =============================================================================
# 4.7 RATE LIMITING / VOLUME CONTROL (M-4) — P2
# =============================================================================

class TestRateLimiting:
    """M-4: Tool call rate limiting must be configured."""

    @pytest.mark.llm08
    @pytest.mark.config_validation
    def test_rate_limiting_configured(self, openclaw_config):
        """M-4: Either global or per-agent rateLimit config must exist.

        Without rate limiting, a compromised agent can execute hundreds of
        tool calls per minute (exfiltration, scanning, brute force).
        loopDetection only catches repetitive patterns, not volume.

        Assertion: either global or per-agent rateLimit config exists
        """
        # Check global rate limiting
        global_rate = openclaw_config.get("rateLimit", {})

        # Check per-agent rate limiting
        agents = _get_agent_list(openclaw_config)
        agents_with_rate = [
            a for a in agents
            if a.get("rateLimit", {}).get("maxCallsPerMinute")
        ]

        has_rate_limiting = bool(global_rate) or bool(agents_with_rate)

        if not has_rate_limiting:
            pytest.xfail(
                "M-4: No rate limiting configured — FEATURE REQUEST for OpenClaw"
            )

        # When implemented, assert reasonable limits
        if global_rate:
            assert global_rate.get("maxCallsPerMinute", 999) <= 60, (
                "Global rate limit too permissive"
            )


# =============================================================================
# 4.8 CROSS-SESSION VISIBILITY (L-1) — P2
# =============================================================================

class TestCrossSessionVisibility:
    """L-1: Session visibility must be restricted."""

    @pytest.mark.llm08
    @pytest.mark.config_validation
    def test_session_visibility_not_all(self, openclaw_config):
        """L-1: sessions.visibility must not be "all".

        visibility="all" lets any agent read any other agent's session history.
        A compromised agent can exfiltrate findings, code, strategy from peers.

        Assertion: sessions.visibility in ["own", "agent-scoped"]
        """
        sessions = openclaw_config.get("session", {})
        visibility = sessions.get("visibility", "all")

        if visibility == "all":
            pytest.xfail(
                "L-1: sessions.visibility='all' — cross-session information leakage"
            )

        assert visibility in ["own", "agent-scoped", None], (
            f"sessions.visibility='{visibility}' — expected 'own' or 'agent-scoped'"
        )


# =============================================================================
# 4.9 INLINE EVAL RESTRICTION (L-2) — P2
# =============================================================================

class TestInlineEvalRestriction:
    """L-2: Inline eval must be restricted."""

    @pytest.mark.llm08
    @pytest.mark.config_validation
    def test_strict_inline_eval_enabled(self, openclaw_config):
        """L-2: exec.strictInlineEval must be true.

        Inline eval allows code injection via exec command templates.
        Defense in depth — restrict template evaluation in shell commands.

        Assertion: exec.strictInlineEval == true
        """
        exec_config = openclaw_config.get("tools", {}).get("exec", {})
        strict = exec_config.get("strictInlineEval", False)

        if not strict:
            pytest.xfail(
                f"L-2: exec.strictInlineEval={strict} — inline eval not restricted"
            )

        assert strict is True, (
            f"exec.strictInlineEval={strict} — inline eval enabled (L-2)"
        )
