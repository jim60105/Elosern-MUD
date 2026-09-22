# Church System Design (Sub-project 1: Ordination Pipeline)

Date: 2026-09-22
Status: approved by the project owner in a brainstorming session (sections 1-6,
final decisions below)
Amended 2026-09-22 twice (owner, post-review): (1) subrace-gated saintess
grant at enrollment (vessel removed from the preset), clergy title group
behind a new count predicate family, and the saintess-vessel spec
amendments they carry (sections 5.1/5.9 and 9); (2) the office has no
uniqueness — any female royal who enrolls becomes the saintess — and the
preset persona drops all religious narrative (no 聖女繼承人 wording;
pre-enrollment she is simply 王女).
Change split: see §8 — the 24-row catalogue alone exceeds the one-workday
convention, and the owner additionally caps every change at one engineer-day
(eight hours), so implementation ships as six OpenSpec changes: the
28-task `implement-church-core` proposal was superseded by the re-cut into
`implement-church-foundation`, `-enrollment`, `-accrual`, `-redemption`, and
`-combat-ministry`, alongside the existing `implement-church-order-catalogue`
(Series C/E rows + title ladder). Sub-projects 2 (temple service economy) and
3 (prayer/confession/donation observance commands) are deliberately out of
scope and get their own design documents later.

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

### 5.1 Enrollment (owner decision: guild-style dialogue, deterministic core;
amended: subrace-gated office grant)

Modeled byte-shape-wise on guild registration (`commands/guild.py`):

1. New `ChurchHost` typeclass component (sibling of `GuildStaff`), authored
   on the one registered clergy NPC (艾莉安娜·寒水 high celebrant). Owner
   decision: the sanctum steward (羅海西亞·芬威克) is a plain merchant who
   only sells the sanctum's wares; ministry — enrollment and service — is the
   celebrant's office alone (nuns join the roster in a later sub-project).
2. Command `church join` (aliases 入教／洗禮): resolves a local church host
   (`resolve_local_service_host` pattern) → schedule gate
   (`interaction_reason(host, "service_church")`) → deterministic
   `world/rules/church.py::enroll(caller, host)`.
3. `enroll` creates the ledger, stamps `enrolled_tick`, and emits
   `church_enrolled` via `transaction.on_commit` (facade `log_info`).
   Re-enrollment is a stable rejection ("你已屬光明教會").
4. **Subrace/sex branch (owner decision, amendments):** an enroller whose
   subrace is `human_royal` **and whose sex is female** is additionally granted `saintess_vessel` through the
   canonical granted-passive write path inside the same enrollment
   transaction, emitting the existing `saintess_vessel_granted` event. Every
   other enroller becomes a sister (nun) with the plain ledger — no skill is
   granted at enrollment for anyone else; the clergy passives stay
   redemption purchases. The vessel is deliberately NOT a redemption
   catalogue row: it is a blood office the church recognizes at enrollment,
   never purchasable. Consequences, all recorded: trickle/decay-floor/
   ceremonial reads arm only from ownership, so the princess becomes
   functionally saintess exactly at her church visit. **No office
   uniqueness (owner decision):** every female royal who enrolls becomes a
   saintess — there is no global office state, and the lore framing of a
   once-per-generation donated princess is retired, not merely untracked:
   the lore documents that assert it (`docs/lore/overview.md` 宗教信仰 and
   any sibling wording) are realigned in this same change; the oath flag
   machinery is untouched (it already reads vessel ownership).
5. **Vestment handover (owner decision):** enrollment hands over one
   clerical armor through the church host as an NPC item delivery —
   `sister_vestments` (修女聖袍) for ordinary enrollees, `saintess_vestments`
   (聖女聖袍) instead for the vessel branch — granted inside the same
   enrollment transaction via the existing deterministic item-grant path
   (the `QuestReward` item-quantity rail; presentation reads as the host
   placing the vestment in the initiate's hands, offline-deterministic —
   the LLM `give_item` dialogue intent is deliberately NOT the channel).
   The handover is unconditional (owner decision): every enrollment receives
   exactly one vestment even if the initiate already carries that item key
   — the celebrant's gift is the rite, not the inventory, so there is no
   holding check. The grant ships in the same ledger event context
   (`char`, `host`, `item`).
6. **Preset change (same change):** `violet_altoria.passive_skills` drops
   `saintess_vessel`; the vessel-bearing starter becomes a royal princess
   awaiting nothing in particular — pre-enrollment she is simply a 王女.
   **The persona drops all religious narrative (owner decision):** no 聖女
   or 聖女繼承人 wording anywhere; the public identity loses the church
   clause; the personality's temple-blessing passages and the life story's
   consecration/倾湧-duty sentences are deleted (not rewritten into a
   successor framing) while keeping the rest of her story continuous.
   **`saintess_vestments` is removed from her `starting_items` (owner
   decision)** — the robe is no longer a family heirloom she starts with;
   she receives it from the celebrant at enrollment like every other
   initiate. All preset data-contract tests follow.

