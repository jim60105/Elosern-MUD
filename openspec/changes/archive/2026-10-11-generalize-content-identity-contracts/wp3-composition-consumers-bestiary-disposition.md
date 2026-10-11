# WP3 composition mechanics, consumers and bestiary relationship (tasks 3.1-3.5)

Baseline at spawn: `master` = `9c3c14f7`, worktree tip = `ddaae38f`, clean, `git merge-base HEAD master` =
`9c3c14f7`, branch `feat/generalize-content-identity-contracts`. `os-phase
generalize-content-identity-contracts --require proposed` reported
`change=generalize-content-identity-contracts phase=proposed primary=master
branch=feat/generalize-content-identity-contracts
worktree=/var/home/jim60105/repos/MUD/.worktrees/generalize-content-identity-contracts` (exit 0).

## Commits

| Commit | Task | Content |
| --- | --- | --- |
| `420dde8d` | 3.1 | shared transfer/atomic-action coverage: retargets, control, transfer-limit and no-write probes, absorbed-hit case, real practice-claim rollback with retry |
| `71dfa6b1` | 3.2 | new synthetic timed-effect suite (rider/self routing, lifetime, environment parity) |
| `da5d0fbf` | 3.3 | composition grouping + representative coverage contract, representative-driven smokes, independent flee rulebook read |
| `0458bfe6` | 3.4 | bounded bestiary index, pure parser/checker, prose fixtures removed |
| this commit | 3.5 | indexed editorial ledger + structural check, both author guides, metadata, boxes |

## 3.1 Shared transfer arithmetic, gates and rollback (done)

`world/rules/tests/test_skill_hit_dependencies.py` keeps independent arithmetic
(target MP 3 / drain 10 / full share / caster 20 cost 10 -> victim 0, caster 13),
both either-axis affordability rejections, effects-before-cost ordering at and
around the cap, miss, zero-pool and critical/defeat-crossing vectors, and the
two-species isolated-hit-evidence case. Added: an untouched third control whose
HP/MP must stay identical across the exchange and its payment; an explicit
transfer-limit probe (the MP transfer grants no undeclared HP healing and no
permanent stat base changes); explicit no-write probes on both unaffordable
requests (named `INSUFFICIENT_RESOURCE`, `roll_d100` call count 0, actor and
victim gauges plus `db.skill_proficiency` unchanged); and a new absorbed-hit
case whose committed HP loss is the live rulebook floor (`COMBAT_YAML
["damage"]["floor"]`) while the rider still transfers its full fixed amount
exactly once, so the hit-qualified path can never be confused with the miss one.

`world/rules/tests/test_effect_audiences/test_effect_routing_pipeline_rollback_and_composite_effects.py`
keeps its real post-write rollback and now injects a genuine practice claim
before the late failure, so the restore assertion observes progression state
instead of an untouched attribute, and re-issues the identical request
afterwards: the retry succeeds, lands one authored settlement and leaves the
day's single claim, proving the failed attempt neither leaked state nor
double-counted practice.

Observed: `13 tests OK` for those two modules.

## 3.2 Distinct synthetic audiences, lifetime and environment (done)

New `world/rules/tests/test_monster_timed_effect_mechanisms.py` (synthetic `t_`
skills and buffs from the shared kit, no shipped identity):

- enemy hit-rider: a miss grants nothing anywhere; a hit grants exactly one
  instance to the hit enemy; a hit whose committed loss is the damage floor
  (defense swallows the attack) still qualifies; caster, ally and untargeted foe
  are controls; a second hit refreshes the single contribution.
- hit-independent self-guard: a valid attempt grants the caster even on a miss
  and reaches neither the targeted enemy nor the ally; an unaffordable request
  is rejected with `INSUFFICIENT_RESOURCE` and no roll/gauge/buff; an empty
  target list is `TARGET_SPEC_MISMATCH` and an absent target is
  `TARGET_NOT_PRESENT`, both granting nothing.
- lifetime: an aged instance refreshes to one same-key contribution at its full
  declared duration; crossing the refreshed expiry removes it with no residual
  modifier, marker or HP change.
- environment/narrative: two declared variants differing only in narrative
  strings produce identical results through real construction and resolution,
  and forged environment facts on the action context leave the deltas unchanged.

Observed: `4 tests OK`.

## 3.3 Grouped kits, representatives and per-group consumer evidence (done)

