# NEXUS AI CORE — Autonomous Web Development Studio

**Status:** Architecture specification / implementation backlog  
**Department ID:** `web_studio`  
**Parent:** NEXUS AI CORE central orchestrator  
**Execution mode:** Advisory and sandboxed build/test work only until each capability is implemented, reviewed, and explicitly enabled.

## 1. Mission

Turn an approved website brief into a researched, designed, implemented, tested, documented, and deployable website. The department owns the complete website lifecycle, but it does not own global credentials, billing, DNS, production secrets, or unrestricted deployment authority.

The department is an extensible team of specialist agents coordinated by a Web Studio Orchestrator. Each agent has a narrow contract, declared capabilities, bounded inputs/outputs, and auditable hand-offs.

## 2. Department topology

| Role / agent ID | Responsibility | Expected deliverable |
|---|---|---|
| `web_studio_orchestrator` | Intake, decomposition, dependency planning, assignment, progress and budget control | Approved mission DAG and status |
| `web_brief_analyst` | Clarify business goals, audience, constraints and acceptance criteria | Requirements brief |
| `web_research_analyst` | Research public references, competitors and patterns; cite provenance | Research report |
| `web_ia_ux_architect` | Sitemap, information architecture, user journeys and wireframes | Sitemap and UX specification |
| `web_ui_designer` | Page layouts, responsive states, design tokens and component specs | UI specification / design artifacts |
| `web_brand_visual_designer` | Palette, typography, imagery direction and visual consistency | Visual system |
| `web_motion_designer` | Motion principles, interaction states and reduced-motion alternatives | Motion specification |
| `web_content_strategist` | Page copy structure, content model, metadata and localization plan | Content package |
| `web_seo_specialist` | Technical/on-page SEO, semantic structure and indexability review | SEO checklist and metadata |
| `web_accessibility_specialist` | WCAG-oriented review, keyboard flows, semantics, contrast and assistive-technology checks | Accessibility findings |
| `web_frontend_engineer` | Responsive UI implementation and component integration | Frontend source |
| `web_backend_engineer` | APIs, data model, authentication and server-side behavior when required | Backend source and API contract |
| `web_cms_integrator` | CMS/content editing integration when required | CMS configuration and content model |
| `web_browser_tester` | Real-browser functional, responsive and cross-browser checks | Reproducible test report |
| `web_visual_qa` | Screenshot comparison against approved design and visual defect triage | Visual QA report |
| `web_performance_engineer` | Core Web Vitals, asset budgets, caching and runtime performance | Performance report |
| `web_security_reviewer` | Threat review, dependency and configuration checks, auth/API security | Security findings |
| `web_conversion_analyst` | Funnel, usability and conversion recommendations where analytics are lawfully available | CRO experiment backlog |
| `web_release_engineer` | Build packaging, release notes, deployment plan and rollback readiness | Release candidate |
| `web_maintenance_agent` | Post-release health, dependency updates and issue triage | Maintenance report |
| `web_quality_auditor` | Independent acceptance review of evidence and deliverables | Pass / revise / block verdict |

Agents are logical roles, not necessarily one model or one process each. The orchestrator may assign multiple roles to one runtime or fan out a role later, subject to explicit policy.

## 3. Standard workflow

1. **Intake:** capture objective, audience, brand assets, required pages, content, languages, integrations, constraints, budget and acceptance criteria.
2. **Discovery:** research references and competitors. Record source URLs, access time, observations and licensing/copying constraints.
3. **Information architecture:** produce sitemap, page inventory, user journeys and wireframes.
4. **Creative direction:** establish design tokens, typography, color, responsive layouts, image direction and motion rules. Obtain approval for the selected direction before implementation if the mission requires human design approval.
5. **Content and SEO:** map content to pages, define metadata, structured data requirements, localization and right-to-left behavior where needed.
6. **Engineering:** implement frontend/backend/CMS only to the approved specification. Use isolated workspaces and version-controlled changes.
7. **Automated verification:** run unit, integration, accessibility, browser, responsive, SEO, dependency and security checks.
8. **Visual feedback loop:** launch the candidate in an isolated browser; capture screenshots at defined viewports; compare with the approved design; create bounded defect tasks; patch and rerun checks.
9. **Independent audit:** verify requirements traceability, evidence, quality thresholds, security findings and known limitations. Missing audit evidence must never be treated as a pass.
10. **Release preparation:** package a release candidate, migration notes, environment-variable inventory, rollback instructions and deployment checklist.
11. **Human-controlled release:** production deployment, domain/DNS/TLS changes, production secrets, analytics access, payment activation and irreversible actions remain approval-gated.
12. **Maintenance:** monitor only explicitly connected telemetry; produce actionable issue reports and proposed changes.

