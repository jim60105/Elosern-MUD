# WP4 disposition: universal NPC completeness and authored personnel (tasks 4.1-4.5)

Baseline `master` = `9c3c14f7`. This file records what WP4 changed, the split
fixture that proves no location coverage was lost, the retired-id retargeting,
and the boundaries and gaps this package found. It is evidence, not a plan.

## 1. The completeness guarantee after the cutover (task 4.1)

The six per-slice requirements are gone. The replacement is live-source derived
and checked in both directions in two places:

| Where | What it establishes |
| --- | --- |
| `world/rules/npc_roster_validation.py` (`validate_npc_roster`, boot gate) | Derives every actual source, compares it with `NPC_SOURCE_INVENTORY` both ways, and reports each fault against `source kind=… key=…`: missing/stale inventory (owner), missing profile, invalid card, out-of-range age, missing/invalid misunderstanding reply, an authored greeting on a scripted host, an unknown table, a table answered by 0 or >1 hosts, a non-empty owner rule, and an owner that disagrees with the live resolution. |
| `world/lore/tests/test_npc_profile_slice_content.py` (registry contract) | Iterates the derived hosted places, their tables, the qualified people and the companion/template/import kinds. A host, person or table added outside the historical slices is covered with no district-specific test. |

Owner resolution is registry-derived, not an owner list: `PROFILE_SLICES` in
`world/lore/npc_profiles/__init__.py` is now the single declaration the profile
registry is assembled from, and `PROFILE_KEY_SLICES` maps each profile key to
its declaring slice. `derive_shipped_source_owners()` reads it, so a new hosted
place, table or person is owned without editing anything. Only the three
profile-backed kinds have a derivable owner; the three kinds that author no
profile are required to name a non-empty owner. `validate_npc_roster` takes an
injectable `owners` mapping so a synthetic universe can exercise the mismatch
and blank-owner faults.

Fault isolation, each naming the source before sync, is asserted in
`world/rules/tests/test_npc_roster_validation.py`: missing profile, invalid
card, invalid age (bool / negative / out of range), missing and authored
greeting, contract-violating misunderstanding reply, unknown table, table
answered by 0 and by 2, missing inventory row, stale inventory row, wrong owner
on synthetic and on shipped data, blank owner, wrong owner resolution. A valid
new-owner host and its table (a second hosted place under the new label
`test_slice_2`) pass with no district-specific test.

**Deliberate boundary (not a shrink):** place-host inventory rows are checked
for relationship existence and cardinality only; their ages are checked on the
resolved profile. The 25 shipped `place_host` rows carry no `profile_key`/`age`
tuple, so requiring one would either fail the shipped roster or hand-copy every
host age into a second authored file — the host-identity snapshot class this
package removes. The persistent-person rows keep their exact
profile/age/apparent-age binding because they already carry it.

## 2. Split fixture: no location coverage was lost (task 4.2)

`PRE_SPLIT_CONTENT_CAPTURE` in `world/lore/tests/test_settlements.py` — a full
`astuple` row dump including host names, titles, professions, service ids,
profile keys and assortment keys — is split into `PRE_SPLIT_PLACE_CAPTURE`:

