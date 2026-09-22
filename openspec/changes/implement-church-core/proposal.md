## Why

The Light Church exists only as lore plus one generic shop counter and three
unearnable PASSIVE clergy qualifier rows — `docs/lore/skill-trees/light.md`
promises 「劇情／聖職敘階授予」 but no channel delivers it, and no normal
character can become a nun. The approved design
(`docs/superpowers/specs/2026-09-22-church-system-design.md`, five owner
amendments baked in) makes the church an institution: a merit ledger earned by
behaviour (prayer, sexual offering, the erotic practice itself), a deterministic
enrollment behind a new `ChurchHost` component, and an ordination (redeem)
ladder. This is sub-project 1 (`implement-church-core` per design §8); the
Series C/E catalogue rows and the clergy title ladder ship in the sibling
change `implement-church-order-catalogue`.

## What Changes

- New character ledger `db.church` (merit, enrolled tick, redeemed keys, daily
  counters) — merit is a non-transferable, non-spendable-elsewhere counter; all
  writes live in the new `world/rules/church.py` (single-writer boundary).
- New rulebook slice `world/rules/rulebook/church.yaml` (accrual, acceptance
  curve, pray, offering rows) through the existing `load_rules` family, with the
  one-row-one-test correspondence gate and two loader gates: monotonic
  acceptance curve, and the passive-no-negativity polarity gate (iron rule — no
  PASSIVE row may carry a negative-relative-to-baseline effect; trade-offs live
  in prices, never in effects).
- Enrollment: `church join` (aliases 入教／洗禮) — guild-style three stage
  (resolve local `ChurchHost` → schedule gate `interaction_reason(host,
  "service_church")` → deterministic `enroll`), emitting `church_enrolled`.
  **A female `human_royal` enroller is additionally granted `saintess_vessel`
  in the same transaction** via the canonical granted-passive write path and the
  existing `saintess_vessel_granted` event — no office uniqueness (every
  eligible royal becomes a saintess).
- **Unconditional vestment handover** inside the enrollment transaction via the
  deterministic item-grant rail: `sister_vestments` (ordinary) or
  `saintess_vestments` (vessel branch) — exactly one vestment per enrollment,
  no holding check.
- **BREAKING (preset data):** `violet_altoria` drops `saintess_vessel` from
  `passive_skills` and `saintess_vestments` from `starting_items`; the persona's
  religious narrative (聖女/聖女繼承人 wording, temple-blessing passages,
  consecration sentences) is DELETED, not rewritten into a successor framing —
  pre-enrollment she is simply 王女.
- `church pray` (venue + daily cap + world-clock time cost + accrual),
  `church offer <npc> [row_key]` (explicit-selection sexual offering; NPC
  arousal-ordinal acceptance curve through injected `roll_d100`; no affinity
  gate, no venue binding), `church redeem [list|<key>]` (one-shot, all-or-nothing
  granted-skill write; `saintess_vessel` never in the catalogue, pinned by
  test), `church merit`. `climax_while_enrolled` accrual rides the
  `state_reactions.yaml` side-reaction rail; unenrolled behaviour stays
  byte-identical.
- Series A/B/D redemption rows (16 of the 24): the three clergy qualifier
  passives + `vow_of_service`; eight rite actives incl. `rite_lamb_mark` (new
  `charges` buff primitive + lamb-seal target-preference narrowing in
  `monster_behaviour_policy`) and `rite_martyrdom_vow` (defeat-aftermath
  `_victim_pool` filter); four sexual-ministry actives doubling as advanced
  `OFFERING_CATALOG` rows.
- Lore realignment: `docs/lore/overview.md` 宗教信仰 once-per-generation 聖女
  framing retired (any female royal may be donated and consecrated at
  enrollment); `skill-trees/light.md` footnote; `settlement-locations.md`
  神殿／聖所 〔提案〕→〔已實作〕 status tags.
