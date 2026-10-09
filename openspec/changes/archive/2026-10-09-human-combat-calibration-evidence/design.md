## Context

See proposal.md for motivation. Authority is docs/superpowers/specs/2026-10-08-human-guild-exams-and-monster-balance-design.md, approved commit 39d50b2b, together with the engine design. This slice owns sections 8.4-8.8; 8.1 encounter expectations; 10 real runtime smoke. Existing production seams are focused world/rules/tests calibration module; docs/game/ or docs/development/ balance evidence; approved design evidence references.

## Goals / Non-Goals

All state writes stay in world/rules; residences stay world/maps-owned; lore/skills remain immutable/read-only. No AI writer, compatibility alias, migration, new booking queue, difficulty selector, new F exam, reward/merit change, elf/beastfolk calibration, monster ability, retreat kill credit, combat formula change or unrelated refactor is authorized. The approved 2026-10-08 design supersedes disposable examiners and legacy HP/static ratio assumptions; preserve current simulated HP-to-zero and full pool restoration.
Behavior tests use synthetic data and resolver-backed transitions/precedence/rollback, not wording/source assertions or copies of shipped rows. Authored rows use separate tagged data-contract checks under existing freeze discipline; never expand a freeze list to excuse missing behavior. Any new/moved non-browser module is registered exactly once in .github/evennia-shards.json; new browser class/method is registered exactly once in .github/browser-shards.json.
Obtain canonical IDs with uv run --locked python -m tools.spec_traceability list after delta synchronization, never hand-build IDs. Maintain substantive covers_requirement annotations on discoverable tests; no skipped/empty claims. Every added requirement/scenario in this change has behavior coverage; unchanged requirements keep existing coverage. Remove obsolete tests/contracts/callers at their owning cutover.
Changed persistent boundaries emit named-import world.observability info events with English snake_case names and available exam/host/branch/target/tick/session identifiers; exceptions re-raise, carry exc or existing reasoned exemption. Start/restriction/restore/terminal/hold/release/recovery trace events belong to their owning slice. No direct logging import or observability freeze expansion.

## Decisions

Preserve all approved numeric tables and experiment qualifications reproduced below. The 1554 projected trials are historical conditional evidence, never proof of real shops/gear/accessories/hosts/schedules/recovery. Keep the F valid 224-point creation resolver build and its real plains starting kit; do not generalize it to all novices. Basic_swordplay coefficient 1/SP8 inefficiency and current strongest-affordable fallback policy remain unchanged.
Build a bounded reusable test fixture using real Evennia Room/NPC/Monster, traits, buffs, prerequisite/proficiency initialization, actual shared gear and restriction activation. Use ActionResolver/initiative/run_round with simulation markers everywhere, full pools, no potions/manual regen/clock advance, 200-round cap. Maintain separate metrics for monster zero-HP defeat, retreat, human loss, all-standing, unfinished, rejects and round median. Do not implement combat math in a harness.
Run focused sample seeds 0-3 across ordinary low/mid, stronger mid/party and upper representative probes; historical tables use their documented 0-15/0-7 seeds and remain labeled projected. One representative real-attribute backend parity case records exact seed/state. A compact evidence artifact records build/item/profile IDs, seeds, policy, backend, engine revision and measured stats/outcomes; do not assert the old projected win counts must reproduce if real gear exposes a defect. A mismatch blocks evidence acceptance until diagnosed in its owning predecessor, with no unapproved numbers/formula/policy changes.
Synthetic mechanics tests avoid shipped rows; separate tagged authored integration data checks and recorded runtime smokes cover persistent Hok/Cassandra/Augustine, real kit restriction consumers, valid normal skill lineages and schedule movement. This change adds no species, skill tuning or optimized NPC policy. A-party high-upper 5/8 all-standing and retreat/no-kill-credit caveats remain explicit.

The chosen design reuses existing registries, resolver, service gate, schedule source and transaction/cache conventions. A separate guild scheduler, disposable opponent, projected-only gear, destructive skill rewrite and compatibility shim were rejected because they violate approved identity or authority boundaries.

## Risks / Trade-offs

- Shared files can conflict. Integrate after required predecessors and serialize shared hunks/manifests as listed in the batch matrix.
- Cached handlers can diverge from rolled-back storage. Snapshot both and assert deterministic before/after state where mutation occurs.
- Planned attendance can fail under locks or future state changes. Report planned status and recheck actual start.
- Projected balance does not establish runtime integration. Record only actual exercised evidence in the owning smoke.

## Migration Plan

