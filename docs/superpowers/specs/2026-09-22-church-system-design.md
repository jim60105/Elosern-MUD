# Church System Design (Sub-project 1: Ordination Pipeline)

Date: 2026-09-22
Status: approved by the project owner in a brainstorming session (sections 1-6,
final decisions below)
Change split: see §8 — the 24-row catalogue alone exceeds the one-workday
convention, so implementation ships as two OpenSpec changes
(`implement-church-core`: ledger + enrollment + pray + offering + redemption
engine + Series A/B/D catalogue; `implement-church-order-catalogue`: Series
C/E rows). Sub-projects 2 (temple service economy) and 3 (prayer/confession/
donation observance commands) are deliberately out of scope and get their own
design documents later.

## 1. Problem and current state

The Light Church exists in lore as the world's dominant soft power
(`docs/lore/overview.md` 宗教信仰, `docs/lore/settlement-locations.md`
§神殿／聖所) and in the engine only as: one generic shop counter
(`ShopDefinition` derived from the place registry), a generic `talk` venue,
and the combat-side clergy passives (`pain_to_pleasure`, `priestly_grace`,
`rapture_renewal` in `world/skills/registry/data_utility_passives.py`) plus
the saintess vessel (`openspec/specs/saintess-vessel/spec.md`). There is no
in-game path for a normal character to become a nun: the three clergy
passives are PASSIVE-kind qualifier rows, which by design cannot be earned
through practice, cross-lineage unlock, or conferral — today they reach
characters only through presets/imports at creation. `docs/lore/skill-trees/
light.md` promises 「劇情／聖職敘階授予」 but no such channel exists. The
church's three public counters (worship+heal, sexual ministry, toy shop) are
one shared generic shop plus venue prose.

grep confirms: no church/temple/clergy mechanics under `world/quests/`,
`world/maps/`, or `commands/`.

## 2. Goals and hard constraints

- **The church becomes an institution**: enrollment, a merit economy earned
  by behaviour, an ordination (skill-redemption) ladder, and two tank-making
  combat skills that make the clergy loop ("舍棄防禦") actually tankable.
- **No quest channel.** The owner explicitly rejected quest-reward grants to
  avoid duplicating the guild system's identity. Ordination is earned purely
  by behaviour: prayer (time cost), sexual offering, and the erotic
  practice itself (climax accrual).
- **No affinity gate.** Offering acceptance is judged by the NPC's arousal
  ordinal, never by affinity — the church sells bodies as ministry, not
  friendship. (Affinity stays what it is elsewhere.)
- **Offline determinism.** `pray`, offering, redemption, and both combat
  skills are fully playable with every LLM service dead. AI is a prose
  overlay only (as with the guild: registration behind a command, not a
  dialogue-model call).
- **Single-writer boundary.** All writes live in `world/rules/church.py`
  (new); lore stays frozen-dataclass registries; commands stay thin.
- **All-or-nothing transactions.** Enrollment, offering settlement, and
  redemption are each one transaction; rollback leaves ledger and skills
  byte-identical.
- **Integer copper only** (existing currency rule); merit is a separate,
  non-transferable, non-spendable-anywhere-else counter.
- **Passive-no-negativity iron rule (owner decision).** No PASSIVE catalogue
  row may carry any effect that is negative relative to baseline (no price
  increases, no defense reductions as a downside): there is no "unequip a
  passive" concept, so a passive downside would be a permanent punishment.
  Every trade-off must live in the redemption *price*, never in the effect.
  Enforced by a loader polarity check and a data-contract test, not intent.
- **The saintess vessel never enters the catalogue.** It is a blood office
  pinned to preset activation by the saintess-vessel spec; a test pins its
  permanent absence from the redemption catalogue.

## 3. Rejected alternatives (recorded for the archive)

- **Quest-reward skill grants** (extend `QuestReward`): rejected by owner —
  overlaps the guild's identity.
- **Merit via a guild-style merit currency + board**: rejected — same
  overlap concern.
- **Global Script ledger (GeneratedQuestStore pattern)**: rejected — merit is
  character state; it must persist, serialize, and transact with the
  character, so it lives on `db.church`.
- **Hardcoded accrual at settlement sites**: rejected — scatters tuning
  across Python and fragments the rulebook surface; accrual rides the
  rulebook side-reaction pattern like `pain_to_pleasure` rides it for
  pleasure.
- **LLM-dialogue-driven church actions**: rejected — violates offline
  playability.
- **Threat/aggro table**: explicitly NOT built. The engine has no threat
  value (`monster_behaviour_policy` picks `lowest_hp` /
  `highest_effective_power` with a seeded tie-break); the owner wants a
  target-preference override, not a threat system.

