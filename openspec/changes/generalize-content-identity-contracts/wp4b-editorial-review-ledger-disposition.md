# WP4b disposition: NPC characterization editorial ledger (task 4.5)

Baseline `master` = `9c3c14f7`; handover branch tip = `29b8673b`. This file
records what task 4.5 delivered, how the ledger's structural check works, how
the "no expected dialogue fixture" claim is proved, and the state of the six
retired slice ids. It is evidence, not a plan.

## 1. What 4.5 added

| Artifact | What it is |
| --- | --- |
| `world/lore/npc_editorial_review.py` | The pure parser/checker: `parse_npc_editorial_ledger`, `unparsed_ledger_rows`, `check_npc_editorial_ledger`, `LEDGER_FACES_BY_KIND`, `LEDGER_ROW`, `LEDGER_DATE`, `LedgerEntry`. No file, DB or `world.*` import. |
| `docs/development/npc-editorial-review.md` | The dated, source-indexed ledger: 60 rows, one per live source. |
| `world/lore/tests/test_npc_editorial_review.py` | Drives the ledger against the actual derived source set and every named fault with synthetic rows. |
| `docs/development/adding-npcs.md` §Step 3.3 | NPC authoring guidance: the ledger, the checker, the same-change update rule, per-table keyword uniqueness, no global keyword uniqueness, no prose fixture. |
| `docs/development/evennia-testing-guide.md` §NPC 人物設定與台詞的審查紀錄 | Test-data guidance: the ledger is the review record, prose is never pinned. |
| `docs/_sidebar.md` | The ledger link beside the bestiary ledger. |
| `tools/test_data_lint_seed.json` + `tools/test_data_freeze.json` | `world/lore/tests/test_npc_editorial_review.py` registered in both `contract` lists with the one reason string `registry-indexed NPC characterization editorial review contract`. |

This mirrors the WP3 precedent (`world/lore/bestiary_documentation.py`,
`docs/development/bestiary-editorial-review.md`,
`world/lore/tests/test_bestiary_documentation.py`) in the shape the accepted
design D2 names: a dated editorial ledger in place of expected prose, with
structural checks, not a fixture containing the expected dialogue.

## 2. The ledger's index and its structural check (orphan detection)

Rows are indexed by the pair the live registries actually derive - `(kind, key)`
from `world.rules.npc_roster_validation.derive_shipped_sources`. A pair, not a
bare key, is required: `altoria_tailor`, `altoria_jeweller` and
`altoria_alchemist` are each both a `place_host` key and a `dialogue_table` key
(`world/lore/npc_profiles/inventory.py`), and the live derivation ships 60
pairs (25 `place_host`, 25 `dialogue_table`, 3 `persistent_adventurer`, 4
`starting_companion`, 1 `quest_template_occupant`, 2 `import_example`).

`check_npc_editorial_ledger(sources, entries)` returns one problem string per
broken relationship, each naming the source:

- **orphan** - an entry whose `(kind, key)` is not a live source:
  `"<kind>:<key>: ledger entry for an unshipped source"`.
- **missing** - a live source with no entry:
  `"<kind>:<key>: no editorial review entry"`, computed from
  `sorted(set(sources) - seen)` so it is caught even when orphan rows are
  present.
- **duplicate**, **unknown kind**, non-`YYYY-MM-DD` **date**, per-kind
  **face-count** mismatch, a blank **face**, and a blank overall
  **disposition**.

Orphan detection has one silent-drop path - the anchored regex skips a
row-shaped line it cannot parse - and `unparsed_ledger_rows` closes it: any
line that starts a table row and carries a backticked token but does not parse
is returned verbatim, and the live test asserts that set is empty. A dropped
live row would also surface as a missing entry, but a dropped *orphan* row would
otherwise be invisible.

Which faces a kind owns is declared once, in `LEDGER_FACES_BY_KIND`
(`place_host`: profile/card/voice; `dialogue_table`:
greeting/responses/service-semantics; `persistent_adventurer`:
profile/card/voice; `starting_companion`: card/voice;
`quest_template_occupant` and `import_example`: card). `import_example` carries
no greeting field - its two shipped cards write only `persona` and the roster
gate validates them through `validate_character(record, NPC)` - so its single
authored surface is the card.

## 3. No expected dialogue fixture, and no freshness claim

- The ledger records dates and dispositions only; it never quotes a shipped
  spoken line. `test_the_ledger_is_not_an_expected_dialogue_fixture` collects
  every shipped spoken line across all six kinds - the 25 dialogue tables'
  greetings and keyword responses, every host's and persistent person's
  `voice.greeting`/`voice.misunderstood`, and every companion preset's offline
  greeting - asserts the long-line population is at least the dialogue corpus
  (so a membership hit would be a real quotation rather than a coincidence),
  and asserts none of the lines occurs in the ledger text.
