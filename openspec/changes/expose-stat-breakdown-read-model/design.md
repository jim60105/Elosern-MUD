# Design: expose-stat-breakdown-read-model

## Context

Parent design §11. The character panel is the exact version-4 payload of
`web/webclient/presentation/character.py` (`CHARACTER_SCHEMA_VERSION = 4`),
built from the strict read-only `StatusView` inputs in
`world/rules/status_query.py`; the compact `status` surface shares that
source. v4 trait rows are `{key, label, current, max?}` — the legacy JS
renderer displays `current` for EVERY row (statics included), so `current`
must stay the total-display field during the P6→P7 transition. Existing
AUTHORITATIVE value computations: gauge maxima via the shipped gauge
reader `round((base + mod) × mult)`; `magic_level` via
`SkillHandler.effective_value` (its own rounding form); defense/attack/
agility via P2's adjusted helpers over the merged (rule-table + equipment)
no-create bundle, with agility additionally floored ≥ 0; initiative keeps
its DOCUMENTED raw-agility exception; to-hit/heal apply consumer-specific
floors AFTER the effective stat. Panel purity is a hard contract:
presenters never materialize handlers (P4's no-create pattern; even
`_require_gauge` reads raw attributes deliberately —
`SkillHandler.effective_value` touches `entity.traits`, so the breakdown
must NOT call it with a live entity). The legacy client gates
`schema_version !== 4` (`protocol.js:3227`) with exact-shape v4 validators
on both the Python and JS sides; `combat_panel` and other panels keep their
own versions.

## Goals / Non-Goals

**Goals:**

- One canonical pure breakdown builder producing, per panel stat:
  `base` (stored literal), accounting-complete named `layers`
  (`{source, name, kind, amount}`; skill/condition/equipment), and
  `effective` computed FROM THOSE LAYERS with the authoritative per-stat
  computation (see D1's table).
- Character payload v5 ships with those rows; `current` remains the
  legacy total field on every row; equipment rows carry the P3 adjustment
  text.
- Text-client parity; compact surface stays totals-only, fed from the SAME
  builder (no second assembly path).
- Legacy client keeps rendering correct totals at v5 (statics included)
  until P7.

**Non-Goals:**

- Vue rendering / Storybook / Vitest component / showcase v5 migration
  (P7), new stats, mutation-path changes, removing `current` (P7's call).

## Decisions

### D1 — Authoritative computation table, exceptions named, parity per mapping

The panel does NOT invent a universal formula and does NOT claim every
combat consumer equals the panel row. Per displayed stat, the authoritative
computation and its layers are:

| panel stat | authoritative value | layers must exactly explain |
|---|---|---|
| atk_phys, defense | merged-bundle flat/pct applied over the stored base with skill mults, single final rounding (the same primitives P2's adjusted attack/defense use) | skill mult ×, condition flat/pct, equipment flat/pct |
| agility | same as above, THEN floored ≥ 0 (P2 floor) — panel shows the floored value; initiative's raw-agility exception is EXPLICITLY OUT of parity scope (documented) | same + floor is display-clamp only |
| magic_level | the shipped `SkillHandler.effective_value` arithmetic (its rounding form), fed by the same owned-key × registry fold | skill mults only (no rules adjust it today; if one did, it layers) |
| hp/mp/sp `max` | the shipped gauge-reader value `round((base + Σ flat) × Π mult)`; layers decompose it (equipment caps = equipment flat layers, plus condition flats/mults if any) | exactly the components the reader consumes |

`effective` is composed FROM the assembled layer list (not a parallel
recomputation), so accounting completeness and value are the same fact.
Parity tests assert each panel stat against ITS named authoritative
computation under identical fixed inputs — never a blanket "all combat
consumers" claim. Consumer-specific floors/roundings that run AFTER the
effective stat (to-hit, heal) are listed as non-contradictions, not parity
targets.

### D2 — Layers are accounting-complete and fail-closed

Every non-empty contribution that feeds the authoritative computation MUST
appear as one layer whose `name` resolves through a registry lookup (skill
registry label / `STATUS_DISPLAY` label / item `display_name_zh`). Truly
empty sources contribute nothing; a contribution with NO resolvable label
(unknown buff key, rule without display entry, item missing a registry
name) makes the read model raise — the panel then serves the shipped
common unavailable form (fail-closed, never a silently-missing layer,
never truncation while keeping the value). Layer identity and sort tuples
are fixed: skill `(skill_key)`, condition `(source_kind: buff|rule,
key)`, equipment `(slot-order, item_key)`; amounts are signed,
`kind ∈ mult|flat|pct`. Bounds: ≤ 32 rows, ≤ 16 layers/stat; exceeding a
bound on a legitimate actor is a fail-closed unavailable (test-pinned with
a synthetic 17-source actor), never silent truncation.

### D3 — Pure builder first, one data flow

The breakdown builder is a pure function over validated snapshots: stored
trait values read through the SAME raw-attribute helpers the shipped
readers use, owned-skill mults from `owned_keys()` (pure stored read) ×
registry `StatMultiplyEffect`s, and the merged NO-CREATE bundle
(P2/P4 pattern). It never receives a live-entity property access path:
no `entity.traits`, no `SkillHandler` instantiation (its arithmetic is
reproduced from the same primitives and pinned equal by test), no
handler materialization. `status_query` calls it ONCE per read: the
character presenter requests the layer-bearing view, the compact presenter
serializes only `current`/`effective` from the same result — one assembly
path, two renderings. A regression test asserts a never-materialized
entity's persisted attributes are byte-identical after panel build.

### D4 — v5 rows keep `current` as the legacy total field

Trait rows become exactly `{key, label, base, current, max, effective,
layers}`: `current` stays the total-display value on EVERY row (statics:
equal to `effective`; gauges: the persisted resource remainder, which is
state, not a formula, and carries no layers — its row's layers decompose
`max`). `base`/`effective`/`layers` are new. v4 exact-shape validators are
replaced by per-version validators (`v4` kept ONLY for the legacy test
fixture, `v5` for production dispatch); the JS side gains the matching
version-dispatched exact validator — this is validator work, not a one-line
gate change.

### D5 — Text client prints the same rows

Text status/inventory render
`label current/effective（來源｜來源…）` from the identical builder output
(server-side 正體中文) and adjustment summaries; compact combat status
keeps totals only; no command key/alias/syntax change.

### D6 — Legacy tolerance = totals, correctly

Legacy client at v5: `current`/`max` render exactly as before (statics
included — the null-current trap is designed out by D4); `layers` are
ignored. Python+JS validators accept version-dispatched exact shapes; P7
renders breakdowns and drops v4.

## Risks / Trade-offs

- [Magic parity reproduces `SkillHandler` arithmetic outside the handler] →
  pinned by a dedicated equality test over owned-key/registry fixtures;
  drift fails loudly.
- [Fail-closed panel unavailable on a labeling bug] → preferred over an
  untrustworthy breakdown; the same loader/display-coverage gates make it
  a build-time failure in practice.
- [Version-dispatched validators double exact-shape maintenance briefly] →
  P7 deletes v4.

## Open Questions

None.
