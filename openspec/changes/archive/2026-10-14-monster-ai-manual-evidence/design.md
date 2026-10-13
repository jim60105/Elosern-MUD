# Design

## Context

Approved simulation design replaces the original large campaign with 144 encounters and 128 paired selector seeds. The repository uses uv-managed Django/Evennia setup, synthetic fixtures and explicit shard ownership. No manual campaign belongs in full-suite discovery or contract_gate. The approved source contracts are docs/superpowers/specs/2026-10-11-monster-ai-design.md, docs/superpowers/specs/2026-10-11-monster-ai-attack-design.md, docs/superpowers/specs/2026-10-11-monster-ai-tactics-design.md and docs/superpowers/specs/2026-10-11-monster-ai-simulation-design.md. Architectural authority remains docs/superpowers/specs/2026-07-29-ai-mud-engine-design.md, including true traits and deterministic single-writer settlement.

## Goals / Non-Goals

This slice delivers the requirements in specs/monster-ai-manual-validation/spec.md with a one-engineer-day implementation boundary. The implementation tasks are bounded to at most 90 minutes each; documentation and focused integration complete the same change. Dependencies supply already completed interfaces rather than hidden implementation work.

No stat rebalance, new ability, cooldown, phase mechanic, patrol, behavior tree, GOAP, durable memory, per-monster GM editing, GM UI, player command, migration or compatibility layer is included. Legacy is a permanent product mode. Intelligence is never inferred from species, tier, ordinary/stronger rank or archetype; player-facing wording uses `智慧`.

## Decisions

Provide an explicit manual tool with separate selector, named-archetype campaign and performance operations, plus focused ordinary/overwhelm smoke. Each operation uses isolated scratch persistence and disables network/model access. Synthetic registered variants have identical stats and independent intelligence 10/90. Reports preserve raw paired outcomes and approximation limits. Permanent tests establish tool contracts using tiny deterministic fixtures, never rerun the campaign.

Use focused modules under world/rules/monster_ai/ only when their actual behavior is implemented. Proposed responsibility names are models, candidates, estimation, utility, selection and trace. Keep orchestration identity/observation lifetime in existing combat/session owners and rulebook validation in its current owner. Extending one centralized behavior module would combine unrelated lifetimes. Calling handlers or a copied-entity dry-run resolver would risk writes, reactions and resolution RNG; neither alternative is permitted.

## Risks / Trade-offs

Approximation can change candidate preference. Record conservative limits and exclude unknown harmful outcomes rather than invent value. The resolver repeats legal checks after earlier actions, so predecision validity cannot promise settlement after state changes. Real normal/overwhelm context includes simulation and companion nonlethal policies; projections and finishing must respect actual recipient floors.

Shared files and shard manifests can conflict. Apply dependencies first and assign one integration owner to shared edits. Synthetic fixtures establish independently known mechanism outcomes. Shipped roster/prose/weight assertions and private source-layout tests cannot establish behavior.

## Migration Plan

This pre-release change adds no data migration. Existing production variants remain legacy until monster-ai-staged-activation consumes accepted evidence. Session configuration stays recorded in process until termination; restart reconstructs with validated startup tuning and empty history. Rollback uses the retained mode switch and a new session or deliberate restart, with normal transaction boundaries.

## Behavioral evidence and ownership

Use world.rules.tests.test_monster_ai_manual_reports as the focused new test module where a new module is needed, and extend the existing tests named by the observed boundaries. Register each added non-browser module exactly once in .github/evennia-shards.json. Manual tools are not test modules. Tests classify synthetic mechanisms, registry contracts or representative smoke under the existing data-contract conventions.

Generate canonical requirement IDs using tools.spec_traceability against the equivalent delta-applied spec tree; never guess IDs. Attach covers_requirement only where assertions establish the contract. MODIFIED headings retain their current IDs but require a substantive assertion review. Any replaced source-only assertions need actual provider/settlement/state regressions.