- `test_a_wording_only_edit_of_the_ledger_still_passes` rewrites a
  disposition-cell phrase and a face-cell phrase (separately) and asserts each
  edit leaves the relationship check returning `()` with the entry count
  unchanged; it also asserts the disposition edit changes at least one line per
  entry, so the ledger's own prose is provably freely editable in both cell
  kinds.
- The module docstring, the ledger header and both guides state that the record
  proves coverage, never prose quality, and that it does not establish a review
  is still fresh after a later content edit.
- Dialogue prose is likewise not pinned by any test: the shipped-corpus test in
  `world/lore/tests/test_npc_profile_slice_content.py` checks absence of
  command/mechanic tokens and per-table keyword uniqueness, and never compares
  a line to an expected string.

## 4. The six retired slice ids and their retargeting

All six `npc-profile-registry` slice requirements are removed by the delta and
none survives as an annotation. The scan is reproducible: a gitignore-off grep
over the whole worktree for the six retired slugs
(`altoria-lower-terrace-hosts-carry`, `altoria-middle-terrace-trade-hosts-carry`,
`altoria-upper-terrace-hosts-carry`,
`guild-branch-master-and-rank-examiners-carry`,
`village-ciaran-first-home-hosts-carry`,
`village-ciaran-second-home-hosts-carry`) matches exactly three files, all of
them this change's own planning artifacts, and zero annotation sites:

1. `cutover-matrix.md` - Matrix A rows 47-52 and the six Matrix B rows for
   `world/lore/tests/test_npc_profile_slice_content.py`.
2. `scope-inventory.md` - the six "Current annotations" sections.
3. `wp4-completeness-personnel-disposition.md` §6.

Those are the retirement records D3 requires, not live claims. In particular no
file under `docs/` (including `docs/superpowers/specs/`, whose only
`npc-persona-*` document is `2026-10-01-npc-persona-authoring-design.md`, which
names change labels and not requirement ids) carries any of the six slugs.

The retargeting itself is the two live requirement ids
`npc-profile-registry::every-registry-derived-host-has-complete-individual-characterization`
and `npc-profile-registry::authored-host-dialogue-preserves-service-semantics`.
`world/lore/tests/test_npc_profile_slice_content.py` and
`world/rules/tests/test_npc_roster_validation.py` now carry them at real sites
covering the whole derived corpus, not the six historical slices.