- Player-command docs trio (`docs/game/commands.md`,
  `docs/game/command-reference.md`, `tests/test_command_docs.py`) for
  `church join/pray/offer/redeem/merit`.
- **§9 saintess-vessel delta:** the vessel's sole acquisition channel becomes
  enrollment (preset grant replaced, not duplicated); the title-family closed
  set extension for the church redemption count is sanctioned, the 聖女
  office-name title ban reaffirmed.

## Capabilities

### New Capabilities
- `church-ordination`: the whole sub-project-1 pipeline as one capability — the
  `db.church` ledger, the `church.yaml` rulebook slice with its loader gates,
  enrollment (incl. the subrace/sex-gated vessel grant and the unconditional
  vestment handover), pray, offering, climax accrual, the redemption engine and
  its Series A/B/D rows, the lamb-seal and martyr-vow combat rails, and the
  five observability events.

### Modified Capabilities
- `saintess-vessel`: the preset-activation grant path is REPLACED by the
  church-enrollment grant path (design §9.1), and the title-invariant
  requirement is amended to sanction exactly one predicate-family extension —
  the church redeemed-count family — while reaffirming the no-title-state
  decision and the 聖女 office-name ban (design §9.2).
No other capability's requirement text changes: the `church` venue kwarg rides
the place registry's existing free-form authored-component-kwargs contract and
the `ChurchHost` attachment rides the existing profession-blueprint roster
derivation (`settlement-place-registry` and `place-driven-service-sync` consume
the new authored content verbatim); the clergy title ladder and its predicate
family are the sibling change's `title-system` delta, sanctioned here only
through §9.2.

## Dependencies

depends-on: (none — prerequisite capabilities already landed/archived)

Size: ≤ one engineer-day, exactly per design §8 (the 24-row catalogue alone
exceeds the convention; this half ships ledger + rails + 16 rows, the sibling
ships 8 rows + the title ladder).

Consumed verbatim: `guild-registration` (the three-stage host pattern),
`title-system` (studied; only touched by the sibling change), `shop-economy` /
integer copper, `world-clock` + `climax-settlement`, `action-resolution-pipeline`
(offering act execution rails), `sexual-transition-rulebook` (NPC arousal
state), the granted-passive write path (`lineage_ownership_closure` shape), the
`QuestReward` item-quantity rail (vestment grant channel), `state_reactions.yaml`
side-reaction rail, `monster_behaviour_policy`, `defeat_aftermath/violation`.

## Impact

- New: `world/lore/church/` (frozen `OFFERING_CATALOG`, `REDEEM_CATALOG`,
  church-place derivation), `world/rules/church.py` (sole writer),
  `world/rules/rulebook/church.yaml`, `commands/church.py`, `ChurchHost`
  component (sibling of `GuildStaff`).
- Edited: `world/skills/registry/` (16 new SKILL_REGISTRY rows), buff
  declaration (`charges` primitive), `monster_behaviour.py` (seal narrowing),
  `defeat_aftermath/violation.py` (martyr filter), `state_reactions.yaml` +
  `church.yaml` rows, `world/lore/player_presets/data_pack_cards.py`
  (`violet_altoria`), the two clergy NPC roster rows (+ initial-arousal
  authoring kwarg), `.github/evennia-shards.json`, docs trio + lore docs.
- No quest channel, no affinity gate, no LLM participation in any mechanic
  (offline determinism), no backward-compat shims (unreleased project).

## Batch:

depends-on: (none)

Code-conflict notes: owns `world/rules/church.py`, `world/lore/church/`,
`commands/church.py`, `church.yaml`, `data_utility_passives.py` (Series A/B/D
rows appended), the preset row for `violet_altoria`, and the saintess-vessel
main-spec text at archive. `implement-church-order-catalogue` appends Series
C/E rows to the same registry block, `church.yaml`, and `REDEEM_CATALOG` after
this change lands — queue it behind this one. No other active change exists at
proposal time (openspec active-change list was empty).
