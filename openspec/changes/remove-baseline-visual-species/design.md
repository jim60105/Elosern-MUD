# Design: remove the baseline art-only visual species

## Context

- `world/lore/monster_visuals.py::build_monster_visual_registry` merges
  `BASELINE_VISUAL_ROWS` (twelve rows, `is_baseline_art_only=True`) with
  `adapt_combat_species(...)` over `MONSTER_SPECIES_REGISTRY`, rejecting
  collisions.
- `typeclasses/monsters.py` declares `art_species_key = AttributeProperty(...)`.
  It is read in `world/art/presenter.py::_portrait_subject` (fallback when
  `species_key` is `None`) and in `world/art/official_refs.py` through
  `ART_SPECIES_PROVENANCE_ATTRIBUTE` (the elif arm of the monster reference
  resolver near line 335). No non-test code writes it.
- Existing unregistered-key handling only makes such keys unreachable:
  `queue.py` skips claims and settles, `web/art_media.py` refuses media,
  `gallery_seed.py` skips seed folders. Nothing deletes their stored state:
  `prune_gallery_orphans` (service.py) deletes only unreferenced files and
  gallery jobs whose subject fails `parse_subject`, and `parse_subject` does
  not consult the visual registry. So `GalleryRecord`s, pending jobs and
  classic records of the twelve keys would survive forever and keep their
  files referenced.

## Goals / Non-Goals

**Goals:** registry equals the combat projection; `species_key` is the only
monster visual provenance; no stored record or file of an unregistered monster
key survives a startup.

**Non-Goals:** no change to the tier registry or its example labels (史萊姆,
哥布林, … stay plain strings); no change to official catalog seed handling
(already refuses unregistered folders); no change to retired-tier refusals.

## Decisions

### D1. Registry projection

Delete `BASELINE_VISUAL_ROWS`, the `is_baseline_art_only` field and step 1 of
`build_monster_visual_registry`. The collision error message becomes a plain
duplicate/reserved check over combat species. `MonsterVisualDeclaration` keeps
`stable_key`, `display_label`, `published_appearance_zh`. Update the module
docstring.

### D2. Provenance

- Remove `art_species_key` from `Monster`.
- `presenter._portrait_subject`: read `species_key` only; `None` →
  `(None, "ineligible")`. Docstring drops the fallback sentence.
- `official_refs`: delete `ART_SPECIES_PROVENANCE_ATTRIBUTE`, its `__all__`
  entry and the elif arm; an absent `species_key` returns `None` silently.

### D3. Cleanup through the existing startup prune (chosen over a one-off step)

A one-off cleanup command would be a migration (forbidden pre-release) and
would not catch future registry removals. Instead `prune_gallery_orphans`
gains a record phase that runs BEFORE its file phase:

1. New sole-writer function in `world/art/gallery.py`:
   `delete_unregistered_monster_records() -> int` — under `gallery_lock`,
   deletes every `GalleryRecord` whose `db.kind == "monster"` and whose
   `db.subject_key` fails `is_registered_monster_visual_key`; returns the
   count. Card files are NOT unlinked here (the file phase does it, through
   store-root confinement).
2. `service._gallery_job_is_unclaimable(record)` also returns `True` when the
   record's kind is `monster` and its key is unregistered.
3. New helper in `service.py`: classic records (`not is_gallery_job(record)`)
   with kind `monster` and an unregistered key are deleted; each of their
   `output_identity` and `prior_output_identity` values that resolves through
   `resolved_under_store_root` and exists is unlinked. Classic files live
   outside `gallery/`, so the file phase cannot reach them.
4. The existing file phase then deletes the now-unreferenced gallery files.

Order inside `prune_gallery_orphans`: gallery records → job and classic
records → reference read → file phase. Each phase keeps the existing bounded
`gallery_prune_failed` diagnostics; the final `gallery_orphans_pruned` event
gains a `records_unregistered` context count.

### D4. Tests use synthetic species

Every test that borrowed `BASELINE_VISUAL_ROWS[0].stable_key` or set
`art_species_key` uses `world.tests.synthetic_data.factories.make_monster_species`
under `synthetic_registries` and sets `species_key` instead. Tests that only
asserted baseline rows (`test_monster_visuals.py` lines ~75–160) are rewritten
to assert the projection rule on a synthetic registry, not deleted without a
replacement.

## Risks / Trade-offs

- [A combat species later reuses one of the twelve keys] → harmless: it is
  then registered and its new state is kept.
- [The prune deletes stored art of a species that was removed by mistake] →
  intended; registry removal is an authored act, and art regenerates.
- [Spec purpose text still says "baseline wilderness monsters"] → the archive
  sync edits the main spec's Purpose (workflow follow-up).

## Migration Plan

None beyond the startup prune. Rollback is a git revert; deleted art
regenerates through the normal autogen path.
