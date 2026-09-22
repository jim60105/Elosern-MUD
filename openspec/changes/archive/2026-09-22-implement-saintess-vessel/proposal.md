# Proposal: implement-saintess-vessel

## Why

The 光明教會 Saintess (聖女) is the 職位 incarnation of the light tree's 「高潮即峰值」 design, but her only unimplemented piece remains marked 〔提案〕 in `docs/lore/skill-trees/light.md` §「與相鄰系統的接縫」: the PASSIVE `saintess_vessel` (劇情授予, non-genealogy node). Until it lands she operates under generic 聖職者 rules, contradicting the lore contract that her arousal idles in the 微興奮～中等 band and that her public blessing rites read her excitement tier. Everything the footnote depends on is already landed (`blessed_climax`, `bliss_apotheosis`, the `virgin` flag + `first_vaginal_penetration` rule, `saintess_vestments`, 露出計價) — this change closes the last seam.

## What Changes

- Register the PASSIVE `saintess_vessel`（聖女容器）in `world/skills/registry/data_utility_passives.py` with the same qualifier-row shape as `pain_to_pleasure` / `rapture_renewal` / `priestly_grace`: PASSIVE, `element="light"`, `SkillCategory.ENHANCEMENT`, empty effects, no lineage prerequisites. Granted by 劇情/聖職敘階 via preset `passive_skills` (the shipped Saintess card); practice-earning is structurally impossible (the progression and cross-lineage-unlock PASSIVE guards reject it) and it joins the non-conferrable qualifier class like its three siblings.
- 聖光涓流: while `saintess_vessel` is owned, the pleasure decay floor rises to 微興奮 (a holder never decays below 15), and once per world-clock `advance()` (non-combat sources) the holder's gauge is pinned up to 15 if below it, or given one deterministic ±1 fluctuation clamped inside [15, 59] if inside the band, no-op at/above 60. The fluctuation direction is a stateless parity of the resulting world tick and entity identity — replay-stable across a rolled-back and retried advance (no RNG inside the settlement transaction). All writes stay inside `world/rules/` through `apply_pleasure_gain` / the ownership-aware `decay_tick` branch; the single-writer boundary is untouched.
- Two ceremonial reads, one per named rite, authored numbers preserved:
  - `sanctified_ward`: new `skill_owned: saintess_vessel` row on a distinct `blessing_arousal_scale` key; the cast-time grace snapshot folds `1 + max(recovery_arousal_scale, blessing_arousal_scale) × ordinal`, so the tier is read exactly once even with `priestly_grace` also held (never doubled — same-key numerics ADD at merge).
  - `goddess_blessing`: its authored heal 2.8 and `light_blessing` +18/60 s stay byte-identical; the tier read lands as one new 恩典 row on the established pattern (`saintess_vestment_grace` shape): vessel holder + live `light_blessing` + arousal ≥ 中等 → independent defense +6, displayed as its own status-sourced condition.
- Saintess title governance (design.md D5): narrative-only, zero engine title state. The title-system's closed predicate families have no 王室獻任/聖座祝聖 expression and no deterministic removal path; the oath is already engine state (`virgin`, irreversibly flipped by `virginity_once`). The change owns only observability: `saintess_oath_broken` (commit-bound `transaction.on_commit` emission at the flag flip, gated on vessel ownership so a non-holder's virginity flip is not a Saintess oath event) and `saintess_vessel_granted` (preset activation seeding), both via the `world.observability` facade with plain-data contexts.
- No player-command changes: the ceremonies ARE `cast sanctified_ward` / `cast goddess_blessing` (lore 「儀典縮寫」), so `docs/game/commands.md`, `docs/game/command-reference.md`, and `tests/test_command_docs.py` need no edits.

## Capabilities

### New Capabilities
- `saintess-vessel`: the 聖女容器 passive — its ownership-gated 聖光涓流 idle-arousal band behavior on the world clock, the once-only arousal-tier reads on both named blessing ceremonies, and the commit-boundary observability events.

### Modified Capabilities
None. The registry row and the two `combat_modifiers.yaml` rows are shipped-content data whose observable behavior is specified entirely by the new `saintess-vessel` capability; neither `skill-registry` nor `combat-modifier-table` changes its own requirement text (the table's existing one-row-one-test and closed-engine requirements consume the new rows verbatim).

## Dependencies

depends-on: (none)

No prerequisite changes: 劇情授予/passive-grant infrastructure exists (`PlayerPreset.passive_skills`, `db.skills.passive`, `skill_owned`/`skill_qualified` rule gating — the exact shape the three existing clergy qualifier passives use). Prerequisite landed specs consumed verbatim: `damage-state-feedback` (pleasure reaction writes), `world-clock` + `climax-settlement` (the settlement pass the trickle hooks), the buff/HOT machinery (`RecoveryRatePolicy`, `snapshot_grace_multiplier`, `recovery_snapshot_kwargs`), `sexual-transition-rulebook` (`virginity_once`), `equipment-effects` (`saintess_vestments`), `combat-modifier-table` (grace-row pattern), `title-system` (studied and deliberately NOT modified).

## Impact

- `world/skills/registry/data_utility_passives.py` — one registry row.
- `world/lore/player_presets/data_pack_cards.py` — Saintess preset's `passive_skills` gains the key.
- `world/rules/rulebook/combat_modifiers.yaml` — two `skill_owned: saintess_vessel` rows; `world/rules/rulebook/status_display.yaml` — display codes for both.
- `world/rules/`: ownership-aware floor in `sexual_state/lifecycle.py::decay_tick`; `saintess_trickle_step` in `pleasure.py` called once per advance from `clock.py::advance`; grace fold in `action/effects/buffs.py::recovery_snapshot_kwargs`; oath event in `sexual_transitions.py::_apply_then`.
- Observability: two new boundary events via the `world.observability` facade, both commit-bound, plain-dict contexts.
- New test modules registered in `.github/evennia-shards.json`.
- No new storage fields, no command surface, no title state, no backward-compat shims (unreleased project).

## Batch:

depends-on: (none — all prerequisites already landed/archived)

Code-conflict notes: touches `data_utility_passives.py` (row appended at the clergy qualifier block end — registry order is observable), `combat_modifiers.yaml` (two rows appended after `priestly_grace_recovery_scale`), `clock.py`/`pleasure.py`/`lifecycle.py` settlement plumbing, and `buffs.py` grace fold. No other active change currently owns these files (openspec active-change list is empty at proposal time).
