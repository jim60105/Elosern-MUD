# Design

## Context

See `proposal.md` for the two presentation defects. The confirmed reproduction produced `party.portrait_ref: null` beside an art catalog entry with `origin: official` and `/art/official/.../preset/t_synth_preset/hero.png`, both for a retained selection and for an unselected mounted default.

`web/webclient/presentation/party.py::_resolve_portrait_ref` currently reads `record_for(subject, create=False)` and requires `default_image_id` to occur in `cards_for(subject)`. `world/art/gallery_match.py::resolve_display` already selects a matching equipment-bound card before `official_selection_for`, then the record default. `world/art/presenter.py::resolve_subject` continues with a validated classic asset and `official_default_for`. `resolve_entity` applies the canonical named-subject/age checks and uses that chain. The unchanged art panel catalog entry builder already calls `resolve_entity`.

`GalleryPanel.vue` has `officialEntries` derived from the committed `props.model.official_entries`, independent of the card filter, and `visibleCards` derived from the selected tab. Its empty paragraph currently tests only `!visibleCards.length`.

## Goals / Non-Goals

**Goals:** Make the party gate agree with real-image resolution and make gallery guidance reflect committed official-row availability. Retain exact version-2 payload shapes, owner resolution, row ordering and the initial-letter placeholder for genuinely portraitless companions.

**Non-Goals:** No new resolver, chain branch, server field, client official-art inference, catalog admission policy or membership/bounds change. Keep `world/rules/combat_view.py`, `web/webclient/presentation/dialogue.py`, the art panel catalog entry builder and the art resolution implementation unchanged. Do not modify the intentional preference writers or promote decorative silhouettes to real portraits.

## Decisions

### Delegate the gate to the existing complete presenter resolution

Replace the default-card-only test in `_resolve_portrait_ref` with a read-only call to `world.art.presenter.resolve_entity(npc)`. Emit `portrait_catalog_key(npc.pk)` when the returned payload has a real own `url` and `origin` is `runtime` or `official`; otherwise emit `None`. Use the existing origin constants. This wrapper calls the existing `resolve_display` / `resolve_card` chain projection, `official_selection_for`, classic asset validation and `official_default_for` without reproducing their precedence in `party.py`.

The unchanged precedence is equipment-bound matching card > personal official selection > record default card > classic runtime asset > mounted official default > null. Canonical subject/age eligibility, file validation and URL bounds remain the existing resolver's decisions. A decorative `fallback.url` or `origin: silhouette` cannot satisfy the gate. A malformed/no named subject and a retained selection that no longer resolves remain truthful fall-through cases; a later real-image branch can still resolve.

Do not consult only `resolve_card`: its card-only projection returns `None` for a valid personal official selection. Do not OR together individual branches in `party.py`: that would duplicate chain validation and could disagree with the art panel's wire budget. No new shared abstraction is needed because the full resolver already exists. Remove obsolete imports/docstrings tied to the default-card gate.

The party helper returns a reference only, never a copied image payload or constructed official URL. The art panel continues to build the catalog entry. Same-snapshot acceptance uses a live co-located named companion admitted by the existing art view, including the possessed companion case. Catalog membership, capacity, remote companions and combat participation rules remain unchanged; this fix must not expand the art view to implement portrait resolution.

### Preserve read-only resolution and startup indexing

Every gallery read remains `create=False` or the reader's existing non-creating default; no `create=True`, record creation, attribute/file write, generation queue, seeding or catalog reload occurs while presenting. Official branches read `official.current_catalog()`'s admitted startup snapshot; presentation never walks `ART_OFFICIAL_ROOT`. Existing bounded runtime-file existence checks remain unchanged.

Capture gallery-record existence and contents, relevant entity attributes, queue state and both artwork trees before repeated party/art renders. Assert that they remain unchanged afterward. Add focused spies that fail if render attempts a creating gallery read, write, enqueue or official catalog reload/walk; restrict those spies to the render phase after fixture setup. Do not stub the successful art chain or its catalog entry builder. A mounted-default-only case must prove that `record_for(subject, create=False)` is still `None` after rendering.

