## Why

水膜護身 is the whole game's only shield paid in MP: "受擊時以 MP 代扣 30% 的打擊量（代扣總量上限 30 MP，或持續 60 秒後失效），護的是人，付的是魔力." The damage pipeline has no second-resource divert today — `_handle_damage` computes one HP amount and stages one HP write — and the shipped `water_shield` buff row is the dev-era inert `bounds {target: defense, ceiling: 5}` placeholder from the 2026-08-12 catalog, which converts "護的是人，付的是魔力" into an ordinary earth-style defense bump: an honest mechanic rendered as a lie of data. Water's identity clause (保護的資源與掠奪的資源是同條 MP 條 — the shield drains the same gauge the mana tide drains) is unsatisfiable with a bounds row.

## What Changes

- Extend the buff-definition modifier vocabulary with one validated `divert` profile: `{target: <gauge>, fraction: f, cap: N}` — "while active, up to `f` of each incoming damage amount is diverted to the named gauge's owner, up to a cumulative `cap` over the instance lifetime" — loaded fail-closed (fraction finite in (0,1], cap positive int, target a `GAUGE_KEYS` member, mutually exclusive with `rate`/`decay` only where the loader already enforces key exclusivity).
- Consume active divert profiles in the existing damage stage (`_handle_damage`, the same post-defense computation point where light's potency/judgment stages run): per hit, `diverted = min(round(amount × f), remaining cap, owner's current target-gauge MP)`; the staged HP write shrinks by `diverted` and the divert is paid from the gauge **through the canonical MP writer** in the same commit, updating the buff instance's consumed-budget cache so the cumulative cap holds across hits and refreshes per the loaded rule.
- Replace the inert `water_shield` bounds row with the real profile row (`water_film`: divert mp 30 %/cap 30, duration 60) and its display entry here; the registry node rebinding is catalog data (change 4). No alias, no migration: the old bounds-shaped row is deleted in this change (given: wholesale replacement, zero users).
- Divert semantics contract (design): a divert that zeroes the payer's MP is an ordinary attributed crossing through the writer (the wave's global-fact rule — the rule layer decides consequences); a hit that misses or lands zero stages no divert; `hp_loss` feedback sees only the actual HP loss (the diverted part never was HP loss).

## Capabilities

### New Capabilities
None — the divert is one more authored modifier profile on existing capabilities.

### Modified Capabilities
- `combat-resolution`: the damage magnitude stage consults validated divert profiles before staging the HP write (superset of the banded-multiplier requirement, whose formula stages the light wave opened stay untouched and ordered first).
- `buff-handler-integration`: buff definitions may configure a `divert` profile (superset of the rate/bounds/decay configuration requirement — its "at most rate/bounds/decay" enumeration is widened deliberately with the loader's fail-closed posture extended).

## Impact

`world/rules/buffs.py` (profile loading/validation + consumed-budget cache helper); `world/rules/combat.py` (one divert stage inside `_handle_damage`'s amount pipeline + staging); `world/rules/rulebook/buffs.yaml` (delete inert `water_shield` bounds row, add `water_film` divert row) and `status_display.yaml`; new focused test modules → `.github/evennia-shards.json`. `openspec list --json` returned an empty change set at authoring time — no serialization gate. Depends on `water-mp-depletion-reaction` (canonical writer for the divert payment); independent of `water-mana-transfer`. One engineer-day. Verification is synthetic program-behavior tests only — per the ratified NON-GOAL, no water data-contract tests and no echo of the water.md table.

Planning artifacts only this turn; no apply/archive/sync/merge.
