# AI Literacy Policy — SabaTech

**Version:** 1.0 | **Date:** 2026-07-09 | **Status:** Pending Joker approval  
**Regulatory basis:** EU AI Act (Regulation 2024/1689), Article 4  
**Applicability:** All SabaTech staff and contractors operating or using AI systems

---

## 1. Purpose

This policy fulfils SabaTech's obligations under **Article 4 of the EU AI Act**, which requires providers and deployers of AI systems to ensure a sufficient level of AI literacy among their staff and persons dealing with AI systems on their behalf.

**Omnibus 2026 amendment:** The standard was softened from "ensure" to "support" the development of AI competencies. This policy meets the softened standard proportionate to SabaTech's size as an SME.

---

## 2. Scope

This policy applies to:
- **All SabaTech employees** (permanent, temporary, and contractors)
- **External collaborators** who operate AI systems on behalf of SabaTech
- **AI systems covered:** All AI systems deployed or used by SabaTech, including but not limited to:
  - LLMs via OpenRouter / ZAI (DeepSeek-V4-flash, GLM-5.2) for code generation, testing, and research
  - OpenClaw agent framework (multi-agent orchestration with LLM backends)
  - GitHub Copilot / OpenCode (code assistance)
  - Browser automation tools with AI components
  - Any future AI systems adopted by SabaTech

---

## 3. AI Literacy Requirements

### 3.1 Minimum Knowledge Areas (per EC AI Office guidance)

All staff interacting with AI systems must understand:

| Area | Content | How SabaTech ensures |
|------|---------|---------------------|
| **A. AI Fundamentals** | What is AI? How do LLMs work? What are their capabilities and limitations? | Onboarding docs + internal wiki |
| **B. SabaTech AI Systems** | Which AI systems do we use? For what purpose? What are the risks? | AI Systems Register (G3 deliverable) + this policy |
| **C. Role & Responsibility** | Is SabaTech a provider or deployer of AI? What are our obligations? | Role assessment documented in §4 below |
| **D. Risk Awareness** | What risks exist (bias, hallucination, data leakage, prompt injection)? How to mitigate? | Internal training + red-teaming documentation |
| **E. Legal & Ethical** | EU AI Act obligations, GDPR interaction, ethical AI use principles | This policy + compliance docs |

### 3.2 Role-Specific Competencies

| Role | Additional Requirements |
|------|------------------------|
| **AI System Operators** (agents using LLMs daily) | Prompt engineering best practices, hallucination detection, output verification protocols |
| **Developers** (integrating AI into products) | Secure AI integration, adversarial testing basics, EU AI Act compliance requirements |
| **Management** (Joker) | Risk classification under AI Act, compliance obligations, decision-making for AI adoption |

---

## 4. SabaTech AI Role Assessment

| Dimension | Assessment | Justification |
|-----------|------------|---------------|
| **Provider vs Deployer** | **Deployer** of GPAI models (uses LLMs from OpenRouter/ZAI) | SabaTech does not train foundation models |
| **Provider of AI tools** | **Yes — QA-FRAMEWORK** uses LLMs internally for test generation | QA-FRAMEWORK is classified as **Limited Risk** under AI Act |
| **Risk Classification** | **Limited Risk** (Art. 50 transparency obligations apply) | Not high-risk: no Annex III use cases, no decisions about individuals |
| **GPAI Model usage** | DeepSeek-V4-flash, GLM-5.2 via OpenRouter + ZAI | Deployer obligations: document usage, verify provider transparency |

---

## 5. Existing AI Literacy Measures

SabaTech has established the following AI literacy practices prior to this formal policy:

