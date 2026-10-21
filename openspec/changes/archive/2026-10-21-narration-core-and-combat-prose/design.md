# Design

## Context

- `world/rules/event_log.py` owns `EventEntry` (frozen: `kind`, `actor`, `target`,
  `data`, `text_template`), `EventLog`, and the two pure renderers. `render_entry_text`
  is the single format call; `world/rules/combat_beats.py` reuses it so a beat's text is
  one-to-one with the delivered line and rejects a beat over `MAX_BEAT_TEXT` (256 code
  points) by making the whole round's panel unavailable.
- Step 7 (`world/rules/action/event_log.py::_step7_build_event_log`) turns staged
  `PendingEffect.description` strings into entries, one shared `_ENTRY_TEMPLATES` row per
  kind, and pairs `resource_spend` with a `trait_delta` entry. It is inside the resolver
  transaction, runs after every effect is staged and before any `apply()`, and it may
  only read.
- Verified counts: 260 `SKILL_REGISTRY` rows = 223 ACTIVE + 37 PASSIVE. Of the 223
  ACTIVE rows, 157 are non-sexual (115 elemental magic, 16 martial arts, 14 holy rite,
  11 divine mystery, 1 enhancement) and 66 are sexual acts. `SEXUAL_ACT_REGISTRY`
  carries the 66 sidecars; the other two `SEXUAL_ACT`-category rows
  (`divine_sexual_mastery`, `reincarnation_boon_yuna`) are PASSIVE display rows.
- The sexual catalog emits 13 event names, and its acts use 8 of the 11 lifetime
  counters (`_COUNTER_MUTATORS`).
- `run_round` already knows `session_id`, `round_index` and the action `slot_index`;
  `session_id` is deterministic (`mode:pk:tick`). `cast_settlement` already reads the
  world clock. Both are the seeds narration needs, so no new clock or counter is
  introduced.
- No production path calls `world/ai/narrator.py`; `render_plain_text` is the
  deterministic channel. This change keeps it that way.

## D1. Authored text lives in a separate, validated narration catalog — not in `SkillDef`/`SexualActDef`

New package `world/skills/narration/`:

```
vocab.py       bounds (MAX_LINE_CODE_POINTS, MAX_NAME_CODE_POINTS, MAX_SLOTS),
               the band tables, the frozen dataclasses (NarrationRow, NarrationBands)
families.py    the family-tier rows (element x shape, act line, category) every active
               skill falls back to until its own row lands
data_*.py      authored per-skill rows, one contiguous module per content family,
               mirroring the registry's data_*.py slicing discipline
catalog.py     frozen NARRATION_CATALOG: Mapping[str, NarrationRow], family tiers,
               and the shared kind / verdict / band / structural pools
select.py      pure selection: seed -> variant index, band -> clause, compose()
validation.py  fail-closed coverage + bounds validation
```

`NARRATION_CATALOG` is keyed by the registry's own skill keys; the registry stays the
single source of truth for *which* skills exist, and the catalog is validated against
it. Rows are frozen, mappings are `MappingProxyType`, and the module imports
`SHIPPED_SKILL_REGISTRY` plus `SEXUAL_ACT_REGISTRY` (never the live `SKILL_REGISTRY`
binding) so a synthetic test scope cannot trip or skew validation — the same discipline
`world/rules/cross_lineage_unlock.py` and `world/rules/guild_exam_restrictions.py`
already follow.

Rejected alternatives:

- **Required `SkillDef.action_narration` field.** 223 rows live in 15 order-sensitive
  `data_*.py` slices plus 6 act modules built through `_act_family`'s positional tuple;
  adding a required field touches every row, changes `_act_family`'s arity, and forces
  every hand-built `SkillDef` in tests and production (`flee`) to grow a presentation
  field. Registry order is observable, so the churn is also risk surface for no gain.
- **Optional field with a default.** An optional presentation field cannot carry a
  coverage guarantee: a new skill silently renders the generic fallback, which is the
  exact defect this change removes.
- **YAML rulebook.** The repo's rulebooks own mechanics and load through
  `world.rules.rulebook.schema`; prose rows have no numeric validation and would need a
  second, untyped loader. Python data modules give typed, import-time-checked rows and
  the same `data_*.py` review shape the skill registry already uses.