## 4. Data model

### 4.1 Character ledger

`db.church` — created lazily on first enrollment transaction:

- `merit: int` — cumulative grace points (恩寵). Only accrual rows add; only
  redemption subtracts.
- `enrolled_tick: int` — world-clock tick of enrollment.
- `redeemed: [str, ...]` — redeemed catalogue keys (one-shot each).
- `daily: {"day": int, "pray": int}` — per-day counters, reset on clock-day
  change (mirrors the `climax_today` pattern).

Merit is deliberately NOT currency: not tradeable, not spendable on
anything except the redemption catalogue. Copper from offerings flows into
the normal integer-copper wallet.

### 4.2 Lore catalogues (frozen dataclasses, `world/lore/church/`)

- `OFFERING_CATALOG` — rows
  `{key, act_key, merit, copper, min_lineage?}`. `act_key` projects from the
  sexual-act catalogue: an offering row is selectable iff its `act_key` is
  currently owned through the existing counter-gated unlock system
  (solo/partner/shame lines). Advanced rows reference the church-only Series
  D acts (§5.5) — same rows serve both catalogues by key, zero duplication.
- `REDEEM_CATALOG` — ≥20 rows (§5.6): `{skill_key, merit_price, tier,
  prereq_keys (catalogue-internal only), polarity}`. Never references lineage
  prerequisite machinery; catalogue-internal prereqs are a plain list of
  other catalogue keys.

### 4.3 Rulebook (`world/rules/rulebook/church.yaml`)

Registered through the same `load_rules` loader family; one-row-one-test
correspondence gate applies like `combat_modifiers.yaml`:

- `accrual` rows: `pray_completed` (+X, daily cap), `offering_accepted`
  (+X per row via the offering catalogue), `climax_while_enrolled` (+X,
  small; gated on enrollment — ordinary climaxes of the unenrolled stay
  byte-identical).
- `acceptance` rows: NPC arousal ordinal 0..4 → accept percent. Baseline
  shape (owner): ordinal 0 = 50%, strictly monotonic to 100% at 高度/極限;
  the loader rejects non-monotonic rows. Exact intermediates are tuning and
  ship in the change tasks.
- `pray` rows: duration seconds, merit per pray, daily cap.
- `offering` rows: copper payout band (per-offering row overrides),
  enrollment requirement.

## 5. Mechanics

### 5.1 Enrollment (owner decision: guild-style dialogue, deterministic core)

Modeled byte-shape-wise on guild registration (`commands/guild.py`):

1. New `ChurchHost` typeclass component (sibling of `GuildStaff`), authored
   on the two registered clergy NPCs (艾莉安娜·寒水 high celebrant,
   羅海西亞·芬威克 sanctuary steward).
2. Command `church join` (aliases 入教／洗禮): resolves a local church host
   (`resolve_local_service_host` pattern) → schedule gate
   (`interaction_reason(host, "service_church")`) → deterministic
   `world/rules/church.py::enroll(caller, host)`.
3. `enroll` creates the ledger, stamps `enrolled_tick`, and emits
   `church_enrolled` via `transaction.on_commit` (facade `log_info`).
   Re-enrollment is a stable rejection ("你已屬光明教會").

`pray` requires an existing ledger (the unenrolled are told to speak with
the celebrant). Church venues: places whose authored kwargs carry a `church`
flag (derived set in the lore package, same pattern as `shop_key`).

### 5.2 Prayer (`church pray`)

Thin command → `church.py::pray_step(char)`: venue check (church-flag place)
→ daily-cap check → advance the world clock by the rulebook duration (the
prayer *is* the time cost; shares the existing non-combat clock source) →
accrual row adds merit → commit → `church_pray` info event. Deterministic,
no rolls.

### 5.3 Sexual offering (`church offer <npc> [row_key]`)

Explicit-selection model (owner decision): normal partnered sex is untouched
and never auto-counts.

1. Gate: enrolled. Not venue-bound (owner: ministry travels with the sister).
2. Row menu = `OFFERING_CATALOG` rows whose `act_key` the player currently
   owns (projection over the existing unlock counters — no new unlock
   system).
3. Acceptance: read the NPC's arousal ordinal (`entity.sexual.arousal`,
   already fully implemented for NPCs/monsters) → `acceptance` row →
   `roll_d100` through the existing injected-dice gate. Decline has no
   penalty and no cooldown (the arousal curve itself moves with the clock).
4. Accept: execute the act through the existing action-resolution pipeline
   (all pleasure/shame/exposure/counter effects run their normal rails on
   both bodies), then in the same transaction add merit (row) + copper (row
   payout band) → commit → `church_offering_accepted` event.