| Retained (place's own authored data) | Removed (moved to the live contract) |
| --- | --- |
| place key, settlement key, kind, room name, room description, `exterior_xy`, doorway name, doorway aliases, `host_race`, `host_subrace`, `host_sex` | host name, host title, profession, service id, host profile key, assortment keys, extra/excluded item keys |

The 11 captured keys are unchanged. What proves no location coverage was lost:

- `set(PLACE_REGISTRY) == set(expected)` in
  `test_kind_vocabulary_is_closed_and_covers_the_world_document` pins **all 33
  place keys** and each one's kind.
- `test_place_iteration_order_is_the_load_bearing_slice_order` pins the full
  place key order.
- The 11-key capture pins key, kind, exterior, doorway and description, and now
  also the dwelling lineage values the `ciaran-village-commerce` delta requires
  ("explicit valid authored race, corresponding subrace when declared, and
  sex") — the elf/ciaran/female values for the six village homes and the
  human/None/other defaults for the two capital rows.
- `test_shipped_places_transcribe_the_bootstrap_interiors`,
  `test_a_dwelling_that_trades_is_authored_a_home`,
  `test_courier_capability_authors_branches_in_both_settlements` and the
  hostless all-or-none suite (`test_a_place_may_author_no_host_at_all`,
  `test_a_half_authored_host_names_the_fields_that_break_the_set`,
  `test_a_host_less_place_may_not_sell`, `test_a_stray_subrace_or_kwargs_break_the_absent_host`,
  `test_a_hostless_place_cannot_name_a_host_profile_key`) are untouched.
- In `world/rules/tests/test_guild_config/test_service_host_roster.py` the
  named place pins keep every place key, kind, exterior, doorway name and
  host-less shape for the hospitality lane, the crown-and-watch four and the
  learning-and-exchange three, and the sanctioned hostless set literal
  (`ciaran_shelter`, `altoria_palace`, `altoria_market_stalls`, the two
  silverfeather stations, the three adventurer homes) stays as the shape gate.

Removed from that file: `FORMER_YAML_ROWS`, `ASSEMBLED_ROSTER_ORDER`,
`PRE_CHANGE_BASELINE`, `CIARAN_COMMONS_ROWS`, `HOSPITALITY_ROWS`,
`CROWN_WATCH_ROWS`, `LEARNING_EXCHANGE_ROWS` and their tests. Replaced by
`test_derived_roster_is_the_current_place_delegation_projection`, which checks
both directions (every hosted place contributes exactly one row whose
name/title/profession/anchor/service_id/kwargs are the place's own; no row
exists without a hosted place) and keeps the two cross-registry joins the
hand-authored roster used to synchronize: the guild host's authored identity is
`GUILD_BRANCH_REGISTRY`'s, and each shop host's is its derived
`SHOP_REGISTRY` row's. The frozen-baseline neutrality gate for
`place-attendant-hosts::adding-the-blueprint-changes-no-shipped-host` becomes a
real before/after gate: `test_the_attendant_blueprint_changes_no_shipped_host`
captures the derived rows, registers a synthetic unused blueprint (patched as a
superset of the live profession table), asserts every row is unchanged, then
adds a place declaring that blueprint and asserts exactly one new row whose
components are the blueprint's.

## 3. Personnel declarations, qualifications, profiles and routes (task 4.3)

`world/rules/tests/test_human_guild_hosts.py` gains: a valid changed personnel
declaration (new bases, a reduced gear membership and a new age pair land on the
created host, with the ages read off the swapped profile rather than a second
literal pair); missing and shared person profiles; an unregistered and a hosted
residence; and an invalid residence routine (wrong default state, a move target
outside home/frontage/guild). Every pre-existing test — co-location selection
and fail-closed qualification, normal lineage/gear/equipment, connected weekly
Exit traversal, locked arrival with no teleport, collision-safe key suffixing
with no-reset reuse, and creation rollback — is unchanged.

No rank-owned temporary factory is introduced or relied on: the retired
`guild_examiner` source kind stays asserted as a stale inventory row
(`test_stale_temporary_rank_examiner_source_fails`), and the qualification
registry still selects the authored persistent person. The named examiner rank
and the six E-S military pairs are untouched.

## 4. Independent synthetic identities (task 4.4)

Each area now authors its own explicitly synthetic identity, documented in the
file that uses it, instead of sharing one example name across areas:

| Area | Identity | Consumer assertions kept |
| --- | --- | --- |
| identity / composer (`world/rules/tests/test_npc_identity.py`) | `_EXAMPLE_NAME` / `_EXAMPLE_TITLE` | composition with exactly one U+3000, plain-name degradation for an untitled/malformed/unreadable entity, the 128-code-point panel bound |
| import face (`world/imports/tests/test_batch_all_or_nothing.py`) | `_COLLIDING_KEY` / `_COLLIDING_TITLE` | whole-batch rejection with zero entities persisted, LLMNPC subclass and `PlayerCharacter` targets, a non-NPC key holder not rejecting, batch-internal duplicates failing on their own grounds |
| scene builder (`world/quests/tests/test_scene_builder/_support.py`, `test_characterization.py`) | `SYNTH_OCCUPANT_NAME` / `SYNTH_OCCUPANT_TITLE` | the authored name IS the key, the stripped form reaches key/`display_name`, materialization rollback raises `SceneBuilderSpawnError` with no room or entity persisted |
| HUD exploration panel (`web/webclient/presentation/tests/test_exploration_panel/test_wilderness_and_npc_titles.py`) | `_HUD_NAME` / `_HUD_TITLE` | both row kinds carry the composed name; **new**: each row carries `portrait_ref is None`, so the client's truthful placeholder (name's initial + name) has its only source in the composed display name |

Boundary recorded, not changed: the same example names recur in
`world/quests/_compile_helpers.py`, `test_compile_blueprint.py`,
`test_compile_registration.py`, `test_generated_quest_store.py`,
`test_materialization.py`, `test_portrait_pipeline.py`,
`world/ai/director_templates.py` (shipped template data, not a test) and
`web/static/webclient/js/tests/protocol_fixtures.js`. Those are outside
4.4's identity/import/scene/HUD test scope and keep their own synthetic values.
The portrait-placeholder **initial itself** is a client-side computation
(`web/webclient-app/components/ReferenceArtwork.vue`), covered by the existing
Vitest anchors (`web/webclient-app/tests/core/reference_artwork.test.js`,
`stage_actor.test.js`) that `web/webclient/tests/test_node_suite_evidence.py`
runs, plus the browser acceptance class
`web/tests/browser/test_browser_exploration_dialogue.py`. WP4 did not run the
browser suite locally (per assignment budget); it added the Python-side
precondition assertion above and changed no JS.

## 5. Gap: task 4.5 is NOT implemented

The editorial review ledger, its structural checker, the NPC authoring/test-data
guidance update and the "meaningful retargeting of all six retired slice IDs"
evidence for 4.5 are **not done**. The six retired ids were retired from their
annotation sites (section 6) and re-attached to the two new requirements, but
the ledger that the new
`npc-profile-registry::authored-host-dialogue-preserves-service-semantics`
requirement demands (one dated, dispositioned entry per actual characterization
source, orphan detection, no prose fixture, no freshness claim) does not exist
yet. No expected-dialogue fixture was introduced, and no ledger was fabricated.
Task 4.5 remains unticked; the next owner needs the WP3 precedent
(`world/lore/bestiary_documentation.py`, `docs/development/bestiary-editorial-review.md`,
`world/lore/tests/test_bestiary_documentation.py`).

## 6. Retired and re-attached requirement ids

Six `npc-profile-registry` slice requirements are removed by the delta. Their
annotation sites and the effective requirements each assertion actually
establishes:

| Retired id | Re-attached to | Site(s) |
| --- | --- | --- |
| `…::altoria-lower-terrace-hosts-carry-individual-authored-profiles-and-rewritten-dialogue` | `npc-profile-registry::every-registry-derived-host-has-complete-individual-characterization` + `npc-profile-registry::authored-host-dialogue-preserves-service-semantics` | `world/lore/tests/test_npc_profile_slice_content.py` (now the generic every-source characterization and dialogue tests) |
| `…::altoria-middle-terrace-trade-hosts-carry-…` | same two | same |
| `…::altoria-upper-terrace-hosts-carry-…` | same two | same |
| `…::guild-branch-master-and-rank-examiners-carry-…` | `…-complete-individual-characterization` (+ the inventory id on the person case) | `world/rules/tests/test_npc_roster_validation.py::test_persistent_person_passes_with_no_scripted_home_table`, `::test_qualified_person_missing_profile_is_reported` |
| `…::village-ciaran-first-home-hosts-carry-…` | same two | `test_npc_profile_slice_content.py` |
| `…::village-ciaran-second-home-hosts-carry-…` | same two | `test_npc_profile_slice_content.py` |

Retained-by-sibling ids still directly established by WP4 (recorded so the
"0 stale slice ids" scan is not mistaken for complete claim coverage):
`npc-profile-registry::the-shipped-npc-source-inventory-enumerates-every-source-with-an-owner`
(`test_npc_profile_inventory.py`, `test_npc_roster_validation.py`),
`npc-profile-registry::every-shipped-host-and-examiner-profile-authors-a-bounded-age-pair`
(`test_npc_profile_inventory.py`, iterated over the derived sets),
`npc-profile-registry::one-module-assembles-the-profile-registry-from-owned-slices`,
`npc-profile-registry::the-shipped-npc-roster-is-validated-as-complete-before-the-game-starts`.

`world/lore/tests/test_dialogue_assembly.py` was re-read as task 4.5 asks: its
claim (16 capital tables, fixed slice order, terrace alignment) does not move
under WP4, so neither the file nor its ledger reason is edited.

## 7. Verification actually executed

| Command | Observed result |
| --- | --- |
| `evennia test world.rules.tests.test_npc_roster_validation.ShippedNpcRosterContractTests …SyntheticNpcRosterValidationTests` | 36 tests OK (was 28) |
| `evennia test world.lore.tests.test_npc_profile_inventory world.lore.tests.test_npc_profile_slice_content` | 13 tests OK |
| `evennia test world.rules.tests.test_human_guild_hosts` | 11 tests OK (was 7) |
| `evennia test world.rules.tests.test_guild_config.test_service_host_roster` | 24 tests OK |
| `evennia test world.lore.tests.test_settlements` | 32 tests OK |
| `evennia test world.rules.tests.test_npc_identity world.imports.tests.test_batch_all_or_nothing world.quests.tests.test_scene_builder.test_characterization web.webclient.presentation.tests.test_exploration_panel.test_wilderness_and_npc_titles` | 76 tests, 1 error: `WildernessExplorationPresenterTests.test_wilderness_move_rows_advertise_canonical_destinations` (below); all four WP4 areas pass |
| `uv run --locked python -m tools.test_data_lint check` | `scanned=1252 flagged=98 universe=1219+38 quantity-pins=10 violations=0` (identical to the WP3 baseline) |
| direct `derive_shipped_source_owners(quest_templates=QUEST_TEMPLATE_POOL)` | 53 profile-backed owners resolved; shipped roster validates clean |

**Pre-existing, unrelated failure (reported, not repaired):**
`web/webclient/presentation/tests/test_exploration_panel/test_wilderness_and_npc_titles.py::WildernessExplorationPresenterTests::test_wilderness_move_rows_advertise_canonical_destinations`
fails in isolation with `TraitException: Trait-type 'ordered_level' is invalid.`
raised from `world/rules/sexual_state/handler.py` during
`get_world_clock().advance(...)` inside movement charging. Nothing in WP4's diff
touches clock, traits, sexual state, movement or that class (which WP4 did not
edit); it is annotated to
`webclient-exploration-menu::exploration-move-rows-advertise-canonical-destinations`,
not to any WP4 requirement. It is outside this package and was left unrepaired.

## 8. Ledger and metadata realignment

`tools/test_data_lint_seed.json` and `tools/test_data_freeze.json` carry the
four reason strings `metadata-map.md` Table A/B prescribes
(`shipped NPC source inventory equality contract`,
`registry-derived NPC host characterization and authored dialogue coverage contract`,
`place-derived service host roster and current place-declaration contract`,
`registry-derived NPC roster completeness and fault-diagnostic contract`);
`world/lore/tests/test_settlements.py`'s first docstring line is unchanged as
required. Note for a later owner: running `uv run --locked python -m
tools.test_data_lint seed` **wholesale** rewrites the ledger's curated `debt`
list into `seedDebtPaths ∪ flagged` (337 entries, including 40 paths that no
longer exist on disk), which immediately produces `new-debt` and `stale-path`
violations; the committed ledger's curated `debt` list must be preserved. WP4
therefore edited the four contract reasons in the ledger and the seed together
and gated on `check` (0 violations) instead of committing the tool's wholesale
regeneration. WP7 should decide whether the tool or the ledger is authoritative
before it regenerates anything.

## 9. What WP4 did not do

- Task 4.5 (editorial ledger, its checker, authoring/test-data guidance update).
- No browser suite, Vitest suite, JS file, `openspec` delta spec, deferred
  proposal or `exploration-*` change was edited; no spec requirement statement
  was touched, so `openspec validate --all --strict` (315/3) and
  `--specs --strict` (311/0) are unaffected by this package.
- No post-implementation independent critique of this package was performed
  (the pre-implementation plan critique was, and its five blocking findings are
  folded in as reported in the WP4 hand-off).
