## Why

This is change **H6**, the finalize step, of the WebClient Contextual HUD Redesign, governed by
`docs/superpowers/specs/2026-08-25-webclient-hud-redesign-roadmap-design.md` (depends on **H2**, **H4**
and **H5**).

After H5 the client is the contextual HUD, but three things are still wrong on paper. First,
`docs/superpowers/specs/2026-08-02-webclient-ui-design.md` §5.1 still specifies the three-column
dashboard — the exact document that outranked the migration roadmap and kept the design draft out of
the shipped product for twelve changes (roadmap §1). Leaving it in place would set the same trap for
the next reader. Second, the frozen contract audit and the frozen component manifest describe the
pre-redesign shape, so neither gate protects what actually exists. Third, the migration roadmap's own
`webclient-vue-11-finalize` amendment claimed the source docs had been brought up to date; that claim
is only true of the *technology* line.

H6 removes the contradiction at its source rather than layering another document on top of it.

## What Changes

- **Supersede `webclient-ui-design.md` §5.1 and §5.2 in the document itself.** §5.1's five-surface
  three-column layout is replaced by the stage + anchor model and a pointer to the design draft as the
  binding visual reference; §5.2's visual language is replaced by a pointer to the token system that
  now implements it. §5.3 (focus model), §7 (surface content) and every OOB/presenter section are left
  untouched — they were never in conflict.
- **Record the correction in the migration roadmap.** A short note in
  `2026-08-19-webclient-vue-migration-roadmap-design.md` states that its §1 layout intent was not
  delivered by A1–D1 and is completed by this roadmap, with a link. The migration roadmap's precedence
  table is annotated so no future reader re-derives the superseded chain.
- **Re-freeze the implementation-bound contract audit.** `docs/development/webclient-vue-frozen-contract-audit.md`
  is updated to the post-redesign identifier set: the preserved ids H1 froze, and the complete
  `data-testid` re-map that H1–H5 performed. The audit becomes the binding input for the *next* shell
  change, exactly as A1's audit was for C2/C4.
- **Re-freeze the component manifest** at the complete redesign set, and re-state
  `webclient-component-showcase`'s frozen-set requirement at that set. Deleting the orphaned
  `CharacterPanel` (its surface moved into the `CharacterStatusDrawer` at H4) also retires the
  `CharacterPanel` naming in the showcase main spec's required-set enumeration and the
  "status, character, and skill surfaces" requirement — both re-stated in the change's showcase
  delta so the main spec stays true after the deletion.
- **Extend the deferred-surface assertion** to the complete unbacked list — companion/party panel,
  event-log toasts, a persistent objective tracker, and the intimate/adult collapsible — each named
  with the read model it waits on.
- **Remove genuinely dead view code.** Any component left unmounted and unreferenced after H1–H5
  (its surface having moved elsewhere) is deleted with its story and manifest entry, the way
  `webclient-vue-11-finalize` deleted the retired jQuery plugins. Nothing is deleted while a
  `data-testid` or a story still references it.
- **Lock the final quality gate**: the full managed browser suite green against the redesigned DOM at
  both supported viewports, the anchor-overlap and mode-gating assertions promoted into the standing
  layout journey, and the offline-degradation regression re-run.
- Flip every Status cell in this roadmap's delivery table to `Done`.

## Capabilities

### New Capabilities

(none — H1 introduced `webclient-contextual-hud`; H6 only re-states frozen sets.)

### Modified Capabilities

- `webclient-browser-verification`: the frozen-contract requirement is re-expressed so the freeze is a
  standing obligation renewed at every shell restructure rather than a one-off "before the
  GoldenLayout shell is swapped" event; the layout-behavior requirement gains the stage-anchor
  non-overlap and mode-gating journeys and drops the "minimap containment within its pane" phrasing
  that the island model replaced.
- `webclient-component-showcase`: the frozen-set requirement is re-stated at the complete redesign set.
  **Its base text is the current main spec**, which already carries the synced H4 and H5 edits
  (inventory-bag backed-by-`services.inventory.rows`; the client-local settings state; the deferred
  game-help browser) (roadmap §7: never two archives of the same capability at once).

## Impact

- **Modified:** `docs/superpowers/specs/2026-08-02-webclient-ui-design.md` (§5.1, §5.2),
  `docs/superpowers/specs/2026-08-19-webclient-vue-migration-roadmap-design.md` (correction note +
  precedence annotation), `docs/superpowers/specs/2026-08-25-webclient-hud-redesign-roadmap-design.md`
  (Status column), `docs/development/webclient-vue-frozen-contract-audit.md` (re-freeze),
  `docs/development/frontend-vue-architecture.md` (D6 re-stated: the draft is the layout reference, not
  only the token source), `component-manifest.json` (re-freeze), `AGENTS.md` if any documented frontend
  command changed.
- **Removed:** view components left dead by the redesign, with their stories and manifest entries.
- **Tests:** `web/tests/browser/test_browser_layout.py` gains the standing anchor-overlap and
  mode-gating journeys; `web/webclient-app/tests/overlays/deferred_surfaces_absent.test.js` is extended
  to the complete unbacked list; a top-level Python test verifies the re-frozen audit the way A1's
  audit test did.
- **Preserved / untouched:** the server, every presenter, the action allowlist, the OOB envelope, the
  transport, the bridge, the store, the preserved `js/elosern/*` logic, the keyboard router contract,
  the dependency-free text fallback, and `webclient-ui-design.md` §5.3 / §7 / all OOB sections.
