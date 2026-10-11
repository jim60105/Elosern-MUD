# Monster AI roadmap dependency and conflict matrix

This batch covers the entire first approved monster AI roadmap. Changes are implementation slices; attack behavior is complete only after the first five slices, tactical behavior after support, observation and coordination, and rollout after evidence and rollback.

## Dependency and conflict matrix

| Change | Prerequisites | Observable deliverable | Shared edit ownership |
| --- | --- | --- | --- |
| monster-ai-variant-tuning | None | Validate variant-authored intelligence and decision modes while leaving every production variant on legacy. | Shares monster_behaviour.py, rulebook YAML, profile tests and session tuning with attack selection and staged activation; apply those afterward. |
| monster-ai-legal-snapshots | monster-ai-variant-tuning | Create immutable no-write snapshots and share complete deterministic legality with settlement. | Shares action preview/gates and modifier readers with damage estimation and support valuation; serial apply when those extract scalar helpers. |
| monster-ai-bounded-candidates | monster-ai-legal-snapshots | Enumerate semantically legal, deduplicated damage plans under a hard proposal budget. | Shares candidate and target-plan modules with support valuation; support must extend this producer rather than create another one. |
| monster-ai-damage-estimation | monster-ai-legal-snapshots, monster-ai-bounded-candidates | Estimate supported attack health effects with settlement arithmetic and conservative outcome models. | Shares scalar effect settlement and estimation with support valuation; apply scalar extraction before support changes. |
| monster-ai-attack-selection | monster-ai-variant-tuning, monster-ai-bounded-candidates, monster-ai-damage-estimation | Complete production utility attack dispatch with independent sampling, real execution identity and diagnostics. | Shares policy/spec deltas, session policies, combat rounds and overwhelm with observation lifecycle; observation hooks apply after these scope changes. |
| monster-ai-support-valuation | monster-ai-attack-selection | Choose useful existing healing and calculable control through the shared utility selector. | Shares candidates, estimation and utility scoring with observed coordination; scalar support precedes focus scoring. No new ability or state-effect authoring. |
| monster-ai-observation-lifecycle | monster-ai-attack-selection | Collect same-round resolved observations with bounded transaction-safe volatile memory and terminal cleanup. | Shares combat rounds/overwhelm/session lifetime and tuning state with staged activation and attack integration; serialize those writers. Observation eligibility precedes coordination. |
| monster-ai-observed-coordination | monster-ai-support-valuation, monster-ai-observation-lifecycle | Score focus and threat from resolved eligible history without overriding mandatory target rules. | Shares utility scoring, traces and snapshot projections with support and observation lifecycle; apply after both interfaces are complete. |
| monster-ai-manual-evidence | monster-ai-observed-coordination | Provide isolated manual encounter, paired-selector and whole-policy performance evidence outside default tests. | Shares manual operations/report fixtures and documentation with staged activation; activation consumes these reports and must not run the campaign through ordinary gates. |
| monster-ai-staged-activation | monster-ai-manual-evidence | Enable a small named variant set only after complete evidence and demonstrate legacy rollback. | Shares rulebook YAML and AI authoring docs with variant tuning. No production activation can run before manual evidence; no code conflict with unrelated exploration or quest proposals. |

All changes can share .github/evennia-shards.json and release documentation; the dependency-order integration owner resolves those edits. Legal snapshots and candidate enumeration precede effect estimation. Support valuation and observation lifecycle are the only independent substantial slices after attack selection, but their shared snapshot/trace edits require one owner. No unrelated active change is a prerequisite or authorized edit target.

## Roadmap coverage

| Approved source contract | Concrete owner | Establishing evidence |
| --- | --- | --- |
| Roadmap 1, 5, 6; attack 2 | monster-ai-variant-tuning | Strict synthetic loader, actual binding, independently authored same-species variants, unchanged stats and all six profiles |
| Roadmap 2, 3; attack 3, 4 legal gates | monster-ai-legal-snapshots | No DB/handler/timestamp writes, public-only inputs, complete paired cast/interaction rejection, no candidate-proportional ORM work |
| Attack 4 plans, mandatory ordering and budget | monster-ai-bounded-candidates | SELF/NONE/mixed/AREA scales, semantic dedup, seal-before-displacement, real hostile alternative and hard rejected-proposal budget |
| Attack 5 and 6 normalized features | monster-ai-damage-estimation | Independent scalar arithmetic, hit topology, ordered HP, conditional drain, conservative finishing and signed normalized costs/waste |
| Roadmap 1, 6, 9; attack 1, 7, 8, 9 | monster-ai-attack-selection | Production normal/overwhelm attacks, actual repeated slot identity, independent RNG, diagnostics, legacy dice and delta contract cutover |
| Tactics 1 through 4 and 9 support terms | monster-ai-support-valuation | Real useful healing/control settlement, payment-before-heal, mixed audience, concrete marginal next opportunity and no fabricated score |
| Roadmap 7; tactics 6 through 8 | monster-ai-observation-lifecycle | Same-round skills/items/upkeep, nested/outer rollback, terminal cleanup order, reconstruction, isolation and empty restart memory |
| Tactics 5, 9, 10 coordination | monster-ai-observed-coordination | Observed-only focus/threat, live eligibility, two-monster coordination, seal override and initial-memory replay |
| Roadmap 8; simulation 1 through 6 | monster-ai-manual-evidence | 144 real encounters, 128 paired seeds, six situations, isolated persistence, JSON/Markdown uncertainty and warm complete p95 <=50 ms |
| Simulation 7, 8; roadmap 9 | monster-ai-staged-activation | All-legacy starting state, evidence-gated named activation, real affected encounter, focused retuning and demonstrated mode rollback |

## Deliberately unchanged contracts

Monster flee thresholds, FLEE_SKILL_KEY and flee priority remain outside scoring. Non-monster delegated policy remains unchanged. Current effect definitions, base stats, initiative, resolver authority, true-trait arithmetic and transaction journals remain the existing product contracts. AI proposals amend legacy-specific main requirements through change-local deltas only. No durable memory, individual GM override, intelligence inheritance or entity trait copy is added.
