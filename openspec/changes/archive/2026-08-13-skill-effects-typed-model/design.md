## Context

`docs/superpowers/specs/2026-08-12-skill-system-redesign-design.md` §3.1 and D1 are the source of
truth for this change; read them first. Today, `SkillDef.effects: list[str]` is opaque by convention:
`world/skills/handler.py`'s `_parse_stat_multiply` recognizes only `stat_multiply:`; `world/rules/
action.py`'s `_EFFECT_HANDLERS` recognizes only the six prefixes registered via
`register_effect_handler`. Any other prefix — six of them exist in the registry today, covering 18
skills — is accepted by the registry with no validation and does nothing anywhere.

## Goals / Non-Goals

**Goals:**
- Make every effect-ID prefix the registry declares parse into a known, typed representation.
- Make an unrecognized prefix a load-time failure, not a silent no-op.
- Preserve `effective_value`'s existing multiplier math and public behavior exactly (no test in
  `skill-handler`'s existing scenario suite should need to change its assertions).
- Give every later skill-system-redesign proposal one shared place to add its effect class instead of
  re-implementing string parsing per module.

**Non-Goals:**
- This change does not add any new consumer behavior — no new combat mechanics, no new castable
  skills, no rule-table rows. It is pure infrastructure: parsing and validation only. `movement`,
  `weapon_style`, `passive_buff`, `passive_trait`, `combat_prediction`, `element_mastery_rank` gain a
  typed *representation* here but remain behaviorally inert until their respective consumer proposals
  land (this is intentional — see the dependent-changes list in `proposal.md`'s Impact section).
- Does not touch `action.py`'s `_EFFECT_HANDLERS` registration mechanism itself (cast-time dispatch by
  prefix string) — only what feeds it.
- Does not implement the `heal` prefix (no such prefix exists in the current registry; it is
  introduced by the sibling `heal-effect-handler` change, which depends on this one).

## Decisions

- **One dataclass per prefix, not one generic `Effect(prefix, args)`.** A generic bag-of-args class
  would just move the stringly-typed problem one layer down (every consumer would still need to know
  which positional args mean what). Per-prefix dataclasses make each consumer's dependency explicit at
  the type level: `world/skills/handler.py` imports `StatMultiplyEffect` specifically, not `Effect`.
- **`parse_effect` is a single pure function returning a tagged-union-shaped result** (one dataclass
  type per prefix), not a class hierarchy with a shared base requiring `isinstance` dispatch beyond
  what `match`/`isinstance` naturally gives Python 3.13 callers. Consumers use structural pattern
  matching (`match effect: case StatMultiplyEffect(...):`) rather than a visitor pattern — matches the
  project's existing style (no visitor patterns elsewhere in `world/rules/`).
- **`passive_trait` (e.g. `elf_longevity`) becomes `FlavorEffect`, explicitly declared inert.** This is
  a deliberate category (D1's "flavor with no mechanical effect is a legitimate declared category"),
  distinct from an *unrecognized* prefix. `parse_effect` accepts it; nothing ever consumes it.
- **`growth_rate` is a recognized read-time prefix, not an unknown one.** The registry already
  declares `reincarnation_boon_elosia` with `effects=["growth_rate:magic:100"]`, consumed by
  `world/rules/progression.py`'s `_self_magic_growth_multiplier`. It therefore gets
  `GrowthRateEffect(stat, multiplier)` (a `StatMultiplyEffect`-shaped pair) in this change — the
  "unknown prefix raises" guarantee and the "every existing registry entry still parses" scenario
  would otherwise contradict each other on this one existing entry. `progression.py` itself is not
  migrated here (it reads raw strings); only the typed representation is introduced.
- **`ElementMasteryEffect` stores the rank segment, not an element key.** The shipped mastery
  entries declare `effects=["element_mastery_rank:主宰"]` and the sibling
  `element-mastery-cast-gate` change keeps that exact string; the skill's element already lives in
  `SkillDef.element`. The parent design doc's `ElementMasteryEffect(element)` signature is
  explicitly amended here: the parsed field is `rank` (`ElementMasteryEffect(rank="主宰")`). This
  does not conflict with any sibling change — none of them read the field (the cast gate keys off
  owned skill keys, per D4).
- **`body_enhancement*` reclassification lands in this change, not a separate one**, because it is a
  three-line diff (the `kind=` argument) directly adjacent to the typed-effect work on the same skills,
  and separating it would create a dependency edge for no isolation benefit.
- **Cost tiers as constants, not a function**, since the design doc's tier table (§4.3) is a fixed,
  reviewed lookup table (band → MP range), not a formula — a `dict`/`NamedTuple` keyed by tier name is
  simpler and more auditable than a computed curve.

## Risks / Trade-offs

- [Risk] Reclassifying `body_enhancement*` to `PASSIVE` could break a test or UI surface that assumes
  it's castable. → Mitigation: grep test suite and `game-command-docs`/webclient skill-menu surfaces for
  the three keys before merging; task list includes an explicit search step.
- [Risk] Registry-load-time validation means a future content typo in an effect string breaks server
  startup instead of degrading gracefully. → Mitigation: this is the explicit intent (D1) — a loud
  startup failure is strictly better than an 18-skills-silently-dead regression, and this is a
  single-player local server where startup failures are immediately visible to the one operator.
- [Risk] `growth_rate` is parsed twice: once here into `GrowthRateEffect`, and once by
  `world/rules/progression.py`'s `_self_magic_growth_multiplier` (raw-string `startswith`/`float`
  reads). The two parsers could drift if a later change rebalances the growth-rate grammar. →
  Mitigation: deferred deliberately — the parent design §3.1 names only `handler.py` and (under
  later changes) `combat_modifiers.py` for consumer migration, and `progression.py` is outside this
  change's Impact list. Any future grammar change owns updating `progression.py` (its sole
  consumer); a dedicated consumer-migration follow-up can fold it in.
- [Note] At main-spec sync time, the `skill-handler` spec's `effective_value` wording ("every
  currently-owned active skill's matching `stat_multiply` effect") should be widened to "owned
  active or passive skill", since this change extends the read to both ownership buckets.

## Migration Plan

No runtime data migration — `entity.db.skills` storage format (`{"active": [...], "passive": [...]}`)
is unchanged; only the in-memory `SKILL_REGISTRY` definitions and their parsing move. Land in this
order relative to the rest of the skill-system-redesign batch: **first**, before any of the eight
`spell-catalog-*` changes or the other seven mechanism changes, all of which import from
`world/skills/effects.py`.

## Open Questions

None — scope is fully bounded by the approved design doc.
