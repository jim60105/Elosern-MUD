## Context

`SexualState` (`world/rules/sexual_state.py`) already exposes eleven lifetime counters
(`masturbation_count`, `toy_use_count`, `exposure_act_count`, `watched_count`, `duo_act_count`,
`group_act_count`, `hostile_act_count`, `restraint_count`, `interspecies_act_count`, `climax_count`,
`climax_extension_count`), the pleasure gauge, and climax settlement. `SKILL_REGISTRY`
(`world/skills/registry.py`) already carries `SkillCategory.SEXUAL_ACT` with a `group` (line) field,
consumed today by three pre-existing skills (`divine_sexual_arts`, `divine_sexual_mastery`,
`reincarnation_boon_yuna`). `SexualMasteryEffect` (`world/skills/effects.py`) has existed since the
skill-system redesign with no consumer.

This change is pure plumbing: it makes a `SkillDef` able to *be* a counter-gated act (the
`SexualActDef` sidecar), makes an entity's unlocked set queryable, and makes that set visible to
`ActionResolver` and the combat panel through the existing `owned_keys()` seam. It authors zero act
content. Its acceptance test is a single synthetic act proving the seam end-to-end, deleted or left
as a permanent fixture (the tasks.md will call this out explicitly) — the six catalog proposals
supply the real 62 acts against this exact contract without re-reading this module.

This document **is** the registry contract that the catalog proposals (`sexual-act-catalog`, split
across five per-line changes) and the divine line (`divine-sexual-arts`) are written against without
re-deriving it. Read [Sexual Act Resolution](../../../docs/superpowers/specs/2026-08-15-sexual-act-resolution-design.md)
§2 for the original rationale; this document is the authoritative, code-accurate version of that
section as landed.

## Goals / Non-Goals

**Goals:**
- Define `SexualActDef` and `SEXUAL_ACT_REGISTRY` with a stable, documented field contract.
- Ship the six-module package with pre-declared stubs so five catalog proposals and one divine-line
  proposal can each own exactly one file with zero cross-proposal conflict.
- Add `SexualState.unlocked_act_keys()`, including the `SexualMasteryEffect` blanket unlock.
- Extend `SkillHandler.owned_keys()` to include unlocked acts without creating an import cycle and
  without `world/skills/` depending on `world/rules/`.
- Prove the seam with one synthetic act and structural invariants, not real content.

