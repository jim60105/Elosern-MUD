## Context

Current shape (`master`, `elementless-damage-effect` already merged and archived —
`openspec/changes/archive/2026-09-19-elementless-damage-effect/`; the `none`-token handling below is
today's live behavior, not a future state):

`world/skills/effects.py::parse_effect`'s `damage` branch (`world/skills/effects.py:1125-1132`):
```python
if prefix == "damage":
    _, _, rest = effect_id.partition(":")
    element, _, school = rest.partition(":")
    if not element or not school or ":" in school:
        raise ValueError(
            f"damage effect must be damage:<element>:<school>, got {effect_id!r}"
        )
    return DamageEffect(element=None if element == "none" else element, school=school)
```

`world/rules/combat.py::_parse_damage_effect` (independent re-implementation, `world/rules/combat.py:273-284`):
```python
def _parse_damage_effect(effect_id: str) -> tuple[str, str]:
    parts = effect_id.split(":")
    if len(parts) != 3 or parts[0] != "damage":
        raise ValueError("damage effect must be damage:<element>:<school>")
    _, element, school = parts
    if element != "none" and element not in ELEMENT_REGISTRY:
        raise ValueError(f"unknown damage element {element!r}")
    if school not in {"physical", "magic"}:
        raise ValueError(f"unknown damage school {school!r}")
    return element, school
```
Called from `_handle_damage` (`_, school = _parse_damage_effect(effect_id)`, `world/rules/combat.py:338`)
and from `world/rules/monster_behaviour.py::_damage_school`
(`_, school = combat._parse_damage_effect(effect)`, `world/rules/monster_behaviour.py:176`). Both
callers discard `element` immediately — only `school` is ever used. Note the two functions' `none`
exemptions are already textually different (`element=None if element == "none" else element` vs.
`element != "none" and element not in ELEMENT_REGISTRY`) — both correct today, but two independent
places a future edit to one could drift from the other without touching both, which is exactly the
duplication this change removes.

The same file already has the fix pattern for a different prefix, `world/rules/combat.py:628`:
```python
def _parse_self_heal_effect(effect_id: str) -> SelfHealEffect:
    parsed = parse_effect(effect_id)
    if not isinstance(parsed, SelfHealEffect):
        raise ValueError(f"expected self_heal effect, got {effect_id!r}")
    return parsed
```
`_parse_damage_effect` predates this pattern (or was never migrated to it) and is the one prefix
handler in `world/rules/combat.py` that still hand-rolls its own grammar instead of delegating.

## Goals / Non-Goals

**Goals:**
- One function (`parse_effect`) owns the `damage:<element>:<school>` string grammar. Every other
  consumer reads its typed result.
- Preserve every currently-observable behavior for currently-valid content: no shipped or synthetic
  skill's construction or cast resolution changes.
- Close the one validation-timing gap this consolidation exposes for free: a malformed school now
  fails at registry load (like every other malformed effect prefix) instead of silently constructing
  and only failing the first time it is cast.

**Non-Goals:**
- Validating the element segment against `ELEMENT_REGISTRY` inside `parse_effect` (registry-load
  time). Rejected for the same reason `elementless-damage-effect`'s design.md D2 rejected it: a broad
  set of test fixtures deliberately author non-registry element tokens (`damage:t_dummy:physical`,
  `damage:nope:magic`, etc.) that exist purely to exercise `parse_effect`'s shape-parsing and must
  keep constructing. That check stays a cast-time-only concern, layered on top of `parse_effect`'s
  result by the thin wrapper, exactly where it lives today.
- Threading an already-parsed `DamageEffect` through the generic effect-dispatch mechanism
  (`register_effect_handler`) to avoid re-parsing the string at cast time at all. Every prefix handler
  reachable through that dispatch table receives only the raw `effect_id: str` (see
  `_parse_self_heal_effect`'s identical constraint); reworking that generic signature to carry a typed
  payload is a materially larger, cross-cutting change with no bearing on the duplication this change
  fixes, and is explicitly out of scope.
- Any settlement, targeting, policy, or modifier behavior. This is a parsing-layer consolidation only.

## Decisions

**D1 — `_parse_damage_effect` becomes a thin wrapper around `parse_effect`, not a deletion.** The
function name and both call sites stay; only its body and return type change:
```python
def _parse_damage_effect(effect_id: str) -> DamageEffect:
    """Parse and fully validate one damage effect for cast-time resolution.

    Delegates grammar parsing to the canonical `parse_effect` (the
    registry-load-time parser) instead of re-splitting the string, and adds
    the one cast-time-only check `parse_effect` deliberately excludes: a
    non-`None` element must be a real `ELEMENT_REGISTRY` key. `None` (the
    elementless sentinel) is always legal and is never checked against the
    registry.
    """
    parsed = parse_effect(effect_id)
    if not isinstance(parsed, DamageEffect):
        raise ValueError(f"expected damage effect, got {effect_id!r}")
    if parsed.element is not None and parsed.element not in ELEMENT_REGISTRY:
        raise ValueError(f"unknown damage element {parsed.element!r}")
    return parsed
```
Alternative considered: delete `_parse_damage_effect` entirely and inline `parse_effect(effect_id)` at
both call sites, each adding its own `isinstance`/element check. Rejected — that duplicates the
element-registry check across two call sites instead of one, re-creating a smaller version of the
exact problem this change fixes. Keeping one named wrapper function (matching `_parse_self_heal_effect`'s
established shape) is the same amount of code and gives future readers one place to look.

**D2 — Return type changes from `tuple[str, str]` to `DamageEffect`.** Both call sites currently
discard the element (`_, school = ...`); changing the return shape to the typed dataclass costs one
attribute-access edit at each site (`.school` instead of unpacking) and matches how every other parsed
effect in the codebase is already consumed. Keeping the old tuple shape and only changing the internals
was considered and rejected: it would hide the fact that the wrapper is now typed under the hood, and
would require constructing a fresh `(element, school)` tuple from the dataclass for no reason.

**D3 — School validation moves into `parse_effect`; element validation does not.** These are treated
asymmetrically on purpose, and the asymmetry is the crux of this design:
- School is a closed, cheap, two-value set (`{"physical", "magic"}`) with zero known fixtures
  currently authoring a third value in a position expected to construct successfully (verified by a
  repo-wide grep of every `damage:` string; every non-`physical`/`magic` school segment found belongs
  to a test that already expects `ValueError`). Moving this check to registry-load time is free and
  strictly earlier-failing.
- Element validation against `ELEMENT_REGISTRY` has real, known fixture debt (the 217+ sites
  `elementless-damage-effect`'s design.md counts) that intentionally construct with non-registry
  element strings. Moving that check to registry-load time would break those fixtures; it is
  `elementless-damage-effect` D2's explicitly out-of-scope "separate, larger cleanup," and stays out
  of scope here too. The asymmetry is not an oversight — it is the same line already drawn by the
  sibling change, applied consistently.

**D4 — No sequencing dependency; implement directly against current `master`.**
`elementless-damage-effect` has already merged and archived, so this change's `_parse_damage_effect`
wrapper (D1) inherits `None`-legality for free from `parse_effect`'s already-`None`-aware damage
branch — there is nothing to wait for and nothing to re-derive. The earlier draft of this design
assumed `elementless-damage-effect` was still in flight and sequenced this change after it; that
assumption is now moot (verified against the live worktree: both functions already contain the
`none`-token handling shown in Context above) and is recorded here only so a reader of this history
understands why D1–D3 already talk about `None` as an existing case rather than a hypothetical one.

## Risks / Trade-offs

- **Call-site churn at two sites.** `_handle_damage` and `_damage_school` each change one line
  (`_, school = _parse_damage_effect(effect_id)` → `school = _parse_damage_effect(effect_id).school`).
  Mitigated by the focused regression suite in tasks.md exercising both paths (a real cast through
  `_handle_damage`, and a monster's skill-scoring path through `_damage_school`).
- **The new registry-load-time school rejection could theoretically break an undiscovered fixture,
  including one built by string concatenation or an f-string rather than a literal.** A repo-wide grep
  for literal `"damage:..."` strings found none; a follow-up grep for `f"damage:` / `.format(`
  construction found several f-string-built damage effects, but in every one the school segment is a
  hardcoded literal (`:physical"` / `:magic"`) and only the element segment is interpolated, so none is
  at risk from this specific check. Task 0.1 extends the sweep to cover both patterns so a future
  contributor adding a dynamically-constructed school segment is caught before this ships, not after.
  Re-verified by running the full focused test list in tasks.md, which imports `SKILL_REGISTRY` and
  every synthetic fixture module that constructs a `damage:` skill.