## D2. Lookup chain is exact → family tier → generic pool → compact fallback

Selection never raises at runtime. Resolution order for one entry:

1. `NARRATION_CATALOG[skill_key].kind_lines[kind]` (per-skill kind override),
2. the family tier for the skill's category/element/act line,
3. the shared `KIND_POOLS[kind]`,
4. `KIND_POOLS["_compact"][kind]` (zero participant slots).

The log's **first** entry additionally carries the skill's `action` clause in front of the
selected clause. A `kind_lines` row on that first entry is authored as an *outcome* clause
(what the skill's signature effect does) and is composed the same way; on every later entry it
stands alone. Tiers 1–3 are tried in order for each role, so a missing per-skill override never
masks a family line.

The family tier exists only so changes 2–4 can land content in slices: an elemental
spell without its own row renders an element-and-shape line, a sexual act renders a
line-of-act line. Runtime leniency is deliberate (an unknown key, e.g. a synthetic kit
row, must still narrate); *authoring* coverage is enforced at import by D6.

`PENDING_FAMILIES` starts as the frozen set of every ACTIVE family whose per-skill rows
have not landed yet — `{martial_arts, holy_rite, divine_mystery, enhancement,
elemental_magic, sexual_act}` — and each following change removes its own families. The
set only shrinks: a test pins it, so re-opening an exemption fails.

## D3. Variant selection is a CRC over stable identifiers — no gameplay RNG

```python
def variant_index(seed: str, count: int) -> int:
    return zlib.crc32(seed.encode("utf-8")) % count
```

`seed` is a canonical `"|".join` of, in this fixed order: the caller-supplied narration
scope, skill key, entry kind, the entry's ordinal in the log, the entry's target key,
and the qualitative band id. `zlib.crc32` matches the repo's existing deterministic
selection precedent (`world/rules/pleasure.py`'s vessel trickle) and is stable across
processes, unlike `hash()`.

The narration scope is an optional `event_context["narration_scope"]` string:
`run_round` supplies `f"{session_id}|{round_index}|{slot_index}"` and
`cast_settlement` supplies `f"field|{clock.tick}|{actor_key}"`. Callers that supply
nothing get `""` and identical inputs still select identically.

**Why a settled round always renders the same line:** the pick happens once, inside the
round transaction, and the chosen template is stored in the frozen
`EventEntry.text_template`. Rendering a settled log therefore never re-selects; the beat
panel, the text channel, a serialized record and a replay all format the same stored
string. Selection consumes no RNG stream, so `roll_d100` draw counts, hit outcomes,
damage numbers, timing and committed state are bit-identical with narration on or off.

Rejected: `random.Random(seed)` (still imports the randomness surface the project audits
and invites a future `seed=None`), `hash()` (PYTHONHASHSEED makes it per-process), and
using the round's `RoundRecord` (unavailable out of combat and not present at step 7).

## D4. The action line rides the first entry; entry cardinality does not grow

A separate "action" entry per resolved action would add one beat per action, and
`MAX_BEATS` is 64 while `_MAX_ACTIONS_PER_TURN` is 3 — a six-combatant round can already
reach the cap, so one more entry per action would push ordinary rounds into
`too_many_beats` and take the panel away. Instead the first entry's text is composed:

```
<skill action clause> + <outcome clause for this entry's kind and band>
```

e.g. `悠花的火焰箭拖著赤尾破空而出——` + `箭矢咬進哥布林的肩窩。` A miss composes the
same action clause with the miss clause, which is exactly the information the roll
entry carried before (without the number). Later entries render from their kind pool,
so a two-target AREA cast does not repeat the action clause per target.

The single exception: when a successful action produces zero entries — a skill whose
effects stage nothing (the shipped `rite_*` rows with empty `effects`), or a
fully-filtered audience — one `action_narration` entry is emitted. Today that cast
prints nothing at all, so this adds a beat only where the round previously had none.

## D5. Qualitative severity bands, computed at construction, stored nowhere

Frozen tables in `vocab.py`, ascending, validated at import (finite, in `(0, 1]`,
strictly ascending, closed by a final band):

| table | ratio | bands |
| --- | --- | --- |
| damage | `amount / target max hp` | `graze`, `light`, `solid`, `heavy`, `dire` |
| heal | `amount / recipient max hp` | `minor`, `restoring`, `bountiful` |
| pleasure | `amount / gauge span` (100) | `faint`, `clear`, `strong`, `overwhelming` |

The band is a pure function of values already present at step 7 (`amount`, and the
target's stored max HP through the same read `_defeated_entry` already performs), so it
adds no state read with side effects and no new `data` key: `EventEntry.data` stays
byte-identical, and the AI prompt/transcript payloads keep their exact numbers.

Roll outcomes use the existing `data["hit"]` flag; resist verdicts use
`resisted`/`auto_comply`. Resource spend carries no magnitude: a percent band of a
cost is noise, and the act of spending is the narratable fact.

## D6. The 256-code-point bound is guaranteed twice, and validated at import

`MAX_BEAT_TEXT = 256`. The catalog contract:

- every authored line has at most 2 participant slots (`{actor}`, `{target}`);
- for every authored line *and* every composed (action × outcome) pair,
  `literal_code_points + MAX_NAME_CODE_POINTS * slots <= 248`, where
  `MAX_NAME_CODE_POINTS = 80` (the widest authored name bound in the repo; character
  names are capped at 64 by `creation_wizard.NAME_MAX_LENGTH`);
- every kind has a compact fallback with zero slots and `<= 64` code points;
- no line may contain an ASCII digit or a `{data[...]}` field (D7).

Composition is enumerated at import because the pair space is tiny (≤ 3 actions × ≤ 4
outcome clauses per row).

At construction the selector additionally renders each candidate against the *actual*
names and takes the first that fits 256 code points (deterministic order: the seeded
variant, then forward, then backward), finally the compact fallback. The arithmetic
bound covers the authored catalog; the construction filter covers pathological entity
keys. Together, narration cannot cause `beat_text_too_long`, so the beats panel can
never be lost because of prose.

Rejected: raising `MAX_BEATS`/`MAX_BEAT_TEXT` (a published client protocol bound and a
parity contract), truncating a line (breaks the "beat text equals the delivered line"
and HP-projection discipline), and clamping participant names (the player would see a
mutilated name in one channel only).

## D7. Mechanical entries become varied, story-like, and numberless

`_ENTRY_TEMPLATES` is replaced by `KIND_POOLS` (3–5 variants per kind) plus numberless
`_FALLBACK_TEMPLATES` for the keys no catalog row covers:

| kind | narration shape |
| --- | --- |
| `resource_spend` | the cost paid, in effort imagery (`魔力自指間流瀉而出。`) — no amount |
| `trait_delta` | gauge-family line chosen from `data["trait_key"]` (`hp`/`mp`/`sp`) |
| `skill_practice` | growth imagery (`這一式在身體裡留下了痕跡。`) |
| `pleasure_gain` | band clause, plus the act's override and actor/participant voice |
| `sexual_counter` | counter-specific, role-aware clause (D8) |
| `sexual_transition` | event-name clause (`climax_ends` → afterglow line) |
| `roll` / `damage` / `heal` / `self_heal` | outcome clause only; the action clause lives on the first entry |
| `target_defeated` / `target_knocked_out` | defeat/knockout imagery |
| `buff_applied`, `self_buff_applied`, `buffs_cleansed`, `equipment_immune`, `skill_granted`, `grants_revoked`, `disguise_*`, `reveal_*`, `session_stamp`, `rite_*`, `divine_*`, `pleasure_peak`, `gauge_transfer`, `disengage_attempt`, `self_return_clear` | three variants each, tender-neutral or martial as the kind implies |
| `action_skipped`, `party_retreat`, `overwhelm_resolution`, `commanded_action` | combat prose pools; the overwhelm summary loses `{data[...]}` counts from prose and keeps them in `data` |

`world/rules/upkeep.py` builds its tick `damage` and `target_defeated` entries directly, so it
calls the same selector: `settle_upkeep` gains an optional `narration_scope` keyword that
`run_round` fills with the round's own scope, and defaults to `""` for the bounded encounters
that drive upkeep without a session.

Internal-only kinds that intentionally render `""` (`combat_kill_xp`, `knocked_out_mark`,
`divine_drain_actor`, `gauge_transfer_actor`, `damage_divert`) keep rendering `""`.

## D8. Sexual verdict and participant-role awareness

`sexual_resist` data classifies the verdict without new fields: `resisted` →
`resist`; not resisted and `auto_comply` → `auto_comply`; otherwise → `comply`. Act rows
author the *attempt* once (`悠花貼近悠奈，指尖帶著挑逗滑過她的頸側——`), so a comply
clause, a resist clause or an auto-comply clause completes the same sentence for every
verdict, and the act text never has to claim contact that did not happen.

Role awareness comes from facts the entry already carries:

- `entry.target == event_log.actor` selects the actor-voice clause for `pleasure_gain`
  (the caster's own gain) instead of the participant-voice clause;
- `sexual_counter` reads the act's `SexualActDef`: a counter in `actor_counters` narrates
  as something the performer did, a counter in `participant_counters` narrates as
  something both bodies recorded.

Per-act rows and the transition/pleasure/counter content land in
`narration-sexual-acts`; this change lands the classes, the shared clauses, and the
per-line act fallback so sexual output already reads as prose.

## D9. No ANSI or new markup for severity

Severity is lexical. `render_plain_text` is the canonical baseline the AI degradation
path reuses and the beats panel strips ANSI from; colouring severity would put a
presentation decision into the rules-layer string, change the prompt baseline, and add
nothing the words do not say. The `webclient-narrative-markup` allowlist and the
`raw`/`client_raw` prohibition are untouched because no new markup is emitted.

## D10. Structural prose stays a single authored line

The round marker (`CONTINUE_MESSAGE`), the terminal outcome announcements and the
engagement opening are rewritten once, not pooled per round. The client's beat playback
and the browser suites use the closing line to anchor where a round's beats end; a
per-round variant would make that anchor unpredictable for no story gain, since the
story is carried by the entries above it. The engagement opening gains the foe's name
(`你搶先一步，朝哥布林逼了上去。`) because the adapter already holds the monster.

## D11. Narration failures degrade, they never reject

Every lookup miss, band miss or unknown kind falls back (D2, D6). A narration fault must
not turn a legal cast into `EVENT_LOG_CONSTRUCTION_FAILED`: presentation is not a
correctness gate for resolution. The only fail-closed behavior is *authoring* validation
at import (D6), which happens at startup, not at cast time.

## D12. Exact-prose test update policy

Tests must not pin shipped prose. For each affected assertion:

| site | today | after |
| --- | --- | --- |
| `world/rules/tests/test_combat_result.py` | literal `行動完成，繼續戰鬥。` / victory line | compare against `CONTINUE_MESSAGE` / `terminal_outcome_message("victory")` |
| `commands/tests/test_combat_actions.py` | `"繼續戰鬥。" in message` | compare against the exported constant |
| `commands/tests/test_command_branch_behaviour.py` | patched literal victory line | patched constant |
| `world/rules/tests/test_combat_session_flow/test_attribution_seam_and_command_surface.py` | exact `… 的攻擊擲出了 44。` | assert the `roll` entry's `data["raw_roll"] == 44` and that the delivered line carries no digit |
| `world/rules/tests/test_freeform_casting/test_text_commands.py` | `… 恢復了` prefix | assert the heal entry's amount and that the line carries no digit |
| `world/quests/tests/test_integration.py` | `… 累積了技能熟練度。` | assert the quest planner ran and that a `skill_practice` entry exists |
| `web/tests/browser/{test_browser_combat_beats,test_browser_combat_choreography,test_browser_combat_stage}.py` | hardcoded closing line | import the same constant (no new browser class, so no browser-shard change) |
| `world/rules/tests/test_combat_beats.py`, `test_event_log.py` | hand-built templates | unchanged: they already pass their own templates |

Tests that need shipped content use the synthetic test-data kit or file-local fixtures;
the coverage contract slice is a `Data-contract test:` module registered in
`tools/test_data_freeze.json` because it must name the shipped key set.

## D13. Capabilities deliberately not given a delta

- **`skill-registry` / `sexual-act-registry`.** No row, field, key, order or effect changes;
  the narration catalog reads both registries and is validated against them. A `SkillDef` field
  was rejected in D1 for exactly this reason.
- **`sexual-transition-rulebook`.** No rule, event name or effect declaration changes. The
  narration catalog's transition coverage is derived from the act catalog at import (D8), so a
  new emitted event name fails there rather than needing a second list here.
- **`sexual-vocabulary`.** Severity and pleasure wording is narration vocabulary keyed by
  numeric bands, not a new ordered-level vocabulary; the canonical state level names are
  untouched and still read from `world/lore/sexual_vocab.py`.
- **`narrator` (AI).** `world/ai/narrator.py` stays unwired; its prompt payload only sees a
  different `text_template` value, which its existing bounds already handle.
- **`webclient-narrative-markup`.** No new markup or colour is emitted (D9), so the allowlist,
  the palette and the converted-stream prohibition are unchanged.

## Traceability

Every requirement in this change's delta specs gets one behavior test annotated with
`covers_requirement`, resolved from `python -m tools.spec_traceability list` at
implementation time:

| requirement | test module |
| --- | --- |
| `action-narration` catalog coverage / bounds / fallback / slots | `world/skills/tests/test_narration_catalog.py` (pure, synthetic rows) and `world/skills/tests/test_skill_registry/test_narration_coverage.py` (data contract over the shipped keys, tagged `Data-contract test:` and registered in `tools/test_data_freeze.json`) |
| `action-narration` deterministic selection / no RNG / no numbers / action line / mechanical pools / sexual verdict and role / structural prose / degrade-never-reject | `world/rules/tests/test_event_narration.py` (pure: seed, band, compose, compact degrade) and `world/rules/tests/test_event_narration_pipeline.py` (resolver integration, draw-count equality, effect-less skill) |
| `event-log` numberless text with exact payload, purity, internal-only kinds | `world/rules/tests/test_event_log.py` (extended) |
| `action-resolution-pipeline` step-7 narration contract, narration scope, planner view | `world/rules/tests/test_event_narration_pipeline.py` (extended) |
| `webclient-combat-beats` bound guarantee, unchanged cardinality, empty-log beat | `world/rules/tests/test_combat_beats.py` (extended) |
| structural copy reachable from both command and adapter paths | `world/rules/tests/test_combat_result.py` and `commands/tests/test_combat_actions.py` |

Test-cost registration: both new `world.rules.tests` modules are added to exactly one shard
(`rules-a`) in `.github/evennia-shards.json`; the new `world.skills.tests` module is already
covered by the existing `world.skills` package label, so the manifest gains no entry for it.
No browser test class or method is added, so `.github/browser-shards.json` is unchanged; the
three browser modules that hardcode the round-closing line import the constant instead.

## Risks / Trade-offs

- **Volume.** 157 non-sexual + 66 sexual rows by the end; this change ships ~20 family
  rows, the shared pools, and the structural copy (the rest is split across three
  one-day changes).
- **Registry row churn.** No `data_*.py` row is edited, so registry order is untouched;
  the catalog is additive.
- **Fail-closed import.** Adding an ACTIVE skill without a narration row (once its
  family is no longer pending) breaks server start by design. The exemption set is a
  frozen constant pinned by a test, so the failure is a named, intentional one.
- **Hand-built `SkillDef` test rows** need no new field (D1), but they resolve to family
  or generic fallbacks, so tests that assert on narration must use synthetic catalog
  rows.
- **Drift from recorded facts.** The prose is derived only from the entry's own
  `kind`/`data`/participant keys; the band is computed from the same numbers the entry
  records, and a narration test asserts that every rendered line's facts match the
  entry's data (e.g. a healing line never accompanies a damage entry).
- **Style consistency.** Lines are authored per family module with a shared register
  (JRPG sword-and-sorcery, zh-TW, no wuxia vocabulary); a lint-level check enforces the
  mechanical rules (bounds, no digits, placeholder allowlist), not taste.
- **This is the engine day.** The pools and family tiers are short clauses (about a hundred
  lines of content); the mechanical work is the catalog/validator/selector plus the test
  migrations. The content-volume risk is carried by changes 2–4, each of which is almost
  entirely authoring.
