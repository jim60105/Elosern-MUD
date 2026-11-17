# Design

## Context

See `proposal.md`. At the baseline, `CREATION_SCHEMA_VERSION` is 6 in the presenter and browser mirror. Available keys are `schema_version`, `available`, `kind`, `draft`, `presets`, `custom`, plus optional `proposal` (the predecessor brief omitted that existing optional key). `PresetCardView`/`build_preset_cards` carry no artwork; `_serialize_custom` carries no silhouettes. The named-policy writer is `finalize_player_portrait`, which this change never calls.

## Goals / Non-Goals

**Goals:** pure canonical previews and one actor-specific lookup table, with exact mirror rejection.

**Non-Goals:** no asset edits, preset roster edits, queue/policy writes, generation action, portrait panel, layout changes, Telnet changes or fallback-rule retuning.

## Decisions

### Schema and construction boundary

Only this change moves 6 to 7; change 5 moves 7 to 8. Keep the panel-version sentence solely in “The creation panel is an exact read-only creation-mode panel”. Delete the duplicate version sentence from the race-display requirement exactly as recovered. Preserve optional `proposal`, its absence semantics and draft schemas. Both validators reject older/future versions, missing/extra fields and malformed descriptors; no defaulting or trimming into validity.

Keep immutable registry card/control views in `world/rules/creation_wizard.py`. Add read-only preview builders in `world/art/presenter.py`, using `world/art/descriptors.py` and existing geometry/resource construction; serialize via `web/webclient/presentation/creation.py` and validate through `presentation/artwork.py::validate_artwork`. Do not serialize a fabricated entity or call the live-character resolution chain, which could select unrelated gallery/default/policy state. Browser mirror is the protocol source `web/static/webclient/js/elosern/protocol/panels/creation.js`; changing that wire validator is an intentional protocol cutover, not a Vue-only UMD accommodation.

Each `presets[].artwork` is exactly the canonical seven-key descriptor. Its stable subject id is `creation:preset:<key>`. Resolve `official_content_reference_for_preset(card.key)` and the mounted snapshot default, with its fingerprint/geometry. Only that default can be an image attempt. Unadmitted preview defaults produce no image attempt or fault. Always include the alpha terminal; `generation_subject`/`generation_state` are null, `retention_sources` is empty. Never consult an entity’s personal official selection. This preview-specific absence rule does not weaken configured-source fault reporting on existing live subjects.

### The other-sex row is per pending character

Preserve both recovered ADDED requirement blocks, including every scenario, verbatim. Resolve the ambiguity without changing them. Extract a public pure value seam from `gallery_fallback.py::_band_or_hash`, taking `(identity, sex, apparent_age)`; keep its existing entity wrapper and all existing callers’ behavior unchanged. Preview callers supply values directly; no temporary character or attribute mutation.

For custom silhouettes, pass the full identity `portrait:character:<str(actor.pk)>`. This equals the subject the shared finalizer establishes later. The `other` row hashes this identity into each band’s existing ordered pool. It is neither a fixed member nor an arbitrary synthetic id. Build the table separately for each pending character and never cache it globally. Female/male rows use the same resolver’s direct sex entry. This establishes the recovered scenario’s equality for all advertised sexes when later resolution has no registry declaration. A preset preview uses `preset:<key>` instead, because it has no future actor identity and the card’s own declaration still wins.

Build intervals by intersecting the advertised apparent-age range with the child/adult/elder boundaries imported from `gallery_fallback.py`. Do not copy age thresholds into the browser. Every entry is exactly `{sex, apparent_age_minimum, apparent_age_maximum, artwork}`; integer endpoints reject booleans, stay within the advertised range, and minimum ≤ maximum. Every advertised sex has a nonempty complete partition; unknown sexes reject. The table is bounded to 1..16 entries. Its descriptor attempts/retention are empty, generation fields null, and terminal kind `alpha_mask`. Use stable `creation:silhouette:<actor pk>:<sex>:<minimum>:<maximum>` view subject ids within the canonical bound.

### Mechanical source recovery

Copy the three current requirement blocks and apply the generator’s exact replacements, failing if a source sentence is absent. The extractor starts its next-header search after the first header line. Preserve the two added blocks byte-for-byte. The only further source edits remove shipped race/affinity magnitudes and literal localized labels from the copied control scenarios in favor of synthetic registries and registry-relative assertions. These are acceptance-required requirement rewrites, not changed controls or preset counts. The preset bound is a protocol ceiling, never an expected shipped roster size.

The repository CLI additionally requires every existing scenario title to survive a MODIFIED block. Its first strict validation rejected the recovered numeric scenario-title rename. Retain the historical title “Schema version ships as the integer 6” as an identifier while its WHEN/THEN asserts 7 (and change 5 asserts 8 under the same identifier). No runtime version-6 support is retained. This mechanical correction preserves the recovered requirement body and two ADDED blocks without weakening validation.

## Risks / Trade-offs

An actor-specific `other` table prevents global reuse; it avoids a new fallback policy and guarantees future-subject parity. Descriptor additions can exceed the existing panel byte bound; retain the bound and reject the whole oversize payload. Test a valid synthetic maximum-fit payload and a separately oversize payload rather than raising the envelope cap.

## Acceptance and documentation

Extend `web/webclient/presentation/tests/test_creation_panel/test_presenter.py` and `test_validation_core.py`, `world/art/tests/test_gallery_fallback.py` and `test_official_refs.py`, and `web/static/webclient/js/tests/protocol_creation.test.js`. Use synthetic presets with admitted/absent official entries and distinct ids selecting different pool members. Assert no state/queue/file writes, terminal geometry, actor-specific parity, exact coverage and both validators’ rejection matrix. No test pins shipped images, labels, preset count or threshold magnitudes. Update `web/webclient-app/stories/fixtures/creation_panels.js`, protocol fixtures and `docs/development/webclient-synchronization.md` to schema 7 in the same delivery.

Run each focused command independently:

```text
uv run --locked --env-file=.env.evennia-test evennia test --settings test_settings.py --keepdb web.webclient.presentation.tests.test_creation_panel.test_presenter web.webclient.presentation.tests.test_creation_panel.test_validation_core
uv run --locked --env-file=.env.evennia-test evennia test --settings test_settings.py --keepdb world.art.tests.test_gallery_fallback world.art.tests.test_official_refs
node --test web/static/webclient/js/tests/protocol_creation.test.js
openspec validate creation-panel-artwork --strict
```

Expected state: schema-7 fixtures validate on both sides; every malformed case rejects; presentation mutates nothing. Added delta requirements receive real behavior tests now and canonical traceability ids only after main-spec synchronization, per the repository guide.