**Non-Goals:**
- No act content (that is `sexual-act-catalog`'s five line proposals and `divine-sexual-arts`).
- No new effect prefix, no participant model, no body-part resolution (that is `sexual-act-effects`,
  this change's direct dependent — `SexualActDef` declares `actor_part`/`target_part` as data, but no
  code in this change reads them to apply anything).
- No resist contest (`sexual-resist-contest`/`sexual-resist-turn-cost`). `SexualActDef.resistible` is
  declared here as a field because the schema is this change's territory, but nothing in this change
  consults it.

## Decisions

### D-1: `SexualActDef` fields, and what each is for

```python
@dataclass(frozen=True)
class SexualActDef:
    key: str                              # matches the paired SkillDef.key exactly
    unlock: Mapping[str, int]             # counter attribute name -> threshold; ALL must be met; empty = seed
    base_pleasure: int                    # positive integer; pre-multiplier magnitude (sexual-act-effects reads this)
    actor_part: str | None                # a BODY_PARTS member, or None for a partless/multi-target-only act
    target_part: str | None               # a BODY_PARTS member, or None (required None for interspecies/divine acts)
    actor_pleasure_ratio: float           # share of base_pleasure applied to the actor; 0.0 only when exempt (D-6)
    actor_counters: tuple[str, ...]       # SexualState counter attribute names incremented on the actor
    participant_counters: tuple[str, ...] # SexualState counter attribute names incremented on every other participant
    sexual_events: tuple[str, ...]        # sexual.yaml event names this act emits, in emission order
    resistible: bool                      # consumed by sexual-resist-contest; not read by this change
```

`line` is deliberately **not** a field here. `SkillCategory` already carries a `group` for
`SEXUAL_ACT`-categorised skills (skill-category-registry's own requirement), and `_act_family()`
(D-2) sets it once per family exactly as `_elemental_spells()` sets `group=element` once per element.
Storing the line twice would create two sources of truth for the same fact; any consumer that needs
an act's line reads `SKILL_REGISTRY[key].group`.

`unlock` is frozen at construction (`__post_init__` copies it into a `MappingProxyType`): the
dataclass's `frozen=True` only blocks field reassignment, so without the proxy a consumer holding
the caller's original mapping (or the field itself) could rewrite a registered act's unlock
thresholds at runtime — the exact immutability the registry convention demands.

`unlock` and the two counter tuples name **`SexualState` attribute names**
(`masturbation_count`, not `自慰次數`). The design-document catalog tables use the Traditional
Chinese counter names as human-readable labels; the canonical mapping from those labels to attribute
names is:

| Design-doc label | `SexualState` attribute |
|---|---|
| 自慰次數 | `masturbation_count` |
| 玩具使用次數 | `toy_use_count` |
| 露出次數 | `exposure_act_count` |
| 被觀看次數 | `watched_count` |
| 雙人行為次數 | `duo_act_count` |
| 多人行為次數 | `group_act_count` |
| 對敵行為次數 | `hostile_act_count` |
| 忍耐次數 | `restraint_count` |
| 異種行為次數 | `interspecies_act_count` |
| 高潮次數 | `climax_count` |
| 連續高潮次數 | `climax_extension_count` |

Every catalog proposal writes `unlock` and the counter tuples using the right-hand column only.

### D-2: `_act_family()` shape

Mirrors `_elemental_spells()` (`world/skills/registry.py`) exactly: the line, tier commentary, and
any row-shared defaults are written once, and each row is a tuple.

```python
def _act_family(
    line: str,
    *rows: tuple[
        str,                    # key
        str,                    # label
        str,                    # description
        TargetSpec,
        Mapping[str, int],      # unlock
        int,                    # base_pleasure
        str | None,             # actor_part
        str | None,             # target_part
        float,                  # actor_pleasure_ratio
        tuple[str, ...],        # actor_counters
        tuple[str, ...],        # participant_counters
        tuple[str, ...],        # sexual_events
        bool,                   # resistible
    ],
    requires_divine_arts: bool = False,
) -> tuple[tuple[SkillDef, SexualActDef], ...]:
```

`_act_family()` takes exactly **one** line-identifying parameter, `line`, mirroring
`_elemental_spells(element, *spells)`'s single-parameter shape exactly — an earlier draft of this
document introduced a second, redundant `category_group` parameter with no defined relationship to
`line`, and a stray second `*` before `requires_divine_arts`, which is a `SyntaxError` (`*rows`
already makes every following parameter keyword-only; a second bare `*` is invalid, not merely
redundant). Both are corrected above. `requires_divine_arts` is a keyword-or-positional argument
after `*rows` and therefore implicitly keyword-only already — callers SHALL pass it by keyword
(`requires_divine_arts=True`) for readability, though the signature does not enforce that stylistic
choice beyond what `*rows` already forces.

For each row it constructs the paired `SkillDef` (category `SEXUAL_ACT`, `group=line`,
`kind=SkillKind.ACTIVE`, `cost={}` — sex acts are the one confirmed zero-resource-consumption action
class per the system's own premise, `usable_out_of_combat=True`, `effects=[]` until
`sexual-act-effects` adds the `pleasure:`/`sexual_counter:` prefixes) and the `SexualActDef`, then
runs the six per-row structural checks (D-6) before returning the pair. A catalog module calls
`_act_family()` once per line and exports the flattened result; `__init__.py` merges every module's
export into `SKILL_REGISTRY` and `SEXUAL_ACT_REGISTRY`.

`effects=[]` is a deliberate, temporary gap: every act built by `_act_family()` in this change ships
with an empty `effects` list, because `pleasure:`/`sexual_counter:` do not exist yet — declaring a
string with either prefix would make `SkillDef.__post_init__`'s `parse_effect` call raise
`ValueError` at import time, since only `sexual-act-effects` (this change's dependent) adds those
prefixes to the dispatch table. An empty `effects` list is fully valid and fully castable:
`_step5_effect_resolution` (`action.py`) simply does not iterate, so a cast against an
`effects=[]` skill resolves to zero pending effects and commits as a trivial success — the same shape
a still-unmechanized `divine_mystery` entry's handler already produces by returning `[]`. This is
sufficient to prove the ownership/unlock/`ActionResolver` round trip this change is responsible for
(§ Acceptance proof, below) without needing any real effect to exist yet.

### D-3: Package layout and the pre-stub rule

```
world/skills/sexual_acts/
    __init__.py          assembles SEXUAL_ACT_REGISTRY, registers every SkillDef into SKILL_REGISTRY
    _builder.py           SexualActDef, _act_family(), the five per-row structural checks
    solo.py               獨處線 — exports SOLO_ACTS: tuple[tuple[SkillDef, SexualActDef], ...] = ()
    shame.py              羞恥線 — exports SHAME_ACTS = ()
    partner.py             關係線 — exports PARTNER_ACTS = ()
    combat.py              戰鬥線 — exports COMBAT_ACTS = ()
    interspecies.py        異種線 — exports INTERSPECIES_ACTS = ()
    divine.py               神之秘法線 — exports DIVINE_ACTS = ()
    tests/
        test_registry_structure.py   the whole-registry invariants (D-6)
```

Every module above ships in **this** change, already imported by `__init__.py`, each exporting an
empty tuple with the exact name given. A catalog proposal's entire diff against this change is: fill
its one module's tuple, nothing else. `combat.py` here is the 戰鬥線 act module, distinct from
`world/rules/combat.py`; the two are unambiguous by full path but the name collision is flagged here
so no future reader mistakes one import for the other.

Assembly (`__init__.py`) goes through the `_register_rows()` helper, which fails closed on three
shapes of row defect before writing anything: the `SkillDef` key disagrees with the `SexualActDef`
key, the key is already registered in `SEXUAL_ACT_REGISTRY` (duplicate), or the key collides with an
existing `SKILL_REGISTRY` entry — a catalogue row must never silently overwrite a pre-existing
skill definition like `basic_attack`.

### D-4: `unlocked_act_keys()` and the mastery blanket unlock

The unlock rules live in ONE implementation, the pure function
`unlocked_act_keys_for(owned_keys, counter_values)` in
`world/skills/sexual_acts/__init__.py`, so the materialized `SexualState`
query and the no-create `owned_keys()` read (D-5) can never drift:

```python
# world/skills/sexual_acts/__init__.py
def unlocked_act_keys_for(
    owned_keys: Iterable[str],
    counter_values: Mapping[str, int],
) -> frozenset[str]:
    mastery = any(
        isinstance(effect, SexualMasteryEffect)
        for key in owned_keys
        if key in SKILL_REGISTRY
        for effect in SKILL_REGISTRY[key].parsed_effects
    )
    if mastery:
        return frozenset(SEXUAL_ACT_REGISTRY)
    return frozenset(
        key
        for key, act in SEXUAL_ACT_REGISTRY.items()
        if all(
            counter_values.get(counter, 0) >= threshold
            for counter, threshold in act.unlock.items()
        )
    )

# world/rules/sexual_state.py, added to SexualState
def unlocked_act_keys(self) -> frozenset[str]:
    from world.skills.sexual_acts import unlocked_act_keys_for
    return unlocked_act_keys_for(
        self._entity.skills.base_owned_keys(),
        {name: getattr(self, name) for name in _LIFETIME_COUNTER_KEYS},
    )
```

`counter_values` may omit names: an omitted counter reads as zero, which is
exactly an unmaterialized entity's state (D-5).

The `if key in SKILL_REGISTRY` clause **must** appear immediately after the first
`for`, before the second `for` dereferences `SKILL_REGISTRY[key]` — generator-expression
clauses execute in the order written, so placing the guard last (as an earlier draft of this
document did) evaluates `SKILL_REGISTRY[key]` before the guard has run, raising `KeyError` for any
key absent from `SKILL_REGISTRY`. This is not a hypothetical: `base_owned_keys()` always appends
`INNATE_SKILL_ORDER`, which includes `"flee"`, and `"flee"` is registered into `SKILL_REGISTRY` only
as an import-time side effect of `world/rules/disengage.py` — a module `unlocked_act_keys()`'s own
call sites do not necessarily import first. The guard is therefore load-bearing, not defensive
decoration; a test asserting `unlocked_act_keys()` does not raise for an entity whose
`base_owned_keys()` includes a key absent from `SKILL_REGISTRY` (see tasks.md) exists specifically to
pin this.

`unlocked_act_keys_for` imports `SexualMasteryEffect` and `SKILL_REGISTRY` from `world.skills` only
— the catalogue package already depends on both, so no new dependency edge exists. Neither
`world/skills/sexual_acts/_builder.py` nor `__init__.py` imports `world.rules.sexual_state` at
production import time — D-6's counter/event cross-check runs in `tests/test_registry_structure.py`,
not in either production module — so a top-level import there would not, in fact, cycle today. The
`SexualState` method defers its import of the catalogue package anyway, defensively: it keeps
`sexual_state.py`'s existing top-level imports untouched, keeps this the only method in the module
reaching outside its own package, and mirrors the precedent `SexualState.__init__` already sets by
deferring `from typeclasses.monsters import Monster` — a habit worth keeping even where no cycle is
currently provable, since it costs nothing and remains correct if a future change ever does
introduce one.

The ownership read passes `entity.skills.base_owned_keys()` — the **pre-extension** set (D-5) —
never `owned_keys()`, matching `can_cast_spell_tier`'s existing, load-bearing discipline: "conferred
grants never satisfy the mastery override... only `entity.skills.owned_keys()` counts, never
`conferred_grants()`" (progression.py docstring). Reading the extended `owned_keys()` here would
recurse; passing `conferred_grants()` would let `dominion_art` (統御術) unlock the whole catalogue
for a recipient of a fractional 性魔法主宰 grant, which the resolution design doc explicitly forbids.

### D-5: `base_owned_keys()`, `owned_keys()`, and the no-create gate

```python
# world/skills/handler.py
class SkillHandler:
    def base_owned_keys(self) -> list[str]:
        """Return exactly what owned_keys() returned before this change."""
        return [
            *self._raw.get("active", []),
            *self._raw.get("passive", []),
            *INNATE_SKILL_ORDER,
        ]

    def owned_keys(self) -> list[str]:
        base = self.base_owned_keys()
        if not self._sexual_state_materialized():
            return [*base, *sorted(self._unlocked_act_keys_without_sexual())]
        sexual = getattr(self.entity, "sexual", None)
        if sexual is None:
            return [*base, *sorted(self._unlocked_act_keys_without_sexual())]
        return [*base, *sorted(sexual.unlocked_act_keys())]
```

`getattr(self.entity, "sexual", None)` — never `from world.rules.sexual_state import SexualState` —
is what keeps `world/skills/handler.py` free of any `world.rules` import, preserving
`universal-action-ownership`'s existing "world/skills/ does not depend on world/rules/" requirement
and its own scenario, which inspects this file's import statements directly.

**The no-create gate is an amendment over the earlier draft of this document**, which had
`owned_keys()` call `getattr(self.entity, "sexual", None)` unconditionally. `entity.sexual` is a
lazily mounting property: the first read creates the handler's persistent `sexual_traits`
attribute. `owned_keys()` is invoked by `action_preview._skill_wide_failure()` and by the
`skill_owned` rule condition in `evaluate_condition()` — both of which run inside
`action-resolution-pipeline`'s side-effect-free preview and `webclient-status-presentation`'s
no-create status reads, whose live main-spec requirements forbid materializing the handler.
`_sexual_state_materialized()` therefore probes the storage marker
(`entity.attributes.get("sexual_traits", ..., category="traits")` — the same attribute the
no-create read paths check) before touching the property, and `_unlocked_act_keys_without_sexual()`
computes the unlocked set purely from registry data: an unmaterialized entity's counters are all at
their zero baseline, so the query sees the seed acts (empty `unlock`) — or the whole catalogue for a
directly owned mastery skill — through `unlocked_act_keys_for()` (D-4) without creating state. The
`None` branch stays for a bare test double with no `sexual` attribute at all.

`unlocked` is sorted for determinism: `frozenset` iteration order is not guaranteed, and
`owned_keys()`'s ordering feeds the combat panel and `_step1_ownership`'s membership test — the
latter is order-independent, but the former is not, and an unstable order would make snapshot-style
UI tests flaky. Sorting by key (not by unlock difficulty or catalog order) is the simplest option
that is fully deterministic without inventing a display-order concept that belongs to the combat
panel, not to this seam. A later act-ordering proposal, if wanted, would layer on top of this without
changing the contract.

### D-6: The structural invariants, and where each lives

Per-row (checked inside `_act_family()`, at import time, using both the `SkillDef` and
`SexualActDef` it just built — raises `ValueError` naming the offending key):

1. `actor_pleasure_ratio > 0`, unless `requires_divine_arts` is `True` for the family. The ratio
   must additionally be finite for every family — `NaN` and infinity are not "strictly positive",
   and a non-finite ratio would poison every later pleasure computation that multiplies by it.
2. `actor_part != GENERIC_BODY_PART and target_part != GENERIC_BODY_PART`.
3. If `line` is `"異種"` or `"神之秘法"`, `target_part is None`.
4. Every non-`None` part is a `BODY_PARTS` member.
5. `base_pleasure > 0`; `resistible` is a bare `bool`.
6. `unlock` is a mapping of string counter-attribute names to non-`bool` integer thresholds — a
   threshold written as a float, string, or `bool` would misbehave inside the unlock query, so it
   fails closed at construction rather than at play time.

Whole-registry (checked in `tests/test_registry_structure.py`, which runs
`world.skills.sexual_acts.SEXUAL_ACT_REGISTRY` and `world.skills.registry.SKILL_REGISTRY` against
each other, and against `world.rules.rulebook.schema.load_rules` on `sexual.yaml`):

7. Every name in `unlock`, `actor_counters`, and `participant_counters` is one of the eleven
   `SexualState` counter attributes (D-1's table, right-hand column).
8. Every string in `sexual_events` is a value some `sexual.yaml` rule's `when["event"]` carries
   (`{rule.when["event"] for rule in load_rules(SEXUAL_YAML_PATH) if "event" in rule.when}`).
9. `set(SEXUAL_ACT_REGISTRY)` equals `{k for k, v in SKILL_REGISTRY.items() if v.category is
   SkillCategory.SEXUAL_ACT} - {"divine_sexual_arts", "divine_sexual_mastery",
   "reincarnation_boon_yuna"}` — the three named exclusions are the pre-existing mastery/mystery
   skills that carry no `SexualActDef` by design (they are acquisition-path skills, not acts).

Whole-registry checks are test-time, not import-time, because they need the fully assembled
`SKILL_REGISTRY` and a parsed `sexual.yaml`, neither of which is guaranteed complete while any one
module is still being imported — exactly the reasoning `sexual.yaml`'s own
`test_every_rule_id_has_a_test()` and `test_field_kinds_covers_every_targetable_field()` already
follow for the same class of whole-table property.

### D-7: The acceptance proof is test-local, never committed to a line module

This change's acceptance test constructs one `SexualActDef`/`SkillDef` pair directly inside the test
module by calling `_act_family()` with a single row (`effects=[]`, a nonzero `unlock` threshold on an
otherwise-unused counter), and installs it into `SEXUAL_ACT_REGISTRY`/`SKILL_REGISTRY` for the
duration of the test only (`unittest.mock.patch.dict` around both module-level dicts), removing it on
teardown. It is never written into `solo.py` or any other line module. This avoids a task shape where
production content is added and then must be remembered and reverted before archive — the module
state that ships is `SOLO_ACTS = ()` and friends, unconditionally, from the first commit onward.

## Risks / Trade-offs

- **[Risk]** A catalog proposal declares a counter name using the Chinese label instead of the
  attribute name (e.g. `"自慰次數"` instead of `"masturbation_count"`), which invariant 6 catches only
  at test time, not at the point the mistake is made. → **Mitigation**: invariant 6's failure message
  names the exact offending string and the act key; the D-1 mapping table is the single place every
  catalog proposal's author needs to check.
- **[Risk]** `effects=[]` on every real act until `sexual-act-effects` lands means this change alone
  ships zero player-visible capability, and the six-batch parallel catalog work (batch 6 in the
  overview document) produces acts that cannot yet be cast. → **Mitigation**: this is intentional
  sequencing (`sexual-act-effects` depends on this change; the catalog proposals depend on both), not
  an oversight — `tasks.md` calls out that `effects=[]` is expected and correct for every act this
  change and the catalog proposals add, until `sexual-act-effects` is implemented.
- **[Risk]** `base_owned_keys()` duplicates `owned_keys()`'s current body almost verbatim, so the two
  functions could silently drift if one is edited without the other. → **Mitigation**: a dedicated
  test asserts `owned_keys()` for an entity with zero unlocked acts returns exactly
  `base_owned_keys()`'s value, so drift fails loudly rather than silently.

## Migration Plan

Additive only. No existing `SkillDef`, no existing `SexualState` field, and no existing
`owned_keys()` return value changes for any entity with zero unlocked acts (every entity, until a
later proposal ships real act content). No data migration; no `entity.db` shape changes.

## Open Questions

None outstanding — every open design question from the source document set (line naming, the
mastery-unlock recursion, the pre-stub package shape) was resolved during design review and is
recorded as a decision above.