Signature (chosen and documented in `world/rules/tests/test_monster_composition_coverage.py`): per variant, the
authored order of `(slot, effect family, declared audience, hit-dependency
occurrence index)` for every declared active/passive kit skill, or `None` when
the row declares no kit. The behaviour binding is deliberately **not** part of
the signature: the requirement names effect/hit-dependency/audience only, and a
binding-keyed signature would manufacture a new group (and a new demanded
smoke) for a species that merely reuses a composition under another archetype.

Discovered groups and stable-key-ordered representatives: transfer/drain ->
`bank_lurker`; enemy hit-rider -> `flock_leader`; hit-independent self-guard ->
`reef_warden`. Each representative is committed as real evidence by the smoke
that declares it (`REPRESENTATIVE_VARIANT`), and the coverage contract asserts
declared set == derived representative set (naming every uncovered group),
asserts each smoke's `construct_species_individual` call takes the declaration
rather than a copied key, and rejects any other shipped variant key literal in
those modules. Discovery scans every `test_*.py` under `world/rules/tests/` for
the declaration - never a filename pattern or a module list - so a new group
cannot hide. An arbitrary-key synthetic case proves a reused composition joins
the existing group under the same signature.

Representatives were re-picked by that derivation: the crab smoke moved from
`shore_walker` to `reef_warden`, and the sparrow smoke from `grain_pecker` to
`flock_leader` (sorted-key minima), both now derived from the row rather than
copied. Each smoke also gained, per group: ordinary fallback on its exhausted
payable axis (MP for transfer and self-guard, SP for the rider, so both axes are
real evidence), the inclusive flee edge computed from the representative's own
declared threshold (`floor(max_hp * threshold)` -> `FLEE_SKILL_KEY`, one above ->
its kit skill), and a late-target rejection (`TARGET_DEAD`) that pays nothing.

`world/rules/tests/test_monster_flee_decision.py` replaces the mirrored
threshold table (`{"instinctive": 0.35, ...}`, a shipped balance value copied
into an expectation) with an independent re-parse of
`world/rules/rulebook/monster_behaviour.yaml` compared against
`BEHAVIOUR_PROFILES`, plus scalar shape checks and the tier-default resolution.
No literal threshold remains; the pre-existing flee-policy requirement id stays
on the test and the generic policy id is added.

Observed: `7 tests OK` (coverage + three smokes), `38 tests OK` for the wider
C3 batch including `test_monster_individual` and the flee module.

## 3.4 Bestiary index and pure checker (done)