**4.5 fixed one defect in that retargeting.** WP4's sites in
`world/lore/tests/test_npc_profile_slice_content.py` annotated through module
f-string constants (`_CHARACTERIZATION`/`_DIALOGUE`). `tools/spec_traceability`
accepts only literal decorator arguments (AGENTS.md: "Arguments must be literal
IDs"), so those 8 sites raised `dynamic-requirement-id` and recorded **no**
association - the retargeting was invisible to the gate. 4.5 replaced the
constants with literal strings and deleted them, which is what makes the
retargeting meaningful rather than nominal. Before: 8 `dynamic-requirement-id`
errors at that file. After: the two new ids appear as `unknown-requirement-id`
at 8 sites in that file plus the literal sites in
`world/rules/tests/test_npc_roster_validation.py` and the 5 sites in
`world/lore/tests/test_npc_editorial_review.py`; `unknown-requirement-id` is the
documented pre-sync state (the ADDED requirements do not exist in
`openspec/specs/` until the delta is applied) and resolves to a real
association then.

**Recorded obligation for WP7 (not 4.5's file, not silently absorbed):** the
same defect remains in WP3's `world/lore/tests/test_bestiary_documentation.py`
at lines 97, 106, 122, 341 and 351, which annotate
`monster-resource-abilities::bestiary-documentation-covers-keyed-public-content-relationships`
through a `REQUIREMENT` constant. WP7's zero-stale-id / meaningful-coverage gate
needs those five literals too; 4.5 left them because the monster family is
another package's delivered work.

## 5. Keyword/service semantics and per-table uniqueness

Task 4.5 restates "retain keyword/service semantics and per-table uniqueness,
remove globally forced distinct keyword tuples". That half was already landed by
WP4's 4.1 commit `27a4a773` ("...the globally forced distinct keyword tuples and
the corpus-wide prose distinctness are gone..."). It is verified, not re-done:
`_table_problems` in `world/lore/tests/test_npc_profile_slice_content.py`
enforces uniqueness only inside one table and
`test_two_hosts_may_share_the_same_keyword_vocabulary` asserts two hosts may
legitimately share a label set. 4.5 records the rule in both guides.

## 6. Verification actually executed

| Command | Observed result |
| --- | --- |
| `uv run --locked evennia test --settings test_settings.py --keepdb world.lore.tests.test_npc_editorial_review world.lore.tests.test_npc_profile_slice_content world.lore.tests.test_npc_profile_inventory world.lore.tests.test_dialogue_assembly world.rules.tests.test_npc_roster_validation` | `Ran 59 tests ... OK`, both before and after the post-implementation review fixes |
| `uv run --locked python -m tools.test_data_lint check` | `scanned=1253 flagged=99 universe=1219+38 quantity-pins=10 violations=0` (the new test is flagged once it imports `NPC_PROFILE_REGISTRY`/`PLAYER_PRESET_REGISTRY`, and is exempt by its `contract` registration) |
| `uv run --locked python -m tools.test_data_lint seed --dry-run` vs the committed ledger | contract sets differ only by the pre-existing `world/rules/tests/test_buffs.py` asymmetry (metadata-map Table C); **zero** reason diffs; debt differs only by the known wholesale-regeneration effect (dry-run folds the 322 flagged/seed-debt paths back into `debt`). The hand-edit masked nothing. |
| `uv run --locked python -m tools.contract_gate` | observability `violations=0`, test-data `violations=0`, manifests OK, contracts `Ran 18 tests ... OK`; the gate fails only on traceability, for the two new ids' documented pre-sync `unknown-requirement-id` state. |
| `uv run --locked python -m tools.spec_traceability check` | 81 -> 86 errors: the 8 NPC `dynamic-requirement-id` errors are gone (replaced by 8 `unknown-requirement-id` on the same literal sites) and 5 new `unknown-requirement-id` come from the new test; the only remaining `dynamic-requirement-id` sites are the 5 WP3 bestiary ones of §4. |
| `openspec validate generalize-content-identity-contracts --strict` | `Change 'generalize-content-identity-contracts' is valid` |
| `openspec validate --all --strict` | `315 passed, 3 failed (318 items)` - the three failures are `fog-mane-lynx-resource-skill`, `ridge-burrow-hare-resource-skill`, `rock-echo-goat-resource-skill`, i.e. the unchanged deferred monster proposals; no fourth failure. |
| `openspec validate --specs --strict` | `312 passed, 0 failed (312 items)`, no failure added. `openspec/specs/` is byte-identical to the handover tip (`git diff --stat HEAD -- openspec/` empty), so the count is the handover state, not a 4.5 effect. |
| `git diff --check` | clean |

## 7. Delta-spec deviations

None. 4.5 edited no delta spec, no deferred proposal and no `exploration-*`
change, and touched no requirement statement, so `openspec validate` totals are
unaffected by this package.

## 8. Left to a later package

- **WP7**: literalize the five WP3 bestiary annotation sites of §4; resolve the
  pre-sync `unknown-requirement-id` errors by applying/archiving the delta; run
  the integrated evidence gate.
- **WP6 / WP5**: untouched.

## 9. Independent review dispositions

Two blocking rubber-duck critiques were run over this task, one on the plan and
one on the finished diff. Both were folded in.

- **Plan-stage critique, adopted:** literal decorator arguments (the WP4 defect
  of §4); name the retired-id scan's method and its real buckets; keep the new
  module free of any `world.*` import and any module-level mapping, so
  `tools.test_data_lint`'s universe derivation never treats it as catalog data;
  annotate the fault test as well as the coverage test; carry the ledger rule
  into the test-data guide, not only the author guide. **Rejected:**
  `import_example`'s face is `card`, not `card`/`greeting` - the shipped import
  cards write a `persona` and no greeting field, so the card is their only
  authored surface. **Deferred:** tightening `LEDGER_DATE` beyond
  `^\d{4}-\d{2}-\d{2}$` (a real parse would reject `2026-13-45`, but
  `world/lore/bestiary_documentation.py` uses the identical regex; the two
  checks should move together).
- **Post-implementation critique, adopted:** both blocking findings were
  factual errors in this document's §4 - it had claimed a frozen design
  document under `docs/superpowers/specs/` names a retired id verbatim. That
  citation came from the plan-stage critique and is wrong: a gitignore-off
  grep over the whole worktree matches only the three planning artifacts, and
  no `docs/` file carries any of the six slugs. §4 now states the reproducible
  scan and its actual result. Its two non-blocking gaps are closed too: the
  no-fixture guard now spans every kind's spoken lines, and the wording test
  rewrites a face cell as well as a disposition cell with a per-entry
  changed-line floor. **Deferred:** only the `LEDGER_DATE` rigor noted above.