`set_official_selection` intentionally clears `default_image_id` and `set_default` intentionally clears the selection. Those semantics and their writer tests remain intact. Official records stay card-less and official files remain read-only.

### Suppress guidance across every card filter

Change the existing paragraph condition to the conjunction `!visibleCards.length && !officialEntries.length`. This is the conservative rule requested. It applies to all, defaults, bound, pending and failed, including a filter with no matches when other card rows exist. Official rows represent the subject's available artwork independently of which card subset is visible, and remain separately rendered.

When committed `official_entries` is empty, retain the exact text `此分類尚無肖像。選擇「生成新圖」，記錄角色的模樣。`, the `gallery-panel__empty` class, and the paragraph's current placement inside the cards area. With visible cards, it remains absent regardless of official entries. Do not use card tab counts, `is_current`, `is_catalog_default`, personal-preference capability, load success or inferred filesystem availability for this decision. A committed replacement of the list must change the paragraph reactively without a dispatch.

A rule limited to the all tab is rejected because it would still claim missing portraits in other tabs while official artwork is available. No replacement copy, style change or new empty-state component is needed.

### Keep showcase and traceability on their existing ownership paths

Extend the existing `Data/GalleryPanel/Storyboard` with explicit deterministic fixture-publication controls for three official rows with zero cards and for zero official rows with zero cards. Derive the first from `GALLERY_EMPTY` plus `GALLERY_SAMPLE.official_entries`, and route both through `galleryStoryModel` so offline media uses committed local assets. Keep the existing `Empty` export genuinely empty. Update the existing frame guide `docs/design/elosern-redesign2/gallery-storyboard.md` to explain the two states and all-tab suppression.

No new story export/family is required, so `web/webclient-app/component-manifest.json` and frozen story ID sets are intentionally unchanged. If implementation adds a story instead, register it in that manifest's supported coverage inventory and update all gallery showcase/evidence ID inventories in the same change without weakening existing coverage. The existing offline storyboard requirement remains sufficient; this change adds no independent showcase capability or requirement.

Extend the existing Python-to-Vitest evidence bridge `web/webclient/tests/test_vue_gallery_ui_evidence.py::VueGalleryUiEvidenceTest.test_official_rows_are_selectable_read_only` to document the new real component assertions and retain its existing literal annotation. Do not attach Python decorators to JavaScript or add a source-string-only pseudo-test. Backend portrait methods receive the existing party requirement's literal annotation only when their assertions establish it.

## Regression and traceability cutover

Canonical IDs below were obtained from `uv run --locked python -m tools.spec_traceability list --json-output <scratch-path>`. The MODIFIED requirement titles stay unchanged.

| Existing or added evidence | Role and action | Canonical requirement claim |
| --- | --- | --- |
| `test_party_panel.py::PartyPresenterTests.test_default_gallery_ref_resolves_in_same_snapshot_and_reads_only` | Synthetic mechanism; retain valid default-card assertions, replace blanket no-default/no-record assumptions with chain-aware cases. Null remains correct when every later branch is absent. | `webclient-party-panel::the-party-panel-is-an-exact-read-only-version-2-presentation-panel` |
| New methods in the existing `PartyPresenterTests` | Synthetic Evennia integration; real selection-only, no-record mounted default, bound-card precedence, classic asset, record default over mounted default, no-artwork/no-subject and read-only assertions. | `webclient-party-panel::the-party-panel-is-an-exact-read-only-version-2-presentation-panel` |
| `world/art/tests/test_gallery/test_record_write.py::OfficialPreferenceWriteTests` | Synthetic mechanism; preserve card-less records and both explicit mutual-clearing pins. Update only an assertion/comment that actually treats absence of a default card as absence of a presentable portrait; never weaken writer invariants. Current lines 401-440 establish storage invariants, not a party gate. | Retain its existing writer annotations; add no party claim without invoking the party consumer. |
| `gallery.test.js` and `test_vue_gallery_ui_evidence.py::test_official_rows_are_selectable_read_only` | Real component DOM assertions executed by the existing evidence bridge; add guidance absence/presence, tab filtering and committed replacement. | `webclient-gallery-ui::official-entries-render-as-selectable-read-only-rows-with-personal-geometry-affordances` |
| Existing `app_client_gallery.test.js` | Keep unchanged unless it asserts the paragraph; no such assertion was found during proposal inspection. | No new claim required. |