`pray` requires an existing ledger (the unenrolled are told to speak with
the celebrant). Church venues: places whose authored kwargs carry a `church`
flag (derived set in the lore package, same pattern as `shop_key`).

### 5.9 Clergy title group (owner decision, amendment)

A fixed-title family in the existing title system (`world/lore/titles.py`
`FixedTitleDef`: declarative predicate families, auto-unlock + equip only,
display-only — the owner pins these titles as usable by NO other system as a
prerequisite, which matches the title system's existing nature). Modeled on
how guild-rank titles ride the `guild_rank_reached` family:

- New predicate family `church_skills_redeemed` → parameter: an integer
  threshold. It evaluates `len(db.church.redeemed)` (the redeemed count
  only; `saintess_vessel` is never in `redeemed` and never counted).
- Title ladder (displays zh, thresholds tuning): 虔信者 3 ／ 修女 6 ／
  神官 10 ／ 主教 15 ／ 樞機 20. **No church title may display 聖女** — the
  office stays prose per the saintess-vessel spec (reaffirmed, see §9).
- Touch surfaces (all enumerated, none optional): the family enum +
  `TitlePredicate` parameter face + the `predicate_satisfied` evaluator; the
  fixed-title registry loader validation; the closed codex `category` set in
  Python AND its `titles.js` panel-validator mirror (both sides, same
  change); one-row-one-test registry tests; codex panel tests.

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
   force). The celebrant is authored with a raised initial arousal
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
- Enrollment office test: a female `human_royal` enrollment grants the
  vessel and emits `saintess_vessel_granted` exactly once inside one
  transaction; any other subrace and a male `human_royal` do not; two
  eligible royals both grant (no uniqueness); re-enrollment re-grants
  nothing; the preset no longer carries the vessel and its persona carries
  no 聖女 wording; the trickle stays disarmed before enrollment.
- Title tests: threshold boundaries (redeemed count exactly at/under each
  ladder rung); the vessel is never counted; no church fixed-title row
  displays 聖女 (registry data-contract gate).
- Vestment handover tests: ordinary enrollment receives exactly one
  `sister_vestments`; a vessel-branch enrollment without the robe receives
  exactly one `saintess_vestments`; an enrollment that already carries the
  key still receives its one; the grant is transactional with the ledger
  write.
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
- Lore realignment in the landing change: the once-per-generation 聖女
  framing in `docs/lore/overview.md` §宗教信仰 (and any sibling wording,
  e.g. `skill-trees/light.md` 聖女 footnote) becomes "any female royal may
  be donated to the church and consecrated at enrollment"; church status
  tags (〔提案〕→〔已實作〕) move with their mechanics.
- Lore status tags: `docs/lore/settlement-locations.md` §神殿／聖所 〔提案〕
  →〔已實作〕 for the ministry counter in the landing change.

## 8. Change split

### 8.1 Proposed OpenSpec changes (re-cut 2026-09-22, os-propose; owner hard
ceiling ≤ 8 tasks / ≤ one engineer-day per change — the original 28-task
`implement-church-core` violated it and was superseded;
`openspec validate --all --strict` 262/262)