Apply only after shared-military-equipment, human-monster-balance-data, persistent-guild-exam-lifecycle, guild-exam-schedule-hold are present. Read predecessor delta plus live source before editing. This unreleased project has no save migration or backward aliases. Land source, tests, docs and all caller cutovers as one coherent change. Revert the owned implementation commit to roll back deployment; never delete persistent hosts or manufacture data as repair.

## Verification and Ownership

The finite smoke matrix is E versus each six low variants (6); D solo, three D and C solo versus one ordinary mid representative wood_stalker (3); C solo and two C versus trail_hunter (2); restricted B versus bank_lurker (1); restricted B versus high-lower plus A/S/three-A versus high-upper (4); S and three-A versus calamity-lower (2). This is 18 matchup/policy combinations times seeds 0-3, at most 72 trials and 14400 resolver rounds. One F creation/equipment reference and one E/reef seed-zero backend parity case are separate. Use one focused module world.rules.tests.test_human_combat_calibration; upper probes remain synthetic unshipped objects. Historical full 0-15/0-7 tables remain preserved and are not claimed as this smaller real-kit sample.

One focused calibration test file and bounded smoke command, seeds 0-3 and 200 rounds; one native/SQLite attribute parity case. No full 1554-trial rerun or CI suite. Assertions cover outcome semantics/resources/growth/rejects, not arbitrary fixture echo.

Each scenario in specs/ needs substantive synthetic behavior coverage. Retain exact approved authoring checks separately. Record deterministic snapshots before and after reads/failures and host baseline/ownership before and after exams. Update owning game/development authoring documentation with implemented shapes and observed behavior. Appointment owns both command documents; other slices do not rename commands. Run only final focused checks and the contract gate once all owned implementation edits are complete. Full browser/evidence verification remains CI-owned.

## Approved Numeric and Evidence Reference

The following excerpt is preserved from the approved design. Historical experiment outcomes remain conditional projected evidence unless explicitly replaced by recorded real-runtime measurements.

Exploration executed 1,554 individual trials, including current profiles, candidate refinements, party comparisons, behavior-policy checks, and backend parity checks. Current low/mid comparisons used seeds 0–7; final candidate comparisons used seeds 0–15. Upper-envelope probes used seeds 0–7; full-B and C-support follow-up comparisons used seeds 0–15.

The subprocess used `uv run --locked`, configured SQLite `:memory:` before Django setup, and created real Evennia NPC, Monster, and Room objects. It exercised existing traits, skill and buff handlers, prerequisite initialization, ActionResolver, initiative, costs, upkeep, and `run_round`. Repeated trials used Evennia's native in-memory attribute backend for persistence speed. One E-versus-reef seed-zero comparison matched the SQLite-attribute result exactly. Both produced 54 rounds, 81 human HP, 4 SP, 12 basic-swordplay uses and 42 ordinary attacks.

Gear effects were projected at the equipment-adjustment boundary. E–B profiles used lower input traits/pools and permitted ownership equivalent to the target states, rather than real accessories worn by one unchanged senior. Therefore these results do **not** validate restriction implementation, shops, persistent NPC recovery, or identical effective values across all real cap consumers. Those are implementation acceptance criteria.

The F reference used the real character-creation resolver with a valid 224-point allocation. It allocated 69/69/69 into HP/MP/SP, 4/4/4 into physical attack/agility/defense, and 5 into magic. It produced HP/MP/SP 169/169/169, physical bases 5/5/5, and magic 10. The actual plains-human starting kit was worn, including plain sword, leather armor, and silver hairpin; final physical combat values were 7/5/9. This is one valid novice build, not a universal starting-human profile.

Human attacks followed strongest-first affordable skill selection with lower-skill/ordinary-attack fallback. Full B used a simple policy that heals at or below 40 percent HP when affordable, otherwise prepares concentration and gale-step once, then attacks. It is an exploratory strategy, not an optimized production NPC policy. Purification was owned but not exercised because the sampled monsters supplied no relevant condition.

Trials used full starting pools, no potions, no manually added regeneration or clock advancement, and a 200-round bound. Every action context and the round runner carried the simulation marker to freeze skill practice and prevent unlock drift. All sampled trials terminated and recorded zero rejected actions. Combat math was not reimplemented.

### 8.5 Final low-tier stand-and-fight outcomes

The controlled comparison used ordinary monster attacks without retreat so that a win meant reducing the monster to zero HP. Values below are wins out of 16 and victory-round medians.

| Variant | F wins | F rounds | E wins | E rounds |
|---|---:|---:|---:|---:|
| Grain pecker | 16/16 | 15 | 16/16 | 7 |
| Flock leader | 16/16 | 37 | 16/16 | 15.5 |
| Shore walker | 16/16 | 23 | 16/16 | 8 |
| Reef warden | 12/16 | 76.5 | 16/16 | 20 |
| Burrow maker | 16/16 | 14.5 | 16/16 | 8 |
| Nest guard | 15/16 | 74 | 16/16 | 15.5 |