Use file-local synthetic `t_synth_preset`-style identities in behavior tests, patch both `official_refs.PLAYER_PRESET_REGISTRY` and `official._registered_preset_keys`, override `ART_OFFICIAL_ROOT` and `ART_STORE_ROOT`, write a minimal valid PNG during setup, load the catalog once, and reset catalog/diagnostic globals with cleanup as in `world/art/tests/test_gallery_match.py`. Set a named portrait policy, valid canonical ages and `creation_preset_key` on the companion. Choose distinct selected/default official images so a selection regression cannot pass by accidentally falling back to the default. Use real bound-card storage and deterministic equipment fixtures for precedence.

Keep tests in existing modules. If any new Python module is introduced, register it exactly once in `.github/evennia-shards.json`; if any browser class/method is added, register it in `.github/browser-shards.json` in the same change. Neither addition is required by this design. Traceability and ownership gates must retain their current strictness.

## Acceptance evidence

| Fixture state | Before, from confirmed reproduction | Required after |
| --- | --- | --- |
| Co-located preset-born named companion; only `preset/t_synth_preset/hero.png` mounted; no gallery record | `party.slots[0].portrait_ref` is null while art has the official image | Non-null ref is a key of the same snapshot's `art.portrait_catalog`; entry `origin` is `official`; URL equals the admitted `/art/official/<fingerprint>/preset/t_synth_preset/hero.png`; record still absent. |
| Same companion and empty official catalog; no runtime image | Null | Null and the client keeps the initial-letter placeholder. |
| Retained resolving selection of `other.png`; no card | Null while art has the selected image | Non-null ref resolves to `other.png`, with `origin: official`. |
| Bound runtime card plus resolving selection | Existing gate depends on the default card | Ref resolves to the equipment-bound runtime image, preserving precedence. |
| Gallery has three official rows, zero cards | Empty guidance is rendered by the current template | Three official rows render; `.gallery-panel__empty` has zero matches. |
| Same gallery has zero official rows, zero cards | Guidance is rendered | Exactly one unchanged paragraph remains inside the cards area. |

Collect party and art panels from one production coordinator snapshot in the official-only regressions, rather than proving only two unrelated helper outputs. Assert the exact expected image URL and origin through the emitted ref. Record pre-fix failure and post-fix pass for new backend and component regressions. The reported backend reproduction is already ground truth; do not rerun a throwaway reproduction merely to confirm it.

### User-visible preset example

The shipped pair `yuna_darknight` / `yuka_darknight` illustrates the fix. A companion born from either preset carries `creation_preset_key`; with admitted artwork in its own `ART_OFFICIAL_ROOT/preset/<creation_preset_key>/` directory, an explicit official selection or the mounted directory default must reach the companion lineup even when no generated card exists. Removing mounted artwork and leaving no real runtime image retains the initial-letter placeholder. These names belong in documentation/notes only; behavior tests use synthetic keys and never depend on shipped artwork.

## Risks / Trade-offs

- A card-only shortcut or silhouette check can emit null for official artwork or fabricate a real portrait. Mitigate with selected/default image distinction, own-URL/origin checks and null/no-subject controls.
- Test-global official catalogs and registry patches can leak across tests. Restore them through cleanup and load only fixture roots.
- Calling the existing resolver for the gate repeats bounded read work when the art panel also renders. Accept that localized cost to keep one chain owner; do not introduce a cache, new payload or per-render filesystem scan.
- Frozen showcase/evidence inventories can reject unregistered story exports. Reuse the existing Storyboard export; register every new export if the implementation deviates.

## Migration Plan

Apply the presenter and template corrections with their regressions as one unreleased change. No data migration, preference rewrite or compatibility path is required. Existing retained selections and absent gallery records work without repair. A rollback reverts the presentation change and its paired tests/docs; it does not alter persisted artwork or preferences.