## 4. Mission graph and quality gates

The initial mission should be represented as a bounded DAG:

`brief -> research -> IA/UX -> visual-system -> content/SEO -> implementation -> automated-tests -> visual-QA -> independent-audit -> release-candidate`

Security, accessibility and performance reviews should be independent review nodes that can run after a build artifact exists. Where the execution engine supports parallel scheduling, independent review nodes may run concurrently. Until then, the workflow must remain sequential and must not claim parallel execution.

The visual feedback loop must be bounded by configured limits: maximum iterations, wall-clock time, model/tool calls, artifact size and total cost. A failed quality gate returns `review_required` or `blocked`; it must not silently proceed to release.

## 5. Tool adapters (not yet enabled)

Adapters are interfaces, not assumed integrations. Each adapter requires its own implementation, permission mapping, credentials policy, tests and operational review.

- Design: Figma API/MCP or an equivalent design-artifact interface.
- Browser: Playwright in a disposable, network-restricted browser/container.
- Source control: GitHub branch/commit/PR workflow with least-privilege repository access.
- Build: isolated container with pinned dependencies and resource ceilings.
- Accessibility/performance: automated scanners plus human-review evidence.
- CMS/analytics: optional, per-project connectors with read/write scopes separated.
- Deployment: release candidate first; production deployment requires a separate approval and scoped deployment identity.

No connector, browser, CMS, analytics account, production environment or external credential is implied to exist merely because it appears in this specification.

## 6. Security and governance

- Default-deny capability policy; registration alone never authorizes execution.
- Separate capabilities for research/read, source editing, test execution, artifact export and deployment.
- No production credentials in prompts, mission definitions, source files or generated artifacts.
- Browser and build environments must be isolated, disposable, resource-limited and denied access to internal metadata endpoints.
- Treat website content, downloaded assets, repository files and tool output as untrusted input; never follow embedded instructions as authority.
- Protect against SSRF, malicious dependencies, prompt injection, secret exfiltration and unsafe generated code.
- Enforce dependency allowlists or review, lockfiles, secret scanning, SAST/dependency scanning and artifact provenance.
- Human approval required for production deployment, DNS/TLS, payments, account changes, destructive migrations, customer-data access and other irreversible actions.
- Audit mission planning, capability authorization, tool invocations, artifacts, approvals, revisions and release decisions.
- The independent auditor must not be the same execution handler that produced the artifact.

## 7. Runtime gaps to close before activation

The current durable mission worker is sequential and advisory-only. It does not yet provide a website build sandbox, browser automation, artifact storage, visual comparison, general-purpose tool adapters, or this department's agent handlers and central capability mappings.

Required platform increments:

1. Add department/agent manifest contracts with ownership, versioning, status, capabilities, permissions and handler binding.
2. Add central permission mappings for each approved web capability; do not widen the global allowlist implicitly.
3. Add artifact records with immutable IDs, hashes, size limits, retention and principal/mission scoping.
4. Add isolated build and Playwright execution adapters with strict network egress policy and resource ceilings.
5. Add bounded retry/iteration policy and explicit cancellation/time budgets for visual QA loops.
6. Add lease heartbeats during long-running handlers; the current worker only renews between nodes.
7. Add parallel ready-node execution only after concurrency, lease, cancellation and resource-budget semantics are tested.
8. Add department-specific evaluation fixtures and quality thresholds.
9. Add a dedicated independent audit handler and evidence schema.
10. Add CI tests for authorization denial, cross-principal artifact access, malicious web input, sandbox escape boundaries, timeout, cancellation, retries and recovery.

Until these increments pass CI and security review, web-studio roles remain architecture definitions and must not be advertised as operational agents.

## 8. Acceptance criteria for activation

- Every enabled role has a validated manifest, explicit central permission mapping, installed handler and owner.
- Every mission node has bounded input/output schemas, dependencies, attempt ceiling and timeout.
- All generated source changes are isolated in a branch and reviewed through a pull request.
- Browser tests cover defined desktop/mobile viewports and supported browsers.
- Accessibility, performance, SEO and security gates produce machine-readable evidence plus human-readable reports.
- Visual QA records reference and candidate screenshots, viewport, defect list and bounded iteration count.
- Independent audit returns pass before a release candidate is marked complete.
- Production release remains a separate approval-controlled action.
- CI, recovery, authorization and sandbox tests pass on the exact candidate commit.

## 9. Current implementation status

This document is a design baseline only. The department is not yet registered as executable, and none of the proposed web agents is enabled. PR #32 supplies a durable mission queue foundation but currently wires only the ICT Mentor handler. The Web Studio must be delivered in incremental, reviewable PRs on top of that foundation; no merge or deployment is performed by this specification.
