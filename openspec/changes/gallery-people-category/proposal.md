# Proposal: the people gallery category

## Batch:

Gallery window programme, stage 2 ("Who is listed" and "Grouping and paging"
of Specification 2 in `docs/superpowers/specs/2026-11-12-gallery-window-design.md`).

- depends-on: met-person-record
- depends-on: met-person-write-points
- depends-on: gallery-window-mount
- depends-on: gallery-mutation-admission
- conflict: `web/webclient/presentation/gallery_categories.py`,
  `gallery.py`, `gallery_selection.py`; `gallery-scene-category` edits the
  same three files later (different functions) — land this first or rebase.

## Why

People are the one category that grows without an author. The design lists
named NPCs the live character has met, grouped by place, with exactly one
place expanded so the panel always carries complete content without a
truncation rule.

## What Changes

- `gallery_categories.py`: a `people` source over
  `world.rules.met_people.met_people(owner)` — exists now, named policy, not
  in the owner's party — one group per place (`place_label`), ordered by
  recency; `people` is enabled.
- `gallery.py`: for `people`, exactly one group is `expanded` (remembered
  place, else most recent); other groups carry `count` and no subjects; the
  selected person falls back to the expanded group's first subject.
- `gallery_selection.py`: `GalleryViewSelection` gains a remembered expanded
  group per category (`expanded` pairs), defaulting to none; no action writes
  it yet (`gallery-group-expansion`).
- The window renders collapsed groups as headings with their counts (already
  supported by `gallery-wall-component`); switching place arrives in
  `gallery-group-expansion`.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `webclient-gallery-categories`: `people` enabled; people source rules.
- `webclient-gallery-panel`: one expanded people group with fallbacks.

## Impact

- Code: the three presentation modules above.
- Tests: `test_gallery_categories.py`, `test_gallery_v4_presenter.py` (or the
  renamed presenter test module after the cutover).
- Estimate: 6 hours (source 2 h, expansion in the projection and store field
  1.5 h, synthetic tests 2 h, gates 0.5 h).