| Measure | Description | Since |
|---------|-------------|-------|
| **Multi-agent AI system (OpenClaw)** | 6 specialized agents (coder, security, research, devops, qa-tester, opencode) with documented AI usage patterns | Jan 2026 |
| **Internal knowledge base** | MEMORY.md, SKILL.md files, research reports, and investigation docs maintained across agent workspaces | Jan 2026 |
| **Red-teaming toolkit** | Documented evaluation of AI security tools (Promptfoo, Garak, PyRIT, Nuclei) with internal reports | Jun 2026 |
| **EU AI Act research** | Multiple compliance investigations completed (Jun-Jul 2026), including gap analysis and SynthID watermarking evaluation | Jun 2026 |
| **AI model evaluation practice** | Systematic evaluation of LLM models (DeepSeek-V4-flash, MiMo, MAI, VibeThinker) with documented benchmarks | Jun 2026 |
| **Secure AI integration patterns** | Documented patterns for AI tool integration (subprocess isolation for GPL, API-only for AGPL, etc.) | Jun 2026 |
| **AI Act compliance gap analysis** | Complete audit of QA-FRAMEWORK compliance posture with remediation roadmap | Jul 2026 (this sprint) |

---

## 6. Ongoing AI Literacy Actions

| Action | Frequency | Owner | Status |
|--------|-----------|-------|--------|
| **AI model evaluations** | Per new model considered | Research Agent | ✅ Active |
| **AI security research** | Weekly (cron-triggered) | Research + Security Agents | ✅ Active |
| **AI Act compliance monitoring** | Monthly review | Research Agent | ✅ Active (gap analysis Jul 2026) |
| **AI tool security scanning** | Per new tool adoption | Security Agent | ✅ Active (SkillSpector pipeline) |
| **AI literacy onboarding** | Per new team member/collaborator | Research Agent | ⚠️ To formalize |
| **External AI training** | As available | All staff | ⚠️ To formalize |

### 6.1 Recommended External Resources

The European Commission maintains a [living repository of AI literacy practices](https://digital-strategy.ec.europa.eu/en/library/living-repository-foster-learning-and-exchange-ai-literacy) and the [Future of Life Institute](https://artificialintelligenceact.eu/ai-literacy-programs/) curates a database of AI literacy programs aligned with Article 4.

---

## 7. Review Cycle

| Item | Frequency |
|------|-----------|
| **Policy review** | Every 6 months, or upon significant AI Act regulatory change |
| **AI Systems Register update** | When new AI systems are adopted or retired |
| **Competency assessment** | Annual (informal — no formal testing required per EC FAQ) |
| **Regulatory monitoring** | Continuous (Research Agent monitors EU AI Act developments) |

---

## 8. Responsibilities

| Role | Responsibility |
|------|---------------|
| **CEO (Joker)** | Approve policy, ensure resources for AI literacy, final decision on AI system adoption |
| **Research Agent** | Maintain AI Systems Register, monitor regulatory changes, update this policy |
| **Security Agent** | Evaluate AI tool security, maintain red-teaming documentation |
| **All AI Users** | Follow output verification protocols, report AI-related incidents, maintain personal AI literacy |

---

## 9. Related Documents

| Document | Location | Status |
|----------|----------|--------|
| EU AI Act Gap Analysis | `research/eu-ai-act-gap-analysis-2026-07-09.md` | ✅ Complete |
| AI Systems Register (G3) | TBD — DevOps deliverable | ⏳ In progress |
| EU AI Act Compliance (full report) | `reports/research/eu-ai-act-compliance-2026.md` | ✅ Complete |
| Transparency Disclosure (G1) | TBD — OpenCode deliverable | ⏳ In progress |

---

## 10. Regulatory References

| Reference | URL |
|-----------|-----|
| EU AI Act Article 4 (AI literacy) | https://artificialintelligenceact.eu/article/4/ |
| EC AI Office — AI Literacy Q&A | https://digital-strategy.ec.europa.eu/en/faqs/ai-literacy-questions-answers |
| EC Living Repository of AI Literacy Practices | https://digital-strategy.ec.europa.eu/en/library/living-repository-foster-learning-and-exchange-ai-literacy |
| AI Literacy Programs Database (FoLI) | https://artificialintelligenceact.eu/ai-literacy-programs/ |
| Digital Omnibus (Art. 4 softening) | https://www.gibsondunn.com/eu-ai-act-omnibus-agreement-postponed-high-risk-deadlines-and-other-key-changes/ |

---

**Approved by:** _________________ (Joker)  
**Date:** _________________

---

*This policy is proportional to SabaTech's size as an SME per EU AI Act §69(2) and the Digital Omnibus softening of Article 4. It will be updated as the regulatory landscape evolves and SabaTech's AI usage grows.*