`docs/lore/bestiary.md` current sections carry one `` ```bestiary `` block each
(species key, parent species key, default variant, every owned variant with its
kit-backed status, the documented public fields, species status) and the
`<!-- bestiary-current-end -->` marker separates the historical appendices.

New pure `world/lore/bestiary_documentation.py`: `parse_bestiary_document`
(no file, DB or prose access) and `check_bestiary_documentation`, which compares the
parsed structure with registry rows and their published projections - key sets
both ways, uniqueness, parent ownership, default-variant ordinary ownership,
public-field references whose sole authority is the projection key set,
required narrative-field coverage, non-empty bodies, extra blocks, historical
sections claiming coverage, and a status that must follow the row's declared
kit. Every problem names the key and the relationship.

`world/lore/tests/test_monster_species_content.py` drops
`APPROVED_ABILITY_LIMITS`, `APPROVED_CONTACT_CLAUSES`, `_normalised`,
`_sentences` and both prose-comparison tests; the narrative half now asserts
presence and public/private separation only. New
`world/lore/tests/test_bestiary_documentation.py` drives the live document
(coverage both ways) plus every named fault - missing, duplicate, orphaned,
mis-parented, field-incomplete, private-field, status-mismatched, unkeyed
current section, duplicated variant, extra block, empty body - through the same
parser with synthetic rows, proves a wording-only reword of the shipped
publication still passes, and proves complete-looking blocks moved behind the
historical marker satisfy no current coverage.

Observed: `12 tests OK` (new module), `98 tests OK` for the lore monster batch.

## 3.5 Editorial ledger, guides, metadata and retargets (done)

New `docs/development/bestiary-editorial-review.md`: one dated entry per shipped
species key with a disposition for each reviewed face (ecology narrative,
ability limits, historic vs current) and an overall disposition, plus an
explicit statement of what the record can and cannot prove. The structural check
(`parse_editorial_ledger` + `check_editorial_ledger` in the same pure module)
requires exactly one fully dispositioned, correctly dated entry per shipped key
and rejects orphan entries; its faults are asserted in the documentation
contract. Both monster author guides were updated: `docs/lore/bestiary.md`
(index semantics, historical boundary, ledger pointer) and
`docs/lore/monster-creation-guidelines.md` (new "Documenting a species"
section), and the ledger is registered in the docsify sidebar.

Retired monster ids and their new carriers (verified by a whole-tree scan: 0
stale removed monster-id sites remain in any tracked `.py`):

| Retired id | Re-attached to | Site |
| --- | --- | --- |
| `monster-resource-abilities::successful-bite-drains-mp-and-recovers-only-actual-removal` | `hit-qualified-transfers-credit-actual-removal-once` | transfer oracle, absorbed-hit case, critical/defeat case, two-species case |
| `monster-resource-abilities::affordability-precedes-effects-and-recovery-precedes-costs` | `monster-effects-and-payments-share-the-ordinary-atomic-action` | transfer oracle |
| `monster-resource-abilities::穗鳴雀/潮燈蟹-payment-and-atomicity-retain-the-shared-transaction` | `monster-effects-and-payments-share-the-ordinary-atomic-action` | composite rollback control |
| `monster-resource-abilities::production-crocodile-delivery-includes-real-combat-and-persistence-evidence` | `delivered-monster-compositions-retain-representative-consumer-evidence` + `authored-monster-kits-use-shared-policy-selection-and-fallback` | crocodile representative smoke |
| `monster-action-policy::authored-crocodile-behavior-uses-the-existing-first-owned-strategy` | `authored-monster-kits-use-shared-policy-selection-and-fallback` | crocodile smoke, flee thresholds/tier defaults |
| `monster-action-policy::穗鳴雀/潮燈蟹-contact-kit-uses-existing-first-owned-policy-and-fallback` | same | sparrow and crab representative smokes |
| `monster-resource-abilities::穗鳴雀/潮燈蟹-timed-modifier-follows-its-authored-recipient-and-lifetime` | `timed-monster-effects-follow-declared-recipients-and-lifetime` | sparrow and crab representative smokes |
| `monster-resource-abilities::{crocodile-ecology-documents-implemented-limits,穗鳴雀/潮燈蟹-public-ecology-reflects-the-completed-contact-kit}` (WP2 had moved these to the narrative id) | `bestiary-documentation-covers-keyed-public-content-relationships` | new documentation contract (the prose tests that carried them were removed) |

Same-shape changes removed, with their replacement: the two approved-prose
constant tables (8 entries) and the `_normalised`/`_sentences` helpers -> the
keyed relationship checker plus presence/separation checks; the mirrored flee
threshold table (6 entries) -> an independent rulebook re-parse; the
`construct_species_individual("<species>", "<variant>")` literals and reload
key literals in the three smokes -> declarations derived from the live rows.

Metadata: reason strings aligned in the file docstring, the seed and the ledger
for the three representative smokes; new contract registrations for
`world/rules/tests/test_monster_composition_coverage.py` and
`world/lore/tests/test_bestiary_documentation.py`; the timed-effect suite is
gate-clean and deliberately registered nowhere. The ledger was edited
surgically (never regenerated), so the recorded `test_buffs.py`
ledger/seed asymmetry is preserved. Observed: `test-data-lint ... violations=0`.

## Deviations from WP1's plan (each deliberate)

1. `metadata-map.md` aligned `world/lore/tests/test_monster_species_content.py`
   to a reason naming the bestiary relationship contract. Because the keyed
   relationship moved to its own contract module, that file's reason is aligned
   to `registry-derived monster identity, profile/kit coverage and public
   narrative contract` instead, in the same three places.
2. The composition signature excludes the behaviour binding (rationale above),
   and the representative choice is enforced from the derivation rather than
   WP1's per-file assumption; this re-picked two of the three representatives.
3. The new contract modules needed seed/ledger registrations WP1's map could not
   list (they did not exist); the synthetic timed-effect suite needed none, as
   the gate confirms.
4. The three representative smokes keep their WP1 filenames - renaming them
   would churn the ledger and shard manifests for no contract gain - but their
   content is now derivation-driven, and their reasons describe representative
   compositions rather than species.

## Observed checks (this package)

| Command | Result |
| --- | --- |
| `uv run --locked python -m tools.test_data_lint check` | `scanned=1252 flagged=98 violations=0` |
| focused Evennia labels for every touched module | all OK (13, 4, 7, 38, 98, 12 tests) |
| whole-tree scan for the 22 removed monster ids | `stale removed monster-id sites: 0` |
| `uv run --locked python -m tools.spec_traceability check` | reports the pre-sync `unknown-requirement-id` errors for the effective ids this package annotates (expected until the delta specs are synced at archive); WP7 owns the clean end state |

## Pre-existing failure, not caused by WP3

`tests.test_command_docs.CommandDocsContractTests.test_syntax_and_context_match_manifest`
fails on the `guild exam` context string (`公會（需當地考核官）` in the curated
manifest vs `公會（需在所屬分部的公會櫃台前，且已註冊為冒險者）` in
`docs/game/command-reference.md`). No WP3 commit touches `tests/test_command_docs.py`
or `docs/game/`, so both inputs are byte-identical to the branch tip at spawn and
the failure predates this package. Reported, not repaired: it is outside WP3's
package and repairing it would edit a foreign file.

## Left for later packages

- WP4-WP7 per `design.md`; WP7 owns the integrated traceability/metadata
  acceptance and the zero-stale-id conclusion.
- The three deferred monster proposals keep their broken MODIFIED targets and
  old-shaped ADDED blocks as recorded obligations (D1); their owners re-author
  them against the then-current specs.
- The editorial-ledger pattern introduced here is the precedent WP4's NPC ledger
  should follow (indexed by actual source identity, structurally checked,
  never a prose fixture).

## WP3 post-implementation review, every finding and disposition

One blocking whole-diff review ran over the five WP3 commits with the assignment,
the requirement scenarios, the constraints and my reported evidence, and read the
worktree files. Its findings and dispositions:

| Id | Finding | Disposition |
| --- | --- | --- |
| B1 | The representative-evidence link was structural only: a module could declare a representative, satisfy every wiring rule and still carry an empty or skipped test, contributing no evidence. | **Adopted.** The AST pass now also requires a non-skipped `test_*` function whose body resolves an action (`resolve`/`revalidate_submission`), so a declaration without committed behaviour fails. |
| B2 | The inclusive flee edge was located as `int(max_hp * threshold)`, a multiply-and-floor guess whose correctness against the engine's binary-float `stored / maximum <= threshold` comparison is an IEEE-rounding coincidence that a balance retune can break in either direction. | **Adopted.** The boundary is now located by `world/rules/tests/combat_fixtures.py::flee_edge`, which applies the engine's own comparison over candidate HP, and the smokes assert the outgoing side only while a striking band exists. The late-target gate was moved ahead of the flee probe and now restores the victim's HP so both probes select against a living enemy. Disposition wording updated: the boundary is *derived*, not floored arithmetic. |
| N1 | The composition signature collapses the gauge axis (`gauge_transfer:mp:...` and `:sp:...` group identically), so a future SP-draining kit would inherit the MP group's evidence. | **Recorded as a deliberate limitation.** The requirement names effect kind, hit-dependency and audience only; adding element or gauge detail would split same-shape kits (the duplication the design forbids). `effect_family` is the documented one-line extension point if the design ever wants paid-axis diversity as a grouping axis. |
| N2 | `parent-species` enforcement is degenerate (any non-self value is rejected) and the guide/advertised relationship implied possible nesting. | **Adopted as wording.** The registry has no nested species, so the field states the owning species explicitly rather than inferring it from section adjacency; the module comment and the author guide now say exactly that. |
| N3 | The task-3.4 fault list includes a popped required block key, but no fault test asserted it. | **Adopted.** `test_a_missing_block_key_is_named` pops `parent-species` and asserts the named `metadata block is missing ['parent-species']` problem. |
| N4 | The timed-effect rider test's docstring promised the committed loss is the damage floor while asserting only `assertLess`. | **Adopted.** It now asserts the exact committed delta read from the live rulebook (`int(COMBAT_YAML["damage"]["floor"])`), matching the 3.1 oracle. |
| N5 | Watch-item: the retired `crocodile-ecology-documents-implemented-limits` scenario now survives only as the editorial ledger's unjudged prose cell, because the new carrier proves keyed relationships. | **Accepted as the requirement-faithful carrier** (the generic requirement is about keyed public-content relationships) and **recorded here for WP7**: if the zero-carrier audit counts scenario-level coverage, this row needs a note. |

The reviewer confirmed no self-fulfilling oracle in the 3.1 additions, no shipped
balance value mirrored as an expectation (the flee table is gone and the
thresholds are read live), no species allowlist or shape-count pin in the
grouping, correct shard/seed/ledger handling (including that manifest
registration is not contract registration), and that the ledger is a genuine
indexed record. Observed after folding in the findings: `65 tests OK` across the
nine affected modules and `test-data-lint ... violations=0`.
