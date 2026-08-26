## Context

The redesign is functionally complete after H5. What remains is a documentation and gate problem, and
it is the *same* problem that produced this roadmap: a superseded layout specification left standing at
a higher precedence than the document that supersedes it.

`webclient-ui-design.md` §5.1 is not merely stale — it is *normative*. It is what
`webclient-desktop-shell`'s original "narrative log occupies the primary reading area … non-closable
action dock spans the bottom" requirement was derived from, and it is what every B-wave change of the
Vue migration correctly built to. H1–H5 have already re-expressed the derived OpenSpec requirements; if
the source paragraph survives, the derivation can simply be repeated.

The frozen contract audit has the same shape of problem in a smaller form. It was frozen for the
GoldenLayout → Vue swap and its scenario text says "before the WebClient's GoldenLayout/jQuery shell is
replaced" — a one-time event that has passed. H1–H5 performed exactly the operation that requirement
governs (preserve or re-map every browser-targeted identifier) with no standing obligation compelling
them to.

## Goals / Non-Goals

**Goals**

- Delete the contradiction at its source: rewrite §5.1/§5.2 rather than adding a third document.
- Leave a forward-pointing trail in the migration roadmap so the failure mode is legible, not erased.
- Turn the contract freeze into a renewable obligation instead of a one-off event.
- Re-freeze both gates (audit, manifest) at what actually ships.
- Remove code the redesign made dead, with the same discipline `webclient-vue-11-finalize` used.

**Non-Goals**

- No behaviour change. If a browser assertion fails in H6, the fix belongs to the wave that owns that
  surface, not here.
- No edit to `webclient-ui-design.md` §5.3, §7, or any OOB/presenter section — they never conflicted.
- No new capability, no new component, no server change.

## Decisions

### D1 — Rewrite §5.1/§5.2 in place; do not add a fourth layout document

The migration's mistake was additive: the draft landed *beside* §5.1 instead of *replacing* it, so two
layout specifications coexisted and the older one outranked the newer. H6 edits the paragraph, marks it
as superseded-and-replaced with a dated pointer to this roadmap and the draft, and leaves the rest of
the section numbering intact so existing cross-references (`§5.3`, `§7`) keep resolving.

*Alternative rejected:* a deprecation banner at the top of §5. A banner does not stop a reader who
lands directly on §5.1 from a cross-reference, which is precisely how B1 reached it.

### D2 — Annotate the migration roadmap rather than editing its history

`2026-08-19-webclient-vue-migration-roadmap-design.md` is the record of a completed migration. H6 adds a
dated correction note — its §1 layout intent was not delivered, its §2 Goals reduced the draft to a
documentation deliverable, and this roadmap completes it — and annotates the §3 precedence table where
it ranks `webclient-ui-design.md` above itself. The delivery table's `Done` cells are **not** altered:
those changes really did land what they specified.

*Alternative rejected:* retroactively marking the migration incomplete. It was complete against its own
contract; the defect was in the contract, and recording that honestly is more useful than reclassifying
the work.

### D3 — The contract freeze becomes a standing obligation

The `MODIFIED` delta on `webclient-browser-verification` re-expresses the requirement from *"before the
WebClient's GoldenLayout/jQuery shell is replaced"* to *"before any change that relocates a
browser-targeted identifier"*, with the audit as the renewed deliverable. This is what H1–H5 already
practised (roadmap §5: each wave re-maps what it breaks); H6 makes the practice enforceable for the next
restructure instead of relying on a roadmap that will itself be archived.

*Alternative rejected:* leaving the requirement event-scoped and adding a new one for this redesign.
That produces a requirement per restructure and no general rule.

### D4 — H6's showcase delta is based on the current main spec

