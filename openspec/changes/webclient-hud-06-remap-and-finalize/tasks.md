## 1. Supersede the conflicting layout source

- [ ] 1.1 Rewrite `docs/superpowers/specs/2026-08-02-webclient-ui-design.md` §5.1: replace the five-surface three-column layout with the stage + anchor model, and point to `docs/design/elosern-redesign/` as the binding visual and IA reference and to the HUD redesign roadmap as the owning document
- [ ] 1.2 Rewrite §5.2 (visual language) as a pointer to the implemented token system in `web/webclient-app/styles/tokens.css`, keeping its accessibility statements intact
- [ ] 1.3 Verify §5.3 (focus model), §7 (player-facing surfaces) and every OOB/presenter section are byte-unchanged, and that no cross-reference to §5.1/§5.2 elsewhere in the document is left dangling
- [ ] 1.4 Record the replaced §5.1/§5.2 text verbatim in this change so review can see exactly what was superseded

## 2. Leave the failure mode legible

- [ ] 2.1 Add a dated correction note to `docs/superpowers/specs/2026-08-19-webclient-vue-migration-roadmap-design.md`: its §1 layout intent was not delivered by A1–D1, its §2 Goals reduced the draft to a documentation deliverable, and this roadmap completes it — with a link
- [ ] 2.2 Annotate that roadmap's §3 precedence table where it ranks `webclient-ui-design.md` above itself, so the inversion is visible at the point that caused it
- [ ] 2.3 Leave every `Done` cell in its delivery table unchanged — those changes did land what they specified
- [ ] 2.4 Re-state `docs/development/frontend-vue-architecture.md` **D6** so the draft is the binding layout reference, not only the token source
- [ ] 2.5 Add the HUD redesign roadmap to `docs/_sidebar.md` under 專案設計, next to the existing 「Vue WebClient 設計稿」 entry, and fix that section's mislabelled 「Vue 元件展示」 row (it points at `frontend-vue-architecture`, duplicating the Developer-guides entry)

## 3. Re-freeze the implementation-bound contract audit

- [ ] 3.1 Enumerate the current browser-targeted identifier set: the preserved ids H1 froze, plus every `data-testid` re-map H1–H5 performed
- [ ] 3.2 Update `docs/development/webclient-vue-frozen-contract-audit.md` to that set — renewing the single deliverable, not adding a second parallel list
- [ ] 3.3 Update the top-level Python test that verifies the audit so it checks the renewed list is complete and non-overlapping, the way A1's audit test did
- [ ] 3.4 Confirm the `window.Elosern.*` façade surface and the keyboard-router consumption contract are unchanged by the redesign, and record that finding in the audit

## 4. Re-freeze the component set

- [ ] 4.0 Replace the placeholder Purpose line in `openspec/specs/webclient-contextual-hud/spec.md` (`TBD - created by archiving change webclient-hud-01-shell-and-scene. Update Purpose after archive.`) with the capability's real purpose statement
- [ ] 4.1 Re-read H4's `webclient-component-showcase` delta and take **its** edited requirement text as the base for this change's `MODIFIED` (H4 lands first and corrects the inventory-bag deferral)
- [ ] 4.2 Re-freeze `component-manifest.json` at the complete redesign set
- [ ] 4.3 Extend `web/webclient-app/tests/overlays/deferred_surfaces_absent.test.js` to the complete unbacked list — companion/party panel, event-log toasts, persistent objective tracker, intimate/adult collapsible — each named with the read model it waits on
- [ ] 4.4 Add an assertion that every full overlay has a real trigger in the live surface tree, so a built-but-unreachable overlay fails the gate the way `MapOverlay` / `SettingsOverlay` / `HelpOverlay` silently did not
- [ ] 4.5 `npm run build-storybook` and `npm run showcase-coverage` green at the re-frozen set

## 5. Remove dead view code

- [ ] 5.1 For each candidate component, prove emptiness four ways: no import in `web/webclient-app/`, no `data-testid` reference in `web/tests/browser/`, no story, and no manifest entry after its own removal
- [ ] 5.2 Delete only the components that pass 5.1, together with their stories, Vitest suites and manifest entries
- [ ] 5.3 Delete CSS left dead by the deletions; confirm no rule in `styles/` targets a removed class
- [ ] 5.4 Re-run `npm test` and `npm run build` to confirm nothing imported what was deleted

## 6. Promote the redesign invariants into the standing journey

- [ ] 6.1 Move H1's stage-anchor non-overlap assertion into `web/tests/browser/test_browser_layout.py`'s standing journey so every future change runs it at both supported viewports
- [ ] 6.2 Move the mode-gating assertion (hidden surfaces absent from the DOM and the tab order, present again on mode return) into the same journey
- [ ] 6.3 Add the "complete log reachable in one action from the bounded caption" journey
- [ ] 6.4 Replace the superseded "minimap containment within its pane" phrasing with containment within its HUD island

## 7. Final gates

- [ ] 7.1 Full managed browser suite green against the redesigned DOM at 1440x900 and 1280x720 (CI-owned; H6 must not land on a red CI)
- [ ] 7.2 Re-run the offline-degradation regression: bundle blocked → text playable; incompatible OOB → graphical locked with text round-tripping; art unavailable → gradient stage with gameplay unblocked
- [ ] 7.3 `npm test`, `npm run build`, `npm run build-storybook`, `npm run showcase-coverage` green
- [ ] 7.4 `node --test web/static/webclient/js/tests/*.test.js` green
- [ ] 7.5 `uv run --locked python -m tools.spec_traceability check` green; Python branch coverage at its standing threshold
- [ ] 7.6 `openspec validate webclient-hud-06-remap-and-finalize --strict`, then `openspec validate --all --strict` after archive
- [ ] 7.7 Rebuild `web/static/webclient/app/dist` and verify the running client at both supported viewports
- [ ] 7.8 Flip every Status cell in the HUD redesign roadmap's delivery table to `Done`
