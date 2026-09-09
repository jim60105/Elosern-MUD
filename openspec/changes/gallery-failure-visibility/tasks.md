## 1. Gallery error lifecycle and accessor

- [ ] 1.1 In `world/art/gallery.py`, confirm `clear_error` matches the spec's no-op-on-missing-record contract (it must not create a record) and that `record_error` replaces a prior code and timestamp rather than accumulating.
- [ ] 1.2 Add the read-only erroring-subject accessor beside `referenced_stored_identities`, returning each subject that carries a recorded error with its bounded code and timestamp. Re-derive the typed `ArtSubject` from the record's persisted `kind`/`subject_key`; skip a row whose subject no longer parses instead of raising.
- [ ] 1.3 Keep the accessor write-free and lock-consistent with the other reads, and keep the `GalleryRecord` class private to this module — no other module may query it.

## 2. Clear the error on a successful settle

- [ ] 2.1 In `world/art/queue.py::settle_gallery_generated`, clear the subject's recorded error after `append_card` returns and before the spent job record is finished, staying inside the existing `queue_lock -> gallery_lock` order.
- [ ] 2.2 Make the clear non-authoritative: a failure clearing the error must not rewrite the settle's outcome or lose the appended card. Keep `settle_gallery_failed` unchanged — it still records the code and appends nothing.

## 3. Staff status surface

- [ ] 3.1 In `commands/art.py::CmdArtStatus`, add the gallery-state section after the classic listing, reading only through the gallery module's accessors — one line per record with full subject key, valid card count, whether a default is set, and the bounded error code plus its age when one is recorded.
- [ ] 3.2 Apply the existing `[scene|portrait|monster]` kind filter to the gallery section, and keep per-image gallery job records invisible in every section.
- [ ] 3.3 Assert the non-leakage rule holds for the new section: no prompt text, no persona text, no stored identity, no absolute path.

## 4. Staff health counts

- [ ] 4.1 In `CmdArtHealth`, insert the gallery counts as section 4 of five (before the output-policy line): gallery records, total valid cards, and subjects carrying a recorded error.
- [ ] 4.2 Keep the command read-only — the new counts must not create a record, clear an error, or touch a card.

## 5. Staff retry

- [ ] 5.1 In `CmdArtRetry`, add the gallery arm: re-drive every subject the erroring-subject accessor reports through the same validated gallery request seam the automatic paths use.
- [ ] 5.2 Skip an erroring subject the seam rejects (a typed rejection) with no record change, continue the pass, and count only the requests actually issued.
- [ ] 5.2a Clear the recorded error when the seam declines a subject because its gallery is no longer empty — the failure is moot and the automatic guard means nothing else would ever clear it. Keep the error for every other decline reason.
- [ ] 5.2b Rename `world/art/service.py::retry_character_portrait` to a kind-neutral name and update `world/art/tests/test_service.py`'s references. `gallery-monster-generation` generalizes this seam's internals later and must not have to rename it then; doing it here keeps that change free of call-site churn.
- [ ] 5.3 **Remove** the classic-character re-enqueue branch — `queue.failed_keys()` excludes gallery jobs and a character subject no longer owns a classic record, so the branch is unreachable. Leave the classic scene re-enqueue behaviour intact.
- [ ] 5.4 Report both counts (classic re-enqueued, gallery re-requested) in the command's reply.

## 6. Tests

- [ ] 6.1 Cover the error lifecycle: a second failure replaces the first code; clearing a subject with no record creates nothing; clearing leaves cards and the default untouched.
- [ ] 6.2 Cover the accessor: only erroring subjects come back; an empty store writes nothing; an unparseable record is skipped without escaping an exception.
- [ ] 6.3 Cover the settle: a successful append clears a previously recorded error; a later failure records the new code with every existing card intact.
- [ ] 6.4 Cover `@art status`: a failed generation is visible with its bounded code; a healthy gallery shows no error field; gallery job records stay invisible; nothing sensitive leaks.
- [ ] 6.5 Cover `@art health`: the gallery counts line reports the right numbers and the command mutates nothing.
- [ ] 6.6 Cover `@art retry`: an erroring character subject is re-requested exactly once; an ineligible erroring subject is skipped without aborting the pass; a store with no gallery errors requests nothing.
- [ ] 6.6a Cover the moot-error clear: a subject carrying an error that has since gained a card is not re-requested, its error is cleared, and it disappears from the status surface.
- [ ] 6.7 Rewrite `commands/tests/test_art.py::test_retry_skips_a_character_portrait_with_a_non_integer_age` against the gallery arm it now exercises — it currently manufactures a classic character record through `queue.ensure`, a state production can no longer produce.
- [ ] 6.8 Annotate every new test with `@covers_requirement` for the requirements this change adds or modifies.

## 7. Verification

- [ ] 7.1 `openspec validate gallery-failure-visibility --strict` passes.
- [ ] 7.2 `uv run --locked python -m tools.spec_traceability check` reports zero uncovered requirements.
- [ ] 7.3 `uv run --locked python -m tools.observability_lint check` passes with no new waiver.
- [ ] 7.4 The `world.art` and `commands` Evennia shards pass; no new test module was added, so `.github/evennia-shards.json` needs no entry — confirm that is still true before finishing.