H4 corrected the frozen-set requirement's factually wrong deferral of the inventory bag (it *is* backed
by `services.inventory.rows`), and H5 extended it with the client-local settings state and the deferred
game-help browser. Both changes have since landed and been archived, so their edits are synced into the
main spec. H6 re-states the same requirement at the final component set, and its MODIFIED text is taken
from the **current main spec** (not from H4's archived delta), so archiving H6 does not silently drop
the H4/H5 edits. H6 adds only its own deltas: the persistent objective tracker in the deferred list,
the re-frozen manifest wording, and the overlay-trigger assertion.

*Alternative rejected:* folding the re-freeze into H4. H4 cannot know the final set — H5 adds
components after it.

### D5 — Dead-code removal is evidence-driven, not assumed

A component is deleted only when a grep shows no import, no `data-testid` reference in
`web/tests/browser/`, no story, and no manifest entry after its own removal. The likely candidates are
surfaces whose content moved (the boxed art panel after H1's backdrop, the right-column panel wrappers
after H4's drawers), but H6 asserts emptiness rather than predicting it. Deleting a component that a
browser test still targets is exactly the failure this change exists to prevent.

### D6 — Promote the redesign's invariants into the standing layout journey

H1's anchor-overlap assertion and the mode-gating assertion currently live in their authoring wave's
test slice. H6 moves them into `test_browser_layout.py`'s standing journey so every future change runs
them, and drops the superseded "minimap containment within its pane" phrasing that the island model
replaced.

## Risks / Trade-offs

- **Rewriting a source-of-truth document is irreversible in review terms.** → The edit is scoped to two
  numbered subsections, the replaced text is quoted in the change's own record, and §5.3/§7 are
  explicitly untouched so the blast radius is inspectable.
- **H4, H5 and H6 all touched the showcase frozen-set requirement.** → Roadmap §7's topological-archive
  rule plus D4's instruction that H6's MODIFIED text is based on the current main spec (which already
  carries the H4 and H5 edits), so archiving H6 cannot drop those edits. `openspec validate --all
  --strict` after each archive is the check that the base was correct.
- **Dead-code removal can break a gate no one is running locally.** → D5's four-way emptiness proof plus
  the full managed browser suite in this change's gates; the suite is CI-owned, so H6 is the wave that
  must not be landed on a red CI.
- **The correction note could read as blame.** → It is written as a contract defect with a traceable
  cause (roadmap §1's four steps), not as an execution failure. The migration's `Done` cells stand.

## Migration Plan

No runtime migration; 0 released users. Rollback is `git revert` — the change touches documentation,
the manifest, tests, and deletions, so a revert restores the deleted components alongside their
manifest entries and stories in one commit.

## Open Questions

None. The one deferred decision — which components are actually dead — is answered by D5's evidence
procedure at implementation time rather than guessed here.

## Record of the replaced §5.1/§5.2 (task 1.4)

The replaced text, quoted verbatim from `2026-08-02-webclient-ui-design.md` before H6's in-place
rewrite, so the review can see exactly what was superseded:

> ### 5.1 Default desktop layout
>
> The default layout has five required surfaces:
>
> 1. A narrow header shows the game title, location, world date/time, and connection state.
> 2. The narrative log occupies roughly two-thirds of the main content area.
> 3. The right rail shows a 16:9 scene image with a 3:4 contextual portrait overlaid at bottom right.
> 4. The lower right rail splits character status and the local minimap.
> 5. A non-closable action dock spans the bottom.
>
> Players may resize panels. The saved layout configuration (the Vue layout store) includes a project
> layout version. When required component names or layout structure change, known old versions are
> migrated. An unrecognized version is reset to the approved default. The action dock, connection
> state, and command drawer entry point cannot be removed by a stale localStorage layout.
>
> ### 5.2 Visual language
>
> - Backgrounds use charcoal and near-black rather than pure black.
> - Primary text uses warm paper gray.
> - Vermilion marks active focus, current map position, and critical warnings.
> - Borders, icons, labels, and shapes accompany every color distinction.
> - Serif typography may be used for narrative and headings; controls use a highly legible UI face.
> - Art never carries text required to understand state.
> - Reduced-motion preference disables nonessential transitions.

§5.3 (focus model) and §7 (player-facing surfaces) are byte-unchanged; the twelve cross-references to
§5.1/§5.2 all live in `2026-08-25-webclient-hud-redesign-roadmap-design.md` and keep resolving
because the section numbering is preserved.
