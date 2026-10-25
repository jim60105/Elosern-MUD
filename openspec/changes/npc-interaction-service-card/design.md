# Design

## Context

use-person-focus.js::verbCardRows maps rows to digits and BACK_ROW. stores/elosern/presence.js re-resolves verb keys but cardPickKeys recalculates digit mappings on every key event. ChoiceCard.vue is the existing keyboard composite. Prototype docs/design/npc-service-menu has synthetic routes, CSS-only headings and overflow labels that are not gameplay services.

## Goals / Non-Goals

Deliver `U` as one closed runnable engineer-day slice. Completed prerequisites are the exact depends-on lines in proposal.md.

No new gameplay services, balance, recruitment changes, save migration, legacy input conversion, capability bundles or player class system. The NPC-menu prototype proves layout/navigation only and never authorizes backend behavior. The approved source and archived history remain unchanged.

## Decisions

### One card model and exact order

Keep the existing presenceCard kind verbs. Build a single row list in exploration_menu.js targetMenuFor/verbMenuFor and use-person-focus.js. Group order is common, conditional, services, trailing unnumbered BACK_ROW. Common has invariant key talk/action explore.talk_open at position 1 and look-target/explore.look at position 2. Preserve both when unavailable, with explicit reasons from current server target facts; plain NPC talk is disabled not omitted. Look keeps current visibility/gate semantics. Do not fabricate a callable talk descriptor on the client. P's exploration presenter now must emit a disabled talk affordance for a visible NPC with no conversation and a reason, replacing the old no-talk scenario. This UI slice owns that server adjustment and validator fixtures.

Conditional order is invite, leave, possess, possess_release, deliver, npc_persona. Include only actual currently disclosed descriptors in this order; mutually exclusive controls remain governed by existing eligibility. Monster engage/other non-NPC targets keep their existing target-specific behavior. Services follow P's stable semantic ordering. Paused rows retain key/position. Digits label and activate only 1..9; later rows have no digit badge, remain reachable by arrows/scrolling and do not use another scheme. Return retains Escape and receives no number. Do not truncate services to the affordance limit or promote synthetic merit-exchange/training-yard/license-reissue/loot labels into production routes.

### Accessibility and shared primitive contract

Extend ChoiceCard rows with a group identity/heading model rendered as real labeled groups (`role=group` with aria-labelledby) inside the existing composite. Headings are nonselectable, unnumbered and represented in the accessibility tree; row indices count actionable/focusable rows only. All rows including disabled entries remain in the composite's roving focus; use aria-disabled and click/key guards rather than native disabled buttons that cannot focus. Inline text reasons connect through aria-describedby and are present without hover/color. Visible focus, text scaling, existing scrolling and reduced-motion behavior remain. Enter/Space dispatch exactly once; arrows skip headings, Home selects first row and End the trailing return. Keep current focus trap and pointer behavior; no controller or overlay control strip is introduced.

### Stale mapping and local state ownership

Store an interaction mapping signature on the open card comprising actor identity, selected target identity, room identity, ordered stable row keys, route identities and enabled/reason values. This is client-local menu state, never a server authorization token or global presentation revision. Each pointer/key activation carries the signature from the rendered mapping; compare against the currently committed mapping before resolving by key. On any changed entry set/route/enabled mapping consume the in-flight activation without sending, rebuild rows and require a fresh user selection; never let an old digit index execute a new row. A subsequent fresh keydown/pointer selection may act against the new signature. Do not reset the card on unrelated revision/same-content alignment, and never mutate immutable committed panels.

On committed unavailable exploration/presence or disappeared/invisible target, close the card and retire pending route/read correlation immediately even while submission is locked. Actual departure may flash its existing message once; unreadable presence does not assert departure. A pending talk handover preserves focus only while the target remains committed-present. On services-only unreadable keep common/conditional rows with exact inline `服務資訊暫時無法讀取。` and no stale services. none omits that group. services.open responses must match current actor/transport/card/provider/entry; retired responses cannot reopen the card.

### Focus restoration and real acceptance

Capture origin entry key when opening existing drawer/dialogue/command handoff. On close return focus to that same entry iff actor/card/target/key remain valid; otherwise first valid card row, else originating presence entry, else existing rail/compass fallback. Card close returns to its original presence entry (including overflow origin) when present. Departure closes card/service route, invalidates read callbacks and uses existing rail fallback; do not steal focus from an unrelated valid drawer.

Use the prototype's ten states as scenario coverage only. Its CSS generated headings are replaced with real group labels. Synthetic overflow stays explicitly test-only and uses valid route descriptors with intercepted sends, not fake gameplay backends. Add actual integrated smoke selecting a real merchant, opening the existing shop, completing one purchase through existing confirmation/quantity UI, closing back to its originating service, then stale departure rejection. A real examination request opens the existing rank flow without auto-starting on menu selection. Browser checks exercise keyboard/pointer, group accessibility, all disabled reasons and two viewports after entrance/exit motion settles.


## Risks / Trade-offs

U follows P/X/S and active reading-client/unread-notices/immutable-adoption. Shared use-person-focus, presence.js, ChoiceCard, AppClient, frame-resolvers and tests must be serialized; preserve source-aware reading receipts, notice timing, getCommittedState immutable reads and exact-base publication. Prototype remains unmodified evidence.

The batch contract in section 11 of `docs/superpowers/specs/2026-10-25-npc-capabilities-and-services-design.md` defines sequential cutover, active proposal amendment ownership, source conflicts and approved-scope traceability. New test files named below are proposed additions, not claims that they already exist. Existing focused labels were researched from current source.

## Worker execution contract

This is planning only. At apply time complete this slice within one engineer-day, using the exact interfaces below. Each checkbox includes its focused regression evidence and documentation. Do not add compatibility exports, legacy input readers, migrations, replacement professions, gameplay services, or a new persistent service registry. Deterministic owners retain every mutation; AI and UI propose/select only. Preserve player titles, ranks, age bounds, literal bases, scene roles/tiers, recruitment and possession eligibility, schedules and commerce arithmetic.

All paths are relative to the repository root. Reuse current test helpers and behavioral traceability decorators. Update `.github/evennia-shards.json` and `.github/browser-shards.json` only for changed test ownership; serialize manifest edits. Run focused checks once after the slice is complete, followed by `uv run --locked python -m tools.contract_gate` and strict validation of its delta. Use the project's test environment only during apply. Full browser/traceability suites remain CI-owned. No implementation checks were exercised during planning.

## Focused verification at implementation handoff

```text
pnpm exec vitest run web/webclient-app/tests/app_client_presence_rail.test.js web/webclient-app/tests/choice_card.test.js web/webclient-app/tests/npc_service_card.test.js
node --test web/static/webclient/js/tests/exploration_menu.test.js
uv run --locked python -m web.tests.browser.unittest_driver web.tests.browser.test_browser_npc_services
uv run --locked python -m tools.contract_gate
openspec validate npc-interaction-service-card --strict
```

If this slice changes logging paths, also run `uv run --locked python -m tools.observability_lint check` with its focused event tests in the same final batch. Do not run the full browser or full traceability-evidence suite locally.
