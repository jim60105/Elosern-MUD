## 1. The declaration module

- [ ] 1.1 Create `world/art/gallery_kinds.py` with **zero imports**, mirroring `world/art/fallback_keys.py` — the established dependency-neutral pattern in this package. Key the table by the subject kind's declared string value, not by the enum.
- [ ] 1.2 Declare one immutable capability record per kind carrying: has-gallery, store directory segment, maximum card count, and binding support. Declare `scene` explicitly as having no gallery rather than omitting it.
- [ ] 1.2a Type the card maximum as `int | None` where `None` means genuinely unbounded, and declare `character` with `None` — it is uncapped today and must stay uncapped. Do NOT approximate "no cap" with a large sentinel integer; the generalized replace-at-cap rule would then silently cap characters once the sentinel is reached.
- [ ] 1.2b Admit only `None` or `1` as a declared maximum and have the contract test reject anything else. No kind needs an intermediate cap, and admitting arbitrary values would require an N-card eviction algorithm no real declaration exercises.
- [ ] 1.3 Expose the accessors the other modules need — capability lookup by kind value, store directory for a kind, and the reverse directory→kind lookup `gallery_seed.py` builds today — plus the closed set of gallery-bearing store directory segments.
- [ ] 1.4 Make the records and the table immutable (frozen dataclass and a mapping proxy or equivalent) so no consumer can mutate a declaration at runtime.

## 2. Contract and boundary tests

- [ ] 2.1 Contract test: the table holds exactly one entry per `ArtSubjectKind` member — an undeclared kind and a stale entry both fail, each naming the offender.
- [ ] 2.2 Import-boundary test: `world/art/gallery_kinds.py` contains no import statement. Extend the existing `world/art/` import-boundary test rather than adding a parallel mechanism.
- [ ] 2.3 Test that importing the capability table from the gallery prompt layer closes no import cycle.
- [ ] 2.4 Test that a capability record and the table both refuse mutation.

## 3. Route the gallery model through the declaration

- [ ] 3.1 In `world/art/gallery.py`, replace `GALLERY_KIND_DIRECTORIES` with the new accessors and update its exports; keep the store-path shape (`gallery/<kind>/<subject-key>/<image-id><ext>`) byte-identical.
- [ ] 3.2 Make `record_for` and `validate_card` refuse a kind by reading the has-gallery declaration instead of testing membership in the directory dict.
- [ ] 3.3 Make `append_card` enforce the card maximum and the binding rule from the declaration instead of comparing against the monster kind. Preserve today's behaviour exactly: a kind declaring no maximum always accumulates and never replaces; a kind at its declared maximum replaces, deletes the replaced file after the list change commits, and the new card becomes the default.
- [ ] 3.4 Verify the replace path still commits the list change before unlinking, and that a bounded-log deletion failure still leaves the card change committed.

## 4. Route resolution, queue, worker, and seed sync through the declaration

- [ ] 4.1 In `world/art/gallery_match.py`, decide the gallery-bearing guard, the identity prefix check, and the binding-step skip from the declaration.
- [ ] 4.2 In `world/art/queue.py::enqueue_gallery_job`, refuse a kind declared as having no gallery by reading the declaration; keep the typed error and its message shape.
- [ ] 4.3 In `world/art/worker.py`, resolve the gallery output-identity directory segment through the accessor.
- [ ] 4.4 In `world/art/gallery_seed.py`, take the kind vocabulary and the reverse directory map from the accessors, and enforce the surplus-file skip from the declared maximum rather than testing for the monster kind.
- [ ] 4.5 Derive the post-hoc default fixup at `gallery_seed.py:518` (`if had_default or kind is not ArtSubjectKind.CHARACTER`) from the declaration too: a kind needs the fixup exactly when it declares no maximum, because a capped kind's append always sets the default itself. Leaving this as an inline kind comparison would contradict this change's own completeness claim in task 6.5.

## 5. Behaviour-preservation tests

- [ ] 5.1 Assert the enforcement follows the declaration, not the kind: with a kind's declared maximum patched from `None` to `1`, an append replaces instead of accumulating, with no edit to `gallery.py`.
- [ ] 5.1a Assert a character record stays uncapped: many appends retain every card in order, delete no stored file, and leave the first card as the default. This is the regression the sentinel-integer mistake would cause, so test it explicitly.
- [ ] 5.2 Assert a bound card is rejected for any kind whose declaration does not support bindings, and that resolution skips the binding steps for such a kind.
- [ ] 5.3 Assert a kind declared as having no gallery is refused at record creation, card validation, and gallery job enqueue alike.
- [ ] 5.4 Re-run the existing gallery, resolution, seed-sync, and worker suites unchanged — this change alters no observable behaviour, so any existing test needing an edit is a regression to investigate, not a test to update.
- [ ] 5.5 Annotate every new test with `@covers_requirement`, and register any new test module in `.github/evennia-shards.json` in this change.

## 6. Verification

- [ ] 6.1 `openspec validate gallery-kind-capabilities --strict` passes.
- [ ] 6.2 `uv run --locked python -m tools.spec_traceability check` reports zero uncovered requirements.
- [ ] 6.3 `uv run --locked python -m tools.observability_lint check` passes with no new waiver.
- [ ] 6.4 The `world.art` Evennia shard passes with no test changed for behavioural reasons.
- [ ] 6.5 Confirm no remaining gallery capability decision compares a subject kind inline: `gallery.py`, `gallery_match.py`, `queue.py`'s gallery seams, and `gallery_seed.py` — including its post-hoc default fixup — decide every per-kind gallery rule through the declaration. Kind comparisons that are NOT gallery capability decisions — the classic store layout in `presenter.py`, the transport template choice in `sd_worker.py`, and the fallback rule in `gallery_fallback.py` — stay as they are and are out of this change's scope.
