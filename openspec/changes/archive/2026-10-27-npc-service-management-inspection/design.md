# Design

## Context

web/gm/readers/npcs.py::_professions derives labels from components. identity_section/detail/item_of currently display duplicate profession/title rows; S removes them. services_section currently enumerates component fields. The GM frontend is web/admin-app, separate from web/webclient-app and protected by scripts/gm-import-boundary.mjs.

## Goals / Non-Goals

Deliver `G` as one closed runnable engineer-day slice. Completed prerequisites are the exact depends-on lines in proposal.md.

No new gameplay services, balance, recruitment changes, save migration, legacy input conversion, capability bundles or player class system. The NPC-menu prototype proves layout/navigation only and never authorizes backend behavior. The approved source and archived history remain unchanged.

## Decisions

### Read-only GM representation

Keep NPC identity/list labels plain after S/N and delete residual _professions/COMPONENT_LABELS profession terminology where it represents services. Split services_section into player-facing supported service descriptions and technical capability diagnostics. Reuse P's server-side mapping/labels. With no player actor selected show availability as `context_required` and explicit reason that player context is absent; do not render enabled player operations or pretend the GM is an authorized actor. Configuration facts still report person/place binding, resolved anchor dbref/link, authored service/branch/shop/dialogue/issuer identity, and malformed state independently. Existing public NPC inspection can list service names from the supported mapping without exposing hidden dialogue topic associations; hidden/qualified topic details stay in technical authorized diagnostics, not a fabricated player preview.

The observed reader is detail(npc) and has no actor/viewer preview input. Keep that API unchanged. Do not add impersonation, actor selection or a new preview route in this slice. All contextual availability values in the GM summary are therefore context_required, with an explicit reason; technical binding/anchor/configuration diagnostics remain exact. The shared projection's actor-specific behavior is tested at P and by text/web parity, not fabricated by management.

Keep existing NPC memory/dialogue tabs, persona/version, schedule/current slot, universal raw inspection, permissions and independent failure boundaries. The contextual summary is read-only and never initializes/repairs a component, reveals private player eligibility under another identity or emits ui_action. Player service names and technical fields are separate sections; unreadable diagnostics never become an empty service list.

Render using web/admin-app's existing RuntimeLedger/RuntimeTable primitives and reader section descriptors. Never import ChoiceCard, game composables or any Vue component from web/webclient-app. Server semantics may be imported by readers only. Update docs/development/gm-portal-runtime-inspection.md and GM authoring/operations guidance, stories/test fixtures and current spec.


## Risks / Trade-offs

G follows N/P (therefore S) and shares GM reader/tests/docs with S/D; no game Vue import or publication protocol work is permitted. Current active authored dialogue content may share reference docs only; serialize those documentation edits.

The batch contract in section 11 of `docs/superpowers/specs/2026-10-25-npc-capabilities-and-services-design.md` defines sequential cutover, active proposal amendment ownership, source conflicts and approved-scope traceability. New test files named below are proposed additions, not claims that they already exist. Existing focused labels were researched from current source.

## Worker execution contract

This is planning only. At apply time complete this slice within one engineer-day, using the exact interfaces below. Each checkbox includes its focused regression evidence and documentation. Do not add compatibility exports, legacy input readers, migrations, replacement professions, gameplay services, or a new persistent service registry. Deterministic owners retain every mutation; AI and UI propose/select only. Preserve player titles, ranks, age bounds, literal bases, scene roles/tiers, recruitment and possession eligibility, schedules and commerce arithmetic.

All paths are relative to the repository root. Reuse current test helpers and behavioral traceability decorators. Update `.github/evennia-shards.json` and `.github/browser-shards.json` only for changed test ownership; serialize manifest edits. Run focused checks once after the slice is complete, followed by `uv run --locked python -m tools.contract_gate` and strict validation of its delta. Use the project's test environment only during apply. Full browser/traceability suites remain CI-owned. No implementation checks were exercised during planning.

## Focused verification at implementation handoff

```text
uv run --locked --env-file=.env.test evennia test --settings test_settings.py --keepdb web.gm.tests.test_reader_npcs web.gm.tests.test_read_only_contract
node scripts/gm-import-boundary.mjs
pnpm exec vitest run web/admin-app/tests/runtime-views.test.js
uv run --locked python -m tools.contract_gate
openspec validate npc-service-management-inspection --strict
```

If this slice changes logging paths, also run `uv run --locked python -m tools.observability_lint check` with its focused event tests in the same final batch. Do not run the full browser or full traceability-evidence suite locally.
