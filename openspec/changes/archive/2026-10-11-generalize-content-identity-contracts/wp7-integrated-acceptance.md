# WP7 integrated acceptance and evidence (tasks 7.1-7.4)

Baseline `master` = `9c3c14f7` (this branch's merge-base). Everything below is an observation
made at apply time in the worktree `.worktrees/generalize-content-identity-contracts`, not a plan.
Every requirement id in this file was produced by `tools.spec_traceability`; none is hand-slugged.

## 7.1 Effective canonical-id map, retired annotations, traceability check

### Zero stale ids (both id forms, whole tree)

The 29 requirements this change REMOVES were scanned in two forms - the canonical
`capability::slug` id from the tool, and the verbatim `### Requirement:` heading text from each
REMOVED delta block - across every tracked text file (`.py .js .mjs .cjs .ts .vue .md .json .yaml
.yml .toml .sh .jsonl`), excluding `openspec/` (the change's own delta specs, the pre-sync current
specs, the archive and the three deferred proposals all hold these ids by design) and `.worktrees/`.

| Form | Scan surface | Hits |
| --- | ---: | ---: |
| canonical `capability::slug` | 2635 files | **0** |
| verbatim `### Requirement:` heading | 2635 files | **0** |

The earlier package-local scans (WP3: "stale removed monster-id sites: 0") agree; this scan widens
the pattern set to the verbatim headings and covers JS/TS/Vue and the freeze/seed metadata.

### The one uncovered requirement: literalized, not waived

`world/lore/tests/test_bestiary_documentation.py` carried its requirement id in a module constant
(`REQUIREMENT = "monster-resource-abilities::bestiary-documentation-covers-keyed-public-content-relationships"`)
and used `@covers_requirement(REQUIREMENT)` at five sites. The checker accepts only literal string
arguments, so those five sites were `dynamic-requirement-id` errors and the ADDED requirement had
**no live carrier** - exactly WP2's recorded obligation
(`wp2-profile-obligation-disposition.md`: "`monster-resource-abilities::bestiary-documentation-covers-keyed-public-content-relationships`
has no test carrier after WP2 ... WP7's zero-carrier acceptance must fail if that carrier does not land").

WP7 inlined the literal id at all five sites (`:95`, `:106`, `:124`, `:345`, `:357`) and deleted the
constant. That is the whole code change of this package; no assertion, name or behaviour moved.

### Traceability check, without allowlists

| Run | Command | Requirements | Associations | Covered | Uncovered | Errors |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| pre-sync (branch tip) | `uv run --locked python -m tools.spec_traceability check` | 2094 | 8465 | 2065 | 29 | **88** |
| post-sync (effective tree) | `uv run --locked python -m tools.spec_traceability --repo-root /tmp/gcic-post-sync check` | 2080 | 8553 | **2080** | **0** | **0** |

The pre-sync run exits 1 with **zero** `dynamic-requirement-id` errors: all 88 errors are
`unknown-requirement-id` naming the change's own 15 ADDED ids, and the 29 uncovered ids are exactly
the REMOVED requirements that still exist in `openspec/specs/` until the archive sync deletes them.
That state is inherent to a removal/addition change and is documented by
`docs/development/spec-test-traceability.md` §Static validation ("在封存流程中，此檢查僅於同步後階段
具權威性 ... 同步前通過並不代表同步後仍會通過").

The post-sync run is the honest end state, and it is produced by the same tool over a tree in which
the 25 delta files have been applied to `openspec/specs/`: 15 ADDED blocks appended, 32 MODIFIED
blocks replaced by requirement heading, 29 REMOVED blocks deleted, 0 unmatched, 0 RENAMED sections,
every MODIFIED heading id-preserving (Matrix A). It reads **0 errors, 0 uncovered, `ok: true`**, and
all 15 pre-sync `unknown-requirement-id` ids resolve. The effective tree lives outside the repository
and is rebuilt from the current worktree before the run; it is a throwaway check aid, never a
repository artifact.

**Which ids remain to be attached post-sync: none.** All 15 ADDED ids already carry literal-id
annotations, and the effective-tree run proves every one of them resolves and is covered
(`monster-resource-abilities::bestiary-documentation-covers-keyed-public-content-relationships`
resolving to 5 associations is the difference the literalization made). What remains is not an
attachment but the sync itself, which creates the ids.

### Why the effective ids are annotated now (tension 1, resolved against evidence)

The assignment suggested the `flexible-game-data-test-design` precedent resolved the same situation
by "annotating only ids that already exist ... then attaching the newly added ids during the archive's
post-sync step". That description does not match the precedent's own commits: `git grep -F` at
`bb7737d1^` (the commit before its archive commit) shows all four ids that change ADDED
(`spec-test-traceability::test-migrations-...`, and the three `test-data-independence::...` ids)
already attached as literal decorators in `tests/test_spec_traceability.py`,
`world/skills/tests/test_skill_registry/test_registry_contract.py`,
`world/rules/tests/test_skill_hit_dependencies.py` and the three resource-skill modules - while none
of the four ids existed in that commit's `openspec/specs/`. It annotated effective ids pre-sync and
let the sync make them resolvable.

That is also what this repository's contract requires. `docs/development/spec-test-traceability.md`
§"同一變更內的需求退役與重新掛載" requires retirement and re-mount in the same implementation, with
effective ids taken from a merged-delta equivalent tree; and `AGENTS.md` allows no waiver for an
uncovered main requirement. The alternative reading (strip the new ids now, re-attach post-sync) was
rejected because it would leave all 15 ADDED requirements uncovered after the sync - an unarchivable
change - and because `openspec/specs/` may not be edited by this change, so no third state exists.

### Direct coverage review of every new and affected requirement

Post-sync association counts (from the effective-tree run), all with meaningful assertions rather
than a count of decorators:

| ADDED effective id | Associations |
| --- | ---: |
| `equipment-effects::equipment-membership-and-stocking-are-authored-data` | 2 |
| `monster-action-policy::authored-monster-kits-use-shared-policy-selection-and-fallback` | 4 |
| `monster-individual-construction::shipped-variants-construct-their-declared-configuration-through-the-common-boundary` | 3 |
| `monster-resource-abilities::bestiary-documentation-covers-keyed-public-content-relationships` | 5 |
| `monster-resource-abilities::delivered-monster-compositions-retain-representative-consumer-evidence` | 8 |
| `monster-resource-abilities::hit-qualified-transfers-credit-actual-removal-once` | 4 |
| `monster-resource-abilities::monster-ability-identity-and-composition-are-authored-registry-data` | 3 |
| `monster-resource-abilities::monster-effects-and-payments-share-the-ordinary-atomic-action` | 4 |
| `monster-resource-abilities::timed-monster-effects-follow-declared-recipients-and-lifetime` | 6 |
| `monster-species-registry::authored-monster-narratives-synchronize-without-a-fixed-roster` | 9 |
| `monster-species-registry::authored-profile-requirements-are-declared-per-variant` | 12 |
| `monster-species-registry::narrative-and-executable-monster-configurations-remain-separate` | 3 |
| `monster-species-registry::shipped-profile-completeness-follows-authored-declarations` | 2 |
| `npc-profile-registry::authored-host-dialogue-preserves-service-semantics` | 8 |
| `npc-profile-registry::every-registry-derived-host-has-complete-individual-characterization` | 15 |

All 32 MODIFIED effective ids are also covered (1-14 associations each; the thinnest are
`altoria-hospitality::each-host-s-dialogue-teaches-what-its-location-is-for`,
`altoria-sanctum::the-sanctuary-s-host-ministers-and-does-not-trade` and
`ciaran-village-commerce::the-village-s-hosts-are-its-own-people`, each 1). **Zero affected
requirements have zero coverage.** Positive and negative halves are both present in the source: the
registry tests carry valid add/rename/retire cases beside missing-required-profile, non-boolean,
unknown-habitat and unknown-parent negatives; the keyed bestiary module carries the wording-only pass
(`LiveBestiaryDocumentationTests`) beside every named structural fault
(`BestiaryRelationshipFaultTests`); the item/shop suites carry valid membership beside shelf,
keepsake and lineage faults (task 7.2 exercises them).

Two recorded caveats, carried forward unresolved rather than smoothed over:

- WP2 N5 (`wp3-composition-consumers-bestiary-disposition.md`): the retired
  `crocodile-ecology-documents-implemented-limits` scenario now survives only as the editorial
  ledger's unjudged prose cell. This audit counts requirement-level coverage, not scenario-level
  coverage; a scenario-level audit would need that note.
- WP3 N5: the bestiary checker judges structure, never semantic accuracy between two prose passages.
  No assertion here claims text understanding.

### Same-change scenario preservation

Every one of the 32 MODIFIED blocks was compared scenario-heading by scenario-heading against the
current main-spec block it replaces: **0 blocks omit a scenario the current spec still has**. This
matters because `openspec validate` refuses such a delta at archive time - it is exactly why the
three deferred monster proposals fail (§7.4). This change's own deltas cannot add a fourth failure.

## 7.2 Integrated valid-edit and malformed-relationship acceptance

Seven acceptance experiments across the five families. Each perturbs shipped data with a real edit,
runs the acceptance labels against it, and is then restored; restoration is proved by
`git status --porcelain` with only the intended source file modified, not by assumption.

| # | Family | Edit applied to shipped data | Command | Observed outcome | Restored |
| --- | --- | --- | --- | --- | --- |
| P1 | bestiary (valid) | reword a published sentence inside a current bestiary section (`docs/lore/bestiary.md`) | `evennia test ... world.lore.tests.test_bestiary_documentation world.lore.tests.test_monster_species_content` | `Ran 30 tests ... OK` - a wording-only edit passes with no spec edit and no prose pin | yes |
| P2 | bestiary (malformed) | break the section index `species: sway_whistle_sparrow` -> `..._typo` | same module | `FAILED (failures=2)`: `sway_whistle_sparrow_typo: documented species is not in the registry` **and** `sway_whistle_sparrow: shipped species is not documented by any current section` - both directions named | yes |
| P3 | monsters (malformed) | `MonsterVariant("grain_pecker", ...)` linked to an unknown parent species | `world.lore.tests.test_monster_species_registry world.lore.tests.test_monster_species_content` | load-time rejection: `MonsterSpeciesRegistryError: variant 'grain_pecker' declares unknown species 'sway_whistle_sparrow_typo'` | yes |
| P4 | NPC personnel (malformed) | blank a real authored keyword response (`GWENAERA_RESPONSES` 綴飾) | `world.lore.tests.test_npc_profile_slice_content world.lore.tests.test_npc_profile_inventory` | `FAILED (failures=1)`: `table ciaran_gwenaera_home has an empty 綴飾 response` - the source and the relationship are named | yes |
| P5 | starter epithet (valid) | replace the shipped `STARTER_EPITHET` display `南門新客` with `南門熟客` | `world.rules.tests.test_guild_rewards world.lore.tests.test_titles_registry` | `Ran 60 tests ... OK` - no behaviour expectation is pinned to the shipped spelling; first-claim, dedupe and slot semantics are declaration-driven | yes |
| P6 | military exception (malformed) | unstock `military_s_sword` from the capital arms assortment | `world.lore.tests.test_assortments world.lore.tests.test_items` | `FAILED (failures=2)`: `'military_s_sword' not found in {...}` and `military_s_sword is registered but no shop stocks it` - the named E-S pair contract still detects it | yes |
| P7 | items/shelf (malformed) | add the non-sellable relic `family_crest_token` to the weapon-only arms shelf | `world.lore.tests.test_assortments` | `FAILED (failures=1)`: `item='family_crest_token'` -> `"is a 'misc', which shelf 'common_arms' does not stock"` | yes |

What the cases demonstrate, per family:

- **Monsters**: a valid add/rename/retirement validates (`test_a_valid_add_rename_and_retirement_keeps_the_registry_valid`)
  while an unknown parent species is refused at load; the generic profile/kit contracts accept
  authored registry edits without touching a spec.
- **Personnel (new-owner NPC)**: `world/rules/tests/test_npc_roster_validation::test_a_new_owner_host_and_table_are_covered_automatically`
  is the valid case - a host and table outside the six retired slices are covered with no
  district-specific test - and the isolated missing profile/card/age/voice/table/owner faults are
  the negatives. P4 additionally proves the live authored tables are checked.
- **Starter epithet**: a valid author replacement passes everywhere (P5) and the first-claim state and
  notification are asserted through a configured synthetic declaration rather than the shipped string.
- **Items/shop/kit**: valid new equipment may be stocked or unstocked and load clean; P7's shelf
  mismatch and the suite's keepsake/precedence and lineage negatives show broken relationships are
  rejected before any wallet, inventory, stock, progress or affinity write.
- **Bestiary**: prose is editable (P1), and the section index is a checked relationship (P2) with
  every named fault (missing/duplicate/orphan/wrong-parent/missing-field/private-reference/status)
  driven through the same pure checker.

**No spec change was needed for any of it.** The acceptance work ran with
`openspec/specs/**` byte-identical to the handover tip: the branch's 103-file diff contains no
`openspec/specs/` file, and the only file this package modifies is
`world/lore/tests/test_bestiary_documentation.py`. Excluded contracts and the six E-S military pairs
are covered by the runs in §7.3 (settlements/topology, clergy and examiner restrictions, service
roster, the tagged military membership tests).

## 7.3 Integrated project-required gates

Run once after the cutover was assembled. Observed outcomes only; nothing below is projected.

| Gate | Command | Observed |
| --- | --- | --- |
| repository contract gate | `uv run --locked python -m tools.contract_gate` | observability `scanned=674 frozen=0 violations=0 exemptions=201`; test-data `scanned=1253 flagged=99 universe=1219+38 quantity-pins=9 violations=0`; manifests OK; contracts `Ran 18 tests ... OK`. The gate fails **only** on the traceability step, for the documented pre-sync state of §7.1 |
| affected-suite acceptance (Evennia) | 16 focused invocations, each <=100 discovered tests | **1005 tests ran; 1001 OK; 4 pre-existing failures** (below). Per invocation: 75, 44, 67, 60, 37, 67, 46, 45, 71, 49, 83 (the economy sync, 227.7 s), 77, 64, 75, 69, 76 |
| repository contract tests (top level) | `uv run --locked python -m unittest` in 5 batches | **419 tests; 418 OK; 1 pre-existing failure** (below) |
| JS: DOM-independent Node suite | `node --test web/static/webclient/js/tests/*.test.js` | `tests 522 / pass 522 / fail 0` |
| JS: Vue component suite | `pnpm test` (Vitest) | `Test Files 166 passed (166)`, `Tests 2100 passed (2100)` |
| JS: GM import boundary | `pnpm run test:gm-boundary` | `tests 23 / pass 23 / fail 0` |
| browser acceptance | `uv run --locked --env-file=... python -m web.tests.browser.unittest_driver web.tests.browser.test_browser_exploration_dialogue` | `Ran 11 tests in 447.174s ... OK` - one affected file, the local class/file budget allowed by `AGENTS.md` |
| requirement traceability | as §7.1 | pre-sync: the documented 88 unknown-id / 29 uncovered state; post-sync effective tree: 0 errors, 0 uncovered |

Real consumer smoke observed inside those runs (not simulation): the persistent-host smoke emitted
committed construction, base-stat and schedule-departure records for the three qualified adventurers,
and the guild-exam lifecycle smoke drove E/D examinations through real equipment (including the
E-S military pairs), rank changes and gear restoration.

Not run locally, with the reason:

- the single full-suite invocation (`evennia test ... --parallel 16 --noinput`): the repository's own
  `evennia-test-guard` extension caps one invocation at 100 discovered tests and refuses a second
  test command in one shell call, so the broad form cannot be executed in this session. The focused
  invocations above cover the same affected surface instead.
- CI shards, the full managed browser suite, `tools.spec_traceability verify --evidence`, coverage
  combine / 80% threshold / XML, and Codecov upload: CI-owned per `AGENTS.md`; no local substitute was
  fabricated, and no test evidence is claimed for them.

Pre-existing failures, reported and not repaired (both proven independent of this change by the
branch diff, which contains none of the files involved):

1. `tests.test_command_docs.CommandDocsContractTests.test_syntax_and_context_match_manifest`: the
   curated manifest's `公會（需當地考核官）` versus `docs/game/command-reference.md`. Neither
   `docs/game/**` nor `tests/test_command_docs.py` is touched by this branch (WP3 recorded the same
   failure on the same inputs).
2. Four showcase-manifest failures in `web/webclient/tests/test_vue_showcase_{overlays,action,data,world}_evidence.py`:
   `Action/ExitCompass` is in the authored story set but missing from those families' frozen
   manifests. `web/webclient-app/stories/Action/ExitCompass.stories.js` was added by commit
   `585b9526` and exists at the merge-base `9c3c14f7`; neither it nor the four evidence tests appear
   in this branch's diff, so the mismatch predates this change.
3. One batching artefact, not a gate failure: running an explicit label set that contains
   `tests.test_creation_parity_contract` *without* a Django-bootstrapping module first raises
   `ImproperlyConfigured` inside an unrelated import chain. `unittest discover` avoids this because
   `tests/test_client_display_vocabulary_contract.py` (and siblings) call
   `django.setup()` at import time; prepending that module makes the batch green (91 tests OK).
   Reported here so the observed single-batch error is not mistaken for a regression.

## 7.4 Strict OpenSpec validation

| Command | Observed |
| --- | --- |
| `openspec validate generalize-content-identity-contracts --strict` | `Change 'generalize-content-identity-contracts' is valid` |
| `openspec validate --specs --strict` | `Totals: 312 passed, 0 failed (312 items)` |
| `openspec validate --all --strict` | `Totals: 315 passed, 3 failed (318 items)` |

The three failures are exactly `fog-mane-lynx-resource-skill`, `ridge-burrow-hare-resource-skill` and
`rock-echo-goat-resource-skill` - the deferred monster proposals of decision D1, each failing because
its own `monster-species-registry` MODIFIED blocks omit scenarios the current spec carries (10 vs 13
and 8 vs 11). They are recorded obligations of their owners, not repaired here, and no fourth failure
was added. The requirement statements this change adds stay well under 500 characters.
