# Monster AI Manual Validation and Activation Design

**Date:** 2026-10-11
**Status:** Conversational design approved; written-spec review required before implementation planning.
**Parent:** [Upgrade roadmap](2026-10-11-monster-ai-design.md)
**Dependencies:** [Attack decisions](2026-10-11-monster-ai-attack-design.md) and [tactical support](2026-10-11-monster-ai-tactics-design.md)
**Deliverable:** A small one-time reproducible report and controlled variant activation.

## 1. Owner-approved validation limit

The owner explicitly reduced the handoff's 1,000 encounters per archetype and prohibited repeatedly running the entire campaign in the normal test suite. The initial campaign is 24 encounters per archetype, 144 utility encounters total across six archetypes. The standalone selector check uses 128 paired fixed seeds and runs no encounters.

This campaign is manual acceptance evidence, not a default CI job, a unittest-discovered Monte Carlo test, or a balance-certification requirement. Keep regression tests small and focused on actual defects. Do not automatically run this report generator during ordinary gates, full-suite test discovery, startup, or OpenSpec contract checks.

## 2. Campaign allocation

For each archetype, run six distinct synthetic situations, two fixed seeds, and intelligence 10 and 90. That yields 6 * 2 * 2 = 24 encounters. Change only the synthetic variant's intelligence between each paired comparison; preserve its HP, traits, skill ownership, proficiency, opponents, initial resources, and authored effect rules.

| Situation | Distinct exercised boundary |
|---|---|
| Finishing choice | Healthy versus injured opponents and a credible knockout opportunity |
| Area versus single target | Multiple opponents, uneven remaining HP, and real group coverage |
| Resource exhaustion | Legal useful choices competing for finite MP/HP/other applicable pools |
| Mandatory targeting | Multiple seals and displacement, including a genuinely legal non-strike alternative |
| Tactical support and focus | Useful healing/control and already observed allied pressure |
| Long encounter and lifecycle | Repeated rounds, expiring effects, bounded memory, and terminal cleanup |

Construct all six archetype profiles through the production loader and use synthetic registered species/variants. Do not assert shipped lore keys or numerical balance values in mechanism assertions. Add one separate representative shipped-content smoke only if required to establish authoring/registry binding; label and register it under the repository's data-contract rules.

Each encounter stops at normal terminal settlement or a safety bound of 30 actual rounds. Reaching the bound is reported as an unresolved/capped encounter, never silently counted as a win or loss. A simulator bug or illegal action fails the batch; a capped legal encounter remains visible for interpretation.

Campaign seeds are derived from stable scenario/archetype identifiers and the two documented seed indices using the same versioned stable encoding convention. Record the actual decision and combat RNG seeds. Initialize each encounter with empty tactical memory and isolated persistence so a prior run cannot influence it.

## 3. Standalone selection check

Use exactly two legal candidates with a fixed utility gap of 0.5. Inject the same 128 documented RNG seeds at intelligence 10 and 90, using the production selection function and stable candidate ordering. Record both highest-utility selection counts and their paired difference.

Acceptance requires the high-intelligence count to exceed the low-intelligence count by at least 15 percentage points. Report counts and Wilson intervals for each proportion; do not interpret this isolated selector measurement as an encounter win-rate result. Identical seed/config/input replay must reproduce every chosen candidate.

This check runs once as an explicit manual report operation. Permanent selection regressions cover numerical stability, equal-score behavior, invalid input, deterministic replay, and independent combat RNG with small fixed examples. Do not add the 128-seed check to full-suite discovery.

## 4. Simulator execution boundary

Add a manual report tool using existing uv-managed Django/Evennia setup conventions. Its explicit operations are a selector check, one named archetype campaign, and one performance scenario. A single invocation does not implicitly run all three or all archetypes.

The tool constructs real synthetic entities and drives the existing session/round/resolver boundary, including payment, effect settlement, successful commits, and committed reload. Pure score-only loops cannot stand in for encounter evidence. Network/model services are disabled, and each batch uses an isolated scratch database rather than the user's live game or retained test database.

Separate ordinary and overwhelm smoke operations exercise their respective production contexts and internal round/slot identities. These are focused integration checks; they do not multiply the 144-encounter campaign into a full cross-product. Failure/rollback, restart recovery, and invalid-state cases belong to focused deterministic regressions rather than large encounter campaigns.

Run one archetype's 24 encounters per short local command. If the expected command exceeds ten minutes, reduce the operation into named scenario batches before execution. Do not run CI shard commands or a full managed browser suite for this non-UI feature.