The previous F shore-walker median was 107 rounds. Ordinary F variants now take about 14.5–23 rounds in this reference. Reef and nest remain stronger E-grade targets, with F losses and long fights; the table must not be summarized as every low-tier monster being safe for a beginner.

### 8.6 Final mid-tier stand-and-fight outcomes

| Ordinary variant | D solo wins | Three D wins / all-standing | Three D rounds | C solo wins | C rounds |
|---|---:|---|---:|---:|---:|
| Cliff stepper | 0/16 | 16/16 / 16/16 | 5 | 16/16 | 15.5 |
| Wood stalker | 3/16 | 16/16 / 16/16 | 5 | 16/16 | 11.5 |
| Bank lurker | 0/16 | 16/16 / 16/16 | 6 | 16/16 | 15.5 |

Their previous C-solo round medians were 51.5, 41, and 93 respectively. Lower endurance produces ordinary mid-tier fights with a clear party-versus-solo progression.

| Stronger variant | C solo wins | Three D wins / all-standing | Two C wins / all-standing | Two C rounds |
|---|---:|---|---|---:|
| Pass warden | 9/16 | 16/16 / 9/16 | 16/16 / 16/16 | 5.5 |
| Trail hunter | 6/16 | 16/16 / 8/16 | 16/16 / 16/16 | 8.5 |
| Bay warden | 5/16 | 14/16 / 5/16 | 16/16 / 16/16 | 11 |

“All-standing” means no human participant reached zero HP in that trial. It is not a claim about permanent companion death. Strong variants are C-support encounters; three D characters are not a safe-clear benchmark. Every restricted B mid-tier matchup recorded 16/16 wins with a 1–2-round median. Full B also recorded 16/16 throughout; its fixed preparation actions added turns to already short fights.

### 8.7 Real monster-policy outcomes

A separate pass used each variant's real behavior identity and `monster_behaviour_policy`. It distinguished actual defeats, monster retreats, human losses, and unfinished fights.

| Variant | Human reference | Monster defeats | Monster retreats | Human losses |
|---|---|---:|---:|---:|
| Grain pecker | E | 6 | 10 | 0 |
| Flock leader | E | 2 | 14 | 0 |
| Shore walker | E | 5 | 11 | 0 |
| Reef warden | E | 1 | 15 | 0 |
| Burrow maker | E | 5 | 11 | 0 |
| Nest guard | E | 3 | 13 | 0 |
| Cliff stepper | C | 5 | 11 | 0 |
| Pass warden | C | 0 | 14 | 2 |
| Wood stalker | C | 7 | 9 | 0 |
| Trail hunter | C | 0 | 11 | 5 |
| Bank lurker | C | 4 | 12 | 0 |
| Bay warden | C | 0 | 11 | 5 |

Every row contains 16 trials with zero unfinished fights and rejected actions. A retreat resolves an encounter without proving a kill, loot award, or hunt-objective completion. This change preserves that distinction and does not alter retreat credit.

### 8.8 Higher-tier probes

| Probe | HP / attack / agility / defense | Restricted B solo | A solo | S solo | Three A |
|---|---|---:|---:|---:|---:|
| High lower | 320 / 28 / 18 / 20 | 8/8 | 8/8 | 8/8 | 8/8 |
| High upper | 700 / 38 / 26 / 28 | 0/8 | 0/8 | 7/8 | 7/8 |
| Calamity lower | 1,200 / 60 / 60 / 60 | 0/8 | 0/8 | 0/8 | 0/8 |
| Calamity upper | 3,000 / 150 / 150 / 150 | 0/8 | 0/8 | 0/8 | 0/8 |

The high-lower restricted-B median was 14 rounds. Full B recorded 16/16 wins with a five-round median against that probe and 0/16 against high upper, despite successfully exercising utility and healing. These are results for the tested policy; they do not prove that every B strategy fails or establish a universal A boundary.

At high upper, the S victory median was 54 rounds. Only five of eight A-party trials finished all-standing. That endpoint is a hazardous upper-high challenge, not a comfortable or guaranteed S solo clear. The calamity probes exceed the tested lone-human and three-A capabilities. None of these four points validates every combination in its authoring envelope.

One existing skill issue remains outside this change. `basic_swordplay` has the same coefficient 1 as free `basic_attack` while spending eight SP. The measurements include that inefficiency. Do not silently change the skill or attack-selection optimization to make the approved balance appear stronger.