5. Decline: `church_offering_declined` event, no writes.
6. Presentation hint only: an NPC at high arousal, when addressed, is
   prompted in flavour text to propose receiving ministry (no mechanical
   force). Sanctuary NPCs are authored with a raised initial arousal
   (small new authoring kwarg on NPC spawn data; the runtime sexual state
   already exists).

### 5.4 Climax accrual

A `climax_while_enrolled` accrual row rides the same side-reaction rail as
`state_reactions.yaml` rows: entering 進行中 while enrolled adds a small
merit. The erotic practice *is* devotion. Unenrolled entities: byte-
identical behaviour (the row's enrollment condition fails closed).

### 5.5 Redemption catalogue composition (24 rows, ≥20 required)

All new `SKILL_REGISTRY` rows; none in any lineage tree; acquisition path is
only this pipeline. The redemption write path is the sanctioned granted-passive
channel (same shape as preset activation's `lineage_ownership_closure`
write); the practice/unlock/conferral PASSIVE guards stay untouched and
theirs tests stay green — the pipeline is the channel, not a bypass.

- **Series A — clergy qualifier passives (4):** `pain_to_pleasure`,
  `priestly_grace`, `rapture_renewal` (first-time catalogue entry: this is
  the 「聖職敘階授予」 channel itself), `vow_of_service` (new: offering
  copper +25% and offering/climax merit +10%, ledger multipliers only,
  pure-positive).
- **Series B — rite actives (8):** `rite_heal_light` (weak heal rail),
  `rite_cleanse` (remove one negative buff), `rite_calm` (target pleasure
  band pull down one ordinal, non-stimulus policy), `rite_bless_water`
  (short positive buff), `rite_sanctify_ground` (room-ground light buff,
  enemy-side debuff authored as a buff row — an active effect, allowed),
  `rite_absolution` (long-cooldown target reset toward band floor + negative
  cleanse, non-stimulus policy), `rite_lamb_mark` (§5.7),
  `rite_martyrdom_vow` (§5.8).
- **Series C — discipline passives (5, pure-positive only):**
  `poverty_vow` (offering copper income and pray merit up — the original
  "shop prices rise" downside was removed per the iron rule),
  `obedience` (merit doubled while under a domination/submission status),
  `chastity_discipline` (pray merit +), `temple_endurance` (mitigates the
  *existing* high-arousal defense penalty by 25% — mitigation of an
  existing penalty is positive relative to baseline, allowed),
  `public_devotion` (merit from acts performed in public venues +).
- **Series D — sexual-ministry actives (4):** `rite_holy_kiss` (partner
  pleasure push + ally HOT), `rite_milk_blessing` (light lactation rail),
  `rite_confession_bed` (post-climax merit credit to both parties),
  `rite_anointing_touch` (partner wetness/arousal push). These rows double
  as advanced `OFFERING_CATALOG` rows (§4.2).
- **Series E — utility (3):** `rite_martial_blessing` (pre-fight single-stat
  buff, clock-cooled), `rite_shelter` (sanctuary rest bonus ledger flag),
  `rite_morning_devotion` (pray daily cap +1 — feeds the core loop).

Price bands (tuning placeholders; the change tasks set finals): entry
300-600, mid 1200-2500, high 4000-8000. Catalogue-internal prereq chain on
the Series D high rows only.

### 5.6 Redemption (`church redeem [list|<key>]`)

`redeem list` prints catalogue + merit + redeemed marks. `redeem <key>`:
validate (exists ∧ not redeemed ∧ merit sufficient ∧ catalogue prereqs met)
→ subtract merit → write skill (PASSIVE rows write `db.skills.passive`;
ACTIVE rows `db.skills.active`) → append `redeemed` → commit →
`church_skill_redeemed`. Any failure leaves everything untouched (one
transaction). No repeat redemption. `saintess_vessel` absence is pinned by
test.

### 5.7 `rite_lamb_mark` 代贖羔印 — target-preference override

Cast on self → applies the `lamb_seal` combat buff. **Removal (owner
decision): after the bearer's second climax the seal lifts.** Mechanism: a
new small buff-declaration field `charges: int` — each transition of the
bearer's climax phase into 進行中 consumes one charge; at zero the buff is
removed. This is the one new buff primitive in this design, declared
explicitly and tested in isolation; its justification: charge-on-event
counters exist nowhere else, and the alternative (rule rows that remove
buffs conditionally) cannot count.

Behaviour rail: in `monster_behaviour_policy`, **before** target-strategy
evaluation, if any living enemy carries `lamb_seal`, single-target
candidates narrow to seal-bearers (multi-seal: canonical order — player
first, then ascending pk). No seal present → every decision byte-identical
to today. This is preference, not threat: no accumulation, no decay, no
transfer, ends with the fight. AREA skills are unaffected (they already hit
everyone); positional markers are an orthogonal exclusion, never
substituted by the seal.

Tank math the seal protects: sealed bearer is hit → `pain_to_pleasure`
converts HP loss to arousal → each climax = `rapture_renewal` self-heal 50%
max HP + a 0-action turn (existing lock) → second climax consumes the seal
→ recast. Two deliberate self-heal windows per cast, then the party is
exposed again. The SP cost and action lock of the recast are the existing
taxes.

### 5.8 `rite_martyrdom_vow` 殉者之誓 — defeat-aftermath pool filter

Cast during the fight → stamps `martyr_key` (with the durable session id) on
the combat session record. At defeat settlement, `_victim_pool` gains one
filter: if this session's stamp matches a non-fled pool member, the pool
collapses to `[her]`; the existing single-member short-circuit then returns
her with zero target rolls (resist contests keep their normal draws).
Victory consumes the stamp. Edge rules: marker died before the wipe →
normal pool; marker fled → filter finds no eligible martyr → normal pool
(fleeing already removes her from the pool); multiple markers → first by
canonical order. Stale stamps (session id mismatch) can never fire.
Rollback-retry determinism holds: the stamp is durable record state, the
draws are state-derived as today.

## 6. Component boundaries, error handling, observability

| Component | Duty | Depends on |
| --- | --- | --- |
| `world/lore/church/` | frozen `OFFERING_CATALOG`, `REDEEM_CATALOG`, church-place derivation | place registry, skill/act registries |
| `world/rules/church.py` | sole writer: `enroll`, `pray_step`, `offer_*`, `redeem`, ledger reads | rulebook loader, clock, currency, sexual pipeline, skills storage |
| `world/rules/rulebook/church.yaml` | every tunable number | rulebook schema registration |
| `commands/church.py` | `church join/pray/offer/redeem/merit` thin commands | `world/rules/church.py` |
| `world/rules/monster_behaviour.py` | lamb-seal narrowing (§5.7) | buff store |
| `world/rules/defeat_aftermath/violation.py` | martyr pool filter (§5.8) | session record |
| `world/ai/` | zero participation | — |

Error handling: stable rejection messages for every failure mode (no host,
off-duty, not enrolled, outside venue, daily cap, row not unlocked, NPC
declined, insufficient merit, repeat redemption); all state writes inside
`transaction.atomic()`; events only via `world.observability` facade with
context dicts (`char`, `npc`, `row`, `tick`): `church_enrolled`,
`church_pray`, `church_offering_accepted`, `church_offering_declined`,
`church_skill_redeemed`.

## 7. Testing and docs contract

- `church.yaml` one-row-one-test correspondence gate (same audit as
  `combat_modifiers.yaml`).
- Acceptance-curve test: injected `roll_d100`, exhaustive ordinal ×
  boundary-die matrix; asserts ordinal-0 = 50% band, monotonicity,
  top-ordinal = 100%.
- Transaction rollback tests: mid-redemption failure leaves ledger and
  skills untouched; declined offering writes nothing.
- Byte-identical baselines: unenrolled climax accrual; no-seal monster
  decisions; no-martyr violation pool.
- Iron-rule gate: loader rejects negative-polarity passive rows; data
  contract test over shipped rows asserts every church PASSIVE's rule rows
  are positive polarity only.
- Negative-set test: `saintess_vessel` ∉ catalogue, ever.
- New test modules registered in exactly one `.github/evennia-shards.json`
  shard; `covers_requirement` literal IDs on requirement tests; data-
  contract-tagged modules registered in the test-data ledger files.
- Player command surface (`church join/pray/offer/redeem/merit`) updates
  `docs/game/commands.md` + `docs/game/command-reference.md` in the same
  change; `tests/test_command_docs.py` green.
- Lore status tags: `docs/lore/settlement-locations.md` §神殿／聖所 〔提案〕
  →〔已實作〕 for the ministry counter in the landing change.

## 8. Change split

- `implement-church-core`: ledger + rulebook + enrollment + pray + offering
  + redemption engine + Series A/B/D rows (16 rows incl. lamb mark, martyr
  vow, charge-primitive) + tests + docs trio.
- `implement-church-order-catalogue`: Series C/E rows (8 pure-positive
  passives + utility) + their rule rows + tests.

Sub-project 2 (temple service economy: paid heal/purify services, donation
economy) and sub-project 3 (confession and the wider observance command set)
get their own designs; the merit ledger and church-place flag are designed
here so they can build on them without re-cutting the surface.
