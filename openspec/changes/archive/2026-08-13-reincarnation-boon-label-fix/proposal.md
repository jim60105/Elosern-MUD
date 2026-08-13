## Why

The three per-character 轉生特典 passives shipped with transliteration variants of the preset
character names: 轉生祝福·由花/由奈/艾露西亞. The preset-skill-kits change then bound these exact
skills to the template characters 悠花、悠奈、伊洛希雅, so the player-facing skill labels no longer
match the characters that own them. A player who starts as 悠花 sees a skill labeled 轉生祝福·由花 —
the same person, written two different ways.

## What Changes

- `reincarnation_boon_elosia` label: 轉生祝福·艾露西亞 → 轉生祝福·伊洛希雅 (matches the preset
  display name 伊洛希雅; the skill key, effects, and mechanics are unchanged).
- `reincarnation_boon_yuka` label: 轉生祝福·由花 → 轉生祝福·悠花 (matches preset 悠花).
- `reincarnation_boon_yuna` label: 轉生祝福·由奈 → 轉生祝福·悠奈 (matches preset 悠奈).
- `world/rules/rulebook/status_display.yaml` row `reincarnation_boon_yuka_agility_bonus` label:
  轉生祝福·由花敏捷提升 → 轉生祝福·悠花敏捷提升 (derived player-facing status text).
- `world/rules/rulebook/combat_modifiers.yaml` code comment updated to the corrected name.
- No key, effect, cost, kind, or target-spec change anywhere; no database migration, no
  backward-compatibility layer (project is unreleased with zero users).

## Capabilities

### New Capabilities

- `skill-registry`: Delta requirement pinning the three reincarnation-boon labels to the preset
  display names 悠花/悠奈/伊洛希雅 so registry content and preset content cannot drift again.

## Key Decisions

- Labels are the only surface changed; `reincarnation_boon_*` keys stay stable because the preset
  skill kits and the skill-registry spec reference them by key.
- A parity test pins the correspondence: each `reincarnation_boon_<suffix>` label SHALL contain
  the display name of the preset whose kit declares that boon, so a future rename of either side
  fails loudly instead of silently diverging.