## 5. Report contract

Produce machine-readable JSON with a compact Markdown interpretation. The report includes baseline commit, algorithm/configuration fingerprints, Python/Evennia versions, host/clock details for performance, synthetic scenario declarations, seeds, initial memory, intelligence settings, raw results, approximation flags, candidate budget omissions, and unresolved encounters.

For encounters, report win/loss/capped counts, mean rounds with denominators, highest-utility selection fraction, skill distribution, target concentration, rejected-candidate counts, selected illegal-action count, and wait/no-action count. Separate waits caused by legitimate restrictions from unsupported-estimator exclusion and candidate-budget omission.

Provide raw paired results and uncertainty, avoiding claims of meaningful balance differences from two seeds per situation. The main acceptance claims are valid execution, replay, distinct profiles, and intelligence affecting decision quality while stats remain unchanged. Encounter difficulty need not increase monotonically with intelligence.

Detailed decision traces stay opt-in and contain no queued intent or private model payload. Record enough initial observation data to replay same-process tactics. A replay after restart starts with empty memory unless the report explicitly injects its saved synthetic initial observation snapshot; it does not restore gameplay memory.

## 6. Performance smoke and initial budget

Measure the whole policy call, including snapshot construction, legality, estimation, scoring, sampling, and configured trace overhead. Use monotonic wall-clock timing and count actual ORM queries. Do not time only the final softmax call or exclude preflight costs.

The reference case has 16 live participants, up to 16 owned active skills per deciding actor, mixed single/area/support plans, and a candidate budget of 256. This is a benchmark envelope, not a restriction on live game participant or skill counts.

Perform five warm-up calls followed by 50 measured decisions for legacy and utility, holding the snapshot state fixed and isolating policy dice from resolution dice. Include a cold first-call measurement separately. Report p50/p95, actual examined/accepted/omitted candidates, and query counts. The initial acceptance budget is warm complete utility p95 <= 50 ms on the recorded reference host, with no candidate-proportional ORM work.

Vary the proposed candidate count on the same recorded actor/participant data to expose repeated per-candidate queries. Query work may scale with the initial participant and owned-skill read, but not with subsequent enumeration of their target plans. If the budget fails, profile and improve the path; do not understate the cost by reducing the timed boundary or silently increasing the limit.

This performance operation runs manually once for initial acceptance. It is not a timing assertion in permanent tests. Permanent regressions can cover no state mutation and bounded proposal work without depending on host speed.

## 7. Initial tuning and staged activation

Use the attack design's initial archetype weights and explicit variant intelligence. Initial production variant values are authored independently according to lore; no tier-based intelligence band or monotonic stronger-variant rule is permitted. Record actual selected values in the report/configuration changes instead of asserting them in a second test approval table.

Start with all existing variants on legacy. After attack/tactics regressions, real-path smoke, the small manual report, and the repository contract gate pass, enable a small explicitly named set via `variant_decision_mode`. Verify one affected real encounter and retain the mode switch as the rollback mechanism. Expand only after reviewing valid-action rates, waiting/exclusion causes, resource usage, and observed behavior.

Tuning edits may adjust weights and the temperature curve. A changed affected profile needs its focused scenario rerun; do not automatically rerun every archetype. Report a new fingerprint; earlier claims based on the old tuning no longer hold. Intelligence tuning does not include a statistic rebalance.

## 8. Rollback and release evidence

Switch selected variants back to legacy and start a new session or restart according to the in-process configuration recording contract. No destructive data migration or database restoration is required. Existing active sessions retain their recorded configuration until termination unless a server restart deliberately rebuilds them using startup settings and empty memory.

Demonstrate legacy action behavior in focused smoke after the mode change. Preserve non-monster fallback, flee thresholds, mandatory rules, and normal transaction behavior. A rollback must not report database/resolver exceptions as an AI warning.

Deliver the report, exact reproducible operations, seeds, configuration, focused test output, and exercised smoke evidence. Run `uv run --locked python -m tools.contract_gate` before handoff. Run relevant observability lint with focused tests when logging changes. Register any new non-browser test modules in exactly one Evennia shard; manual tool operations are not test modules.

Completion requires real legal action selection and settlement, useful tactical behavior, explicit variant-level intelligence, the small report, and a demonstrated mode rollback. The report may state that encounter balancing remains uncertain; it must not label unsupported or unimplemented behavior complete.