| # | Change key | Scope | Delta specs (requirements) | Tasks | Commits |
| --- | --- | --- | --- | --- | --- |
| 1 | `implement-church-foundation` | `db.church` ledger + `church.yaml` (monotonicity + passive-no-negativity loader gates; acceptance/pray/accrual/payout tuning finals) + frozen `OFFERING_CATALOG`/`REDEEM_CATALOG` shells + validators + `church` place-kwarg derivation (duplicate-kwarg fail-closed) + `ChurchHost` authored on the celebrant roster row only (+ raised-initial-arousal kwarg; the sanctum steward stays a plain merchant); no player-visible surface | `church-ordination` (new, 4: ledger, rulebook gates, venues/hosts, catalogue shells) | 8 | `bbdecd6a` |
| 2 | `implement-church-enrollment` | `church join` three-stage flow + female `human_royal` vessel branch (no uniqueness) + unconditional vestment handover + violet_altoria preset/prose deletion + lore realignment + join docs trio | `church-ordination` (ADDED 6) + `saintess-vessel` (REMOVED+ADDED replacement of requirements 1+5: enrollment grant path, predicate-family extension with the global 聖女 office-name title ban reaffirmed) | 7 | `3a0022a5` |
| 3 | `implement-church-accrual` | `church pray` (venue/cap/clock accrual) + `church offer` (arousal-ordinal acceptance curve, never affinity) + `climax_while_enrolled` side-reaction + commit-bound observability + AI-dead smoke over these paths + pray/offer docs trio | `church-ordination` (ADDED 5, incl. the accrual-path determinism/observability requirement split-finer from core's omnibus) | 7 | `e2708a87` |
| 4 | `implement-church-redemption` | 16-key price-band finals + Series A/B/D `SKILL_REGISTRY` rows + grown `REDEEM_CATALOG` + `church redeem`/`merit` rail + negative-set/guard-green tests + redeem/merit docs trio | `church-ordination` (ADDED 3) | 6 | `d57949cc` |
| 5 | `implement-church-combat-ministry` | `charges: int` buff primitive + climax-transition consumption + `lamb_seal` narrowing + `rite_martyrdom_vow` `_victim_pool` filter + both byte-identical baselines + the cross-change E2E AI-dead loop proof + observability lint | `church-ordination` (ADDED 3, incl. the E2E loop-observability requirement) | 5 | `32bb25e5` |
| 6 | `implement-church-order-catalogue` | Series C (5 pure-positive passives; poverty_vow downside removed per iron rule) + Series E (3 utility) completing 24 rows + clergy title ladder (虔信者 3 ／ 修女 6 ／ 神官 10 ／ 主教 15 ／ 樞機 20, new 聖職 category) | `title-system` (ADDED 2 + MODIFIED 2 with main-spec IDs kept) + `church-ordination` (purely additive, 3) | 13 | `3c4b05b6`, duck fix `9907fd2c`, dep repoint `332922e5` |

### 8.2 Implementation batch order (serial queue)

1. **Batch 1 — `implement-church-foundation`** (apply → verify →
   archive+sync). Hard dependency: none (consumes
   `settlement-place-registry` / `guild-registration` / `shop-economy`
   verbatim; the church place kwarg rides the existing authored-kwargs
   contract, deliberately not delta'd). Owns `world/rules/church.py`,
   `world/lore/church/`, `church.yaml` — every later church change appends
   behind it.
2. **Batch 2 — `implement-church-enrollment`** (apply → verify →
   archive+sync). Depends-on batch 1 (ledger, `ChurchHost`, venues). Owns
   `commands/church.py` (created here) and the saintess-vessel main-spec
   replacement at archive (§9).
3. **Batch 3 — `implement-church-accrual`** (apply → verify → archive+sync).
   Depends-on batches 1–2 (ledger-gated flows, an enrollment to gate on).
   Appends pray/offer subcommands to enrollment's `commands/church.py`;
   touches no catalogue/price data.
4. **Batch 4 — `implement-church-redemption`** (apply → verify →
   archive+sync). Depends-on batches 1–3 (spendable merit, the docs-trio
   split point). Owns the price finals, `REDEEM_CATALOG` content, the clergy
   skill-registry block, and `church.yaml` price/rule additions.
5. **Batch 5 — `implement-church-combat-ministry`** (apply → verify →
   archive+sync). Depends-on batch 4 (its rows to redeem) + transitive 1–3
   (the E2E loop). Owns `monster_behaviour.py`,
   `defeat_aftermath/violation.py`, and the buff declaration — files no other
   change touches; parallel-safe with batch 6 once batch 4 archives.
6. **Batch 6 — `implement-church-order-catalogue`** (apply → verify →
   archive+sync). Depends-on batches 1 + 4: needs `db.church.redeemed` and
   the loader gates (1) and `REDEEM_CATALOG` + the redeem rail (4); the §9.2
   predicate-extension sanction travels with batch 2's saintess-vessel delta.
   Its duck-verified additive delta edits none of the other changes' ADDED
   requirements. Code-conflict note: it appends to redemption-owned files
   (`REDEEM_CATALOG`, the clergy skill-registry block, `church.yaml`) — it
   MUST NOT start before batch 4 is archived; the title-side files it touches
   (`world/lore/titles.py`, the planner evaluator,
   `web/webclient/presentation/title_codex.py`, `protocol/constants.js` +
   its test) are owned by no other active change.
7. Sub-project 2 (temple service economy) and sub-project 3 (confession /
   observance commands) are separate future designs; both build on the
   merit ledger and church-place flag that batch 1 lands.

## 9. Amendments to `openspec/specs/saintess-vessel/spec.md` (carried by
`implement-church-enrollment` as a delta spec)

1. **Grant path:** the vessel stops being preset-initial state; the sole
   acquisition channel becomes church enrollment by a female `human_royal`
   character, with no uniqueness cap. The PASSIVE practice/unlock/conferral guards, the
   granted-only character, and the granted-event observability requirement
   are unchanged (the enrollment transaction reuses the same write path and
   the same `saintess_vessel_granted` event; the preset-activation grant
   scenario is replaced, not duplicated).
2. **Title invariants:** the no-title-state decision, the byte-identical
   `title_collection`/`title_equipped` oath-flip scenario, and the ban on
   any fixed-title row naming the 聖女 office are all reaffirmed. The
   `TitlePredicateFamily` closed set is extended with the church redemption
   count family (a count of redeemed catalogue skills, which by
   construction can never reference the vessel); the extension is what this
   delta amends, the office-name ban is not.

Sub-project 2 (temple service economy: paid heal/purify services, donation
economy) and sub-project 3 (confession and the wider observance command set)
get their own designs; the merit ledger and church-place flag are designed
here so they can build on them without re-cutting the surface.
