# Design

## Context

See `proposal.md` — Why for the motivation. The shipped contracts this change has to fit:

- The race fact belongs to a **lore registry**. `RaceProfile` (`world/lore/races.py:30-43`) is a
  frozen dataclass already carrying race facts (`can_use_divine_arts`), and `RACE_REGISTRY`
  (`:106-139`) holds the three entries. `world/lore/` must not import `world/rules/`
  (AGENTS.md; `world/rules/character_creation.py:825-833` records the same constraint for the
  persona length cap), so a rule the lore-side validators must also apply has to be *data* in lore
  plus a reader in each layer, never a lore import of rules.
- One creation sex validator exists on the player side. `preflight_character_creation` resolves
  `sex` in the same mode branch as the identity fields (`world/rules/character_creation.py:419-436`)
  and normalizes it through `_validate_sex` (`:285-302`) for **both** modes (`:480`); a preset-mode
  request never sets `sex`, so `sex = preset.sex` (`:431`), and a custom-mode `None` becomes
  `DEFAULT_SEX`. The race key is proven to resolve at `:458-464` (`resolve_starting_profile` in
  custom mode, `resolve_preset_values` in preset mode), so a race-aware validator placed at `:480`
  can index `RACE_REGISTRY[race_key]` safely.
- The Telnet wizard never collects a sex; it persists the preflight-normalized member
  (`world/rules/creation_wizard.py:664-668`). Rejecting `None` for an elf would make elf creation
  impossible from that path.
- The WebClient passes `sex` through as a bounded string (`web/webclient/actions/creation_actions.py:194-199`)
  and the creation adapter maps any `CharacterCreationError` to `{outcome: rejected, code, message}`
  through `world/rules/creation_messages.py:89-110`. The SPA omits `sex` only while the select holds
  its default (`use-creation-custom.js:195`, `use-creation-form.js:71`) and re-selects the value the
  draft returns (`use-creation-form.js:160`); the overlay renders a rejected result's `message` in
  `creation-result-message` (`CreationOverlay.vue:143-147`). The name roll is different:
  `creation.roll_name` always sends the displayed member, `"other"` included.
- **NPC side.** `docs/development/adding-npcs.md:14-30` enumerates the five official NPC creation
  paths. Their identity writers are: `world/imports/loader.py::_instantiate_validated_character`
  (`:234-236`), `world/rules/guild_economy.py::sync_service_content` (`:200-202`), the shared
  `world/quests/materializer.py::spawn_role_actor` (`:272`) that both the stage scene builder and
  the published-encounter activation call, and
  `world/rules/starting_companions.py::build_starting_companion` (`:165-167`). None of the
  quest/AI modules mentions `sex` (`world/ai/scenario_director/prompt.py:82-85` only comments on
  the empty sex string it passes for name inspiration), so every elf NPC created today — including
  dream-generated scene and encounter characters — keeps `LivingEntity.sex`'s `"other"` default
  (`typeclasses/entities.py:29`, `DEFAULT_SEX`). The sibling precedent for a canonical identity
  default on these same paths is `ensure_npc_canonical_age` (`typeclasses/npcs.py:20-23`, called by
  `guild_economy.py:177,206`, `starting_companions.py:231`).
- Import validation splits structure from semantics: `CHARACTER_SCHEMA_V1` owns shape/enum
  (`world/imports/schema.py:103`), race-resolved rules live in `validate.py`
  (`_check_race_subrace` `:272-293`, `_check_affinity_elements` `:375-424`), and `load_batch`
  validates the whole batch before opening its transaction (`loader.py:298-302`).
- Authored data validates at registry load: `world/lore/settlements/places.py`
  (`validate_place_registry`, `:319-328`) already rejects a `host_sex` outside `SEX_VALUES`, and
  `world/lore/player_presets/validation.py::_validate_preset_sex` (`:249-261`) runs inside the
  package's import-time validator chain (`__init__.py:114-126`), after the identity validator that
  proves the race resolves.
- The test-data kit builds synthetic races with `dataclasses.replace` and enforces the reserved
  `t_` key prefix (`world/tests/synthetic_data/factories.py:138-141,254-261`), and behavior tests
  may not name shipped catalog symbols or tokens (`tools/test_data_lint.py`, exemptions in
  `tools/test_data_freeze.json`; `RACE_REGISTRY` and `"beastfolk"` are not exemptible tokens).

## Goals / Non-Goals

**Goals:**

- One owner for "which sexes may a race carry" (the registry field) and one implementation of the
  rule (`world/rules/identity.py`), read by the player creation validator, every NPC creation path,
  the import validator, the place validator, the preset loader and the name roller.
- Reject the forbidden combination at every boundary *before* a write, and resolve the omitted case
  to the race's permitted value on every NPC path — with the player-facing rejection keeping one
  stable code and one shared Traditional Chinese message.
- Keep the AI layer state-free and the two client surfaces unchanged.

**Non-Goals:**

- Any client-side sex lock, per-race option list, or `creation` panel version bump (D6).
- Changing `SEX_VALUES`, `DEFAULT_SEX`, or the `entity-sex-vocabulary` capability.
- A `sex` field on the scenario-director blueprint or on published scene packages (D4).
- Monsters: their `race` is not a `RACE_REGISTRY` key and no monster path routes through the seam;
  nothing about them changes.
- Rewriting the `sex` of characters or NPCs that already exist, and any load-time revalidation hook
  for persisted entities (D11).
- A repair or migration path for a developer database holding a male elf (D11).

## Decisions

### D1. The rule's data lives in the lore registry: `RaceProfile.allowed_sexes`

`RaceProfile` gains `allowed_sexes: tuple[str, ...] = SEX_VALUES` (the default keeps every existing
constructor and the synthetic `make_race` factory valid); `RACE_REGISTRY["elf"]` declares
`("female",)`; `human`/`beastfolk` declare `SEX_VALUES`.

Rejected alternative — a rules-layer map next to `_AFFINITY_INPUT_BOUNDS`
(`world/rules/character_creation.py:56-60`) with a helper like `max_affinity_elements`:

1. `world/lore/player_presets/validation.py::_validate_preset_sex` and
   `world/lore/settlements/places.py::validate_place_registry` are the only places an elf preset or
   an elf host can be rejected *before* it reaches a live entity, and both run inside
   `world/lore/`, which must not import `world/rules/`.
2. The import layer resolves everything through `RACE_REGISTRY`/`SUBRACE_REGISTRY`; a rules-owned
   map would have to be duplicated there — the drift `validate.py:368-372` already demonstrates for
   affinity.
3. Affinity's map answers "how much *player input* may this race submit", a form bound the panel
   also advertises. The sex set is a race fact of the same kind as `can_use_divine_arts`.

### D2. One implementation of the rule: `world/rules/identity.py`

A new small deterministic-core module owns the whole rule:

```python
permitted_sexes(race_key) -> tuple[str, ...]      # RACE_REGISTRY[race].allowed_sexes, else SEX_VALUES
resolve_sex(race_key, sex) -> str                 # None → permitted default; forbidden → IdentityError
ensure_entity_sex(entity, sex=None) -> str        # resolve for entity.race, write entity.sex, return it
```

`resolve_sex(None_or_unknown_race, None)` is `DEFAULT_SEX`; `resolve_sex(race, None)` is
`DEFAULT_SEX` when that race permits it, otherwise the race's single permitted member (for `elf`,
`"female"`). A `SEX_VALUES` member the race forbids raises `IdentityError`; a non-member raises the
same message the player path already emits (`"sex must be one of: …"`).

Rejected alternatives: spreading a check across the five writers (five copies of the rule, each
free to drift — exactly the failure `validate.py:368-372` shows), and putting the seam in
`typeclasses/npcs.py` beside `ensure_npc_canonical_age` (the typeclass module is a fine home for a
typeclass *default*, but this rule reads a lore registry and is called from rules/quests/imports;
`world/rules/` is the layer AGENTS.md names as the applier of deterministic state changes).

Why the seam cannot be silently bypassed: the player path keeps its own named error surface but
delegates the rule to `resolve_sex`, the import validator is the gate before the loader writes, and
the remaining four write sites are replaced by `ensure_entity_sex` calls, so no production module
outside `world/rules/identity.py` assigns an entity's `sex` — asserted by a source-level test
(D12).

### D3. Player creation: omitted sex normalizes to a value the race permits

`_validate_sex(value, race_key)` delegates to `resolve_sex` and re-raises `IdentityError` as
`CharacterCreationError(str(error))`, so the WebClient adapter, the wizard and the Telnet command
keep the same exception type and the message table keeps matching on fragments.

Rejected alternative — reject `None` for an elf custom request: the Telnet wizard never collects a
sex, so refusal would remove elf creation from that entry point (a functional regression), and the
WebClient would refuse an untouched form whose select still shows the vocabulary default. Rejected
alternative — make either client collect a mandatory sex: a UI change of its own, and it contradicts
`2026-09-08-player-preset-field-parity-design.md` §7's stance in spirit for no gain.

Entry-point consequences (all from the one resolver):

| Entry point | Submitted sex | Resolved for elf |
| --- | --- | --- |
| WebClient `creation.custom` | key omitted (select still at its default) | `"female"` |
| WebClient `creation.custom` (or any direct payload) | `"male"`, or `"other"` sent explicitly | rejected, `sex_not_allowed_for_race` |
| Telnet wizard / `save_custom_draft` | `None` | `"female"`, stored in the draft as `"female"` |
| preset mode (`save_preset_draft`, `activate_draft`) | not collected; `preset.sex` | `"female"` required, otherwise rejected |
| `creation.roll_name` | the member the select displays (`"other"` untouched, `"male"` chosen) | the roll uses the female pool (D8) |

### D4. NPC creation: the seam resolves, the blueprint stays sex-less

The five NPC paths migrate to the seam; three of them write nothing today and gain the call:

| Path | Write site | Change |
| --- | --- | --- |
| JSON import | `world/imports/loader.py::_instantiate_validated_character` (`:236`) | `entity.sex = record["sex"]` → `ensure_entity_sex(entity, record["sex"])` |
| Place host sync | `world/rules/guild_economy.py::sync_service_content` (`:202`) | `host.sex = place.host_sex` → `ensure_entity_sex(host, place.host_sex)` |
| Stage scene NPCs (dream/LLM pipeline) | `world/quests/materializer.py::spawn_role_actor` (`:272`) | add `ensure_entity_sex(npc)` after `npc.race = tier.race_key` |
| Published encounter roles | same shared spawn function | covered by the row above |
| Starting companions | `world/rules/starting_companions.py::build_starting_companion` (`:167`) | `npc.sex = preset.sex` → `ensure_entity_sex(npc, preset.sex)` |

The scenario-director blueprint and the published scene package **stay sex-less**: `world/ai/`
never writes state, and a role sex authored by a model would be input the deterministic core would
then have to police, with exactly one legal value for every elf role. The instantiator supplies the
sex from the role's tier race, so a dream-generated elf scene NPC lands on `"female"` instead of
`"other"`. Rejected alternative — add an optional blueprint `sex`: it moves identity authoring into
the generative layer and buys nothing the tier's race does not already determine.

### D5. Import enforcement is the semantic layer, not a JSON-Schema conditional

Add `_check_sex_for_race(record)` to `world/imports/validate.py` and call it from
`validate_character` immediately after `_check_race_subrace` (so the race is known, and an
unresolvable race is left to the race check). No `if/then` block is added to `CHARACTER_SCHEMA_V1`
and no second guard is added to `loader.py`.

Reasons: (a) the schema is race-agnostic and value-typed — a Draft 2020-12 conditional would need
either the literal pair `elf`/`female` (a second owner of the canon fact) or a `world.lore.races`
import into a pure data document; (b) the established split in this very file is "schema owns
structural shape, semantics own registry-resolved rules" — `_check_affinity_elements` states and
follows it (`:375-385`); (c) a schema rejection surfaces `jsonschema`'s generic `const`/`enum` text,
while the import contract requires each issue to name the record, the field and the reason
(`import-validation::every-reported-issue-names-the-record-the-field-and-the-reason`). The check is
target-typeclass agnostic, so an elf NPC import inherits it with no branch. "The loader never
persists such an entity" is established by the existing all-or-nothing gate: `load_batch` and the
single-record entry both run `validate_character` and raise `ImportRejected` before
`transaction.atomic()`.

### D6. UI parity is the named server rejection: neither client changes

Decision: **do not lock the `sex` select**, ship no per-race option list, keep the `creation` panel
at version 6, and leave `CreationOverlay.vue` and
`web/static/webclient/js/elosern/protocol/panels/creation.js` untouched — the same decision mirrored
in both clients.

Rationale: the panel contract requires every finite control to derive from immutable registries with
no duplicated literal, so a `race === "elf"` branch in either client would be a second authority for
a canon fact. The player is not surprised: an untouched elf form omits `sex`, the preflight resolves
`"female"`, the returned draft carries it and the select re-selects it; an explicit `男性`
submission returns the named rejection whose Traditional Chinese message the overlay renders in
`creation-result-message` (role `alert`).

Rejected alternative — server-supplied per-race options: it adds a new `custom` key, forces a panel
schema 6 → 7 bump, and requires mirrored validators plus new Node-gate and Vitest coverage in both
clients, all to prevent a combination the server already refuses with an actionable message. It is
larger than the rule it serves and does not make the rule more true.

### D7. The authored-data boundaries validate too

- `world/lore/player_presets/validation.py::_validate_preset_sex` additionally rejects a card whose
  `sex` its race does not permit (the identity validator has already proven the race resolves, and
  `.get` keeps the function standalone-testable).
- `world/lore/settlements/places.py::validate_place_registry` additionally rejects a hosted place
  whose `host_sex` its `host_race` does not permit, next to the existing membership check
  (`:319-328`). All eight shipped elf hosts already declare `female`, so no shipped row changes.

Both raise at load with a message naming the offender, matching the sibling validators' stance.

### D8. The race-level name roll is bounded by the race's declared sex set

`roll_name_for_race` bounds the sex it rolls for: when the race declares exactly one permitted sex,
the roll uses that member whatever the caller passed (including `None`, `""`, an unrecognised
string, or a member the race forbids). Every other race — and an unresolvable `race_key` — passes
the value through unchanged, so the unspecified→random-pool and explicit-member→own-pool behaviour
is untouched, as is the pack-level `roll_name`.

Rationale: the creation form always sends the member its select displays (`"other"` on an untouched
form, `"male"` when chosen), so a rule keyed only on `None`/unknown values would leave the 🎲 button
rolling the male or unisex pool for a female-only race. The bound derives from the same registry
field, adds no second literal, and preserves the module's purity (no new RNG call, no module state,
identical replay for identical seeds). Rejected alternative — leave the roller alone: an elf who
clicks 🎲 with the default `"other"` draws from the unisex pool of a race that can no longer be
anything but female.

### D9. Documentation is part of the change

`docs/development/adding-npcs.md`: the §1 five-path table and mechanism paragraph, §2 question 1
(host identity), Step 1's NPC-specific card rules (a fifth bullet: what an elf card declares, what
an author sees for a non-female sex, and what the dream/scenario-director path does by default),
and the Step 2 CLI note. `docs/development/adding-player-presets.md`: §2 question 1, the §4
`_validate_preset_sex` row (the section's trigger-point and validator counts stay truthful — the
chain is still three trigger points and eleven lore validators), and §5's common-mistakes table.

Both guides describe *existing* mechanisms only; the text is written from the shipped code, never
from this plan. Disclosed: the `adding-npcs.md` scenario in the delta is verified by the doc review
in `review.md` plus the structural checks the tasks state, because no capability owns that page and
this change does not invent one; the preset guide's scenarios are contract-testable and are tested.

### D10. No migration, no repair, no revalidation on load

The project is unreleased with no users (AGENTS.md). No migration, backfill or load-time repair is
written for a developer database that happens to hold a male elf; the development database is
discarded. `LivingEntity.sex` keeps its attribute default, and the *validation and resolution*
gates are what make a non-female elf unreachable.

### D11. No new observability event

The change adds no persistent state transition, no external I/O and no cross-system workflow: it
rejects input earlier and resolves a value on paths that already exist. No `world.observability`
event is added, no `log_*` call is introduced or moved, and `tools/observability_freeze.json` is
untouched. The new rejections reach operators through the existing return values (the import report,
the creation rejection code/message, the load-time `ValueError`).

### D12. Tests, shards and traceability

One **new** test module — `world/rules/tests/test_identity.py` — MUST be registered in exactly one
shard of `.github/evennia-shards.json` in the same change. Every other new test joins an existing
registered module. No browser test class or method is added, so `.github/browser-shards.json` needs
no edit.

Tests for **MODIFIED** requirements carry `covers_requirement("<literal-id>")` with the existing
canonical IDs (obtained with `uv run --locked python -m tools.spec_traceability list`). The **ADDED**
requirements (`import-validation`, `settlement-place-registry`, `preset-authoring-docs`) have no
canonical ID before the archive sync, so their tests are written **without** any annotation; the
mapping is recorded here and the archive stage annotates them with the tool-generated IDs:

| Test | ADDED requirement / scenario |
| --- | --- |
| `world/imports/tests/test_validation_semantics.py::test_a_non_female_elf_record_is_rejected` | `import-validation` "A character record's sex must be permitted by its race" — forbidden member rejected on field `sex` |
| `…::test_a_permitted_sex_produces_no_sex_issue` | same — positive control on the same single-sex race |
| `…::test_races_that_permit_the_value_produce_no_sex_issue` | same — full-vocabulary race, all three members |
| `…::test_an_unresolvable_race_leaves_the_sex_judgement_to_the_race_check` | same — no duplicate issue |
| `…::test_the_sex_check_applies_to_npc_targets_too` | same — NPC target rejected by the same check |
| `world/imports/tests/test_batch_all_or_nothing.py::test_a_non_female_elf_record_persists_nothing_from_the_batch` | same — batch persists no entity, valid sibling included |
| `world/lore/tests/test_settlements.py::test_an_elf_host_with_a_forbidden_sex_fails_load` | `settlement-place-registry` "A place's authored host sex must be permitted by the host's race" |
| `world/lore/tests/test_settlements.py::test_a_permitted_host_sex_still_loads` | same — permitted member passes |
| `tests/test_preset_authoring_docs_contract.py::test_the_validator_table_documents_the_race_bounded_sex_rule` | `preset-authoring-docs` "The preset guide documents the race-bounded sex rule" |
| `tests/test_preset_authoring_docs_contract.py::test_the_mistake_table_carries_the_elf_sex_case` | same — mistake-table entry |

`tools/test_data_lint` gates behavior tests: those files must resolve fixtures through the synthetic
kit and must not name shipped catalog symbols or unexempted tokens (see Contracts for the exact
idioms). The pre-sync `spec_traceability check --change <change>` only indexes
`openspec/specs/*/spec.md`, so ADDED requirements are invisible to it — it reports zero gaps for
them, which is expected, not a waiver.

## Contracts

Control flow and the exact contracts, so an implementation has no room to diverge:

```python
# world/lore/races.py
from world.lore.sex import SEX_VALUES          # new import (world/lore/sex.py has no dependencies)

@dataclass(frozen=True)
class RaceProfile:
    key: str
    lifespan: tuple[int, int]
    vital_baseline: Vitals
    static_baseline: StaticBand
    learning_multiplier: float
    can_use_divine_arts: bool
    description: str
    display_name_zh: str
    # The sex vocabulary members this race may carry; the elf is female-only.
    allowed_sexes: tuple[str, ...] = SEX_VALUES

RACE_REGISTRY["elf"] = RaceProfile(..., display_name_zh="精靈", allowed_sexes=("female",))
# human and beastfolk keep the default (SEX_VALUES); no other entry changes.
```

```python
# world/rules/identity.py — NEW module: the single implementation of the rule
from __future__ import annotations

from typing import Any

from world.lore.races import RACE_REGISTRY
from world.lore.sex import DEFAULT_SEX, SEX_VALUES


class IdentityError(ValueError):
    """Raised when a declared identity value cannot be resolved."""


def permitted_sexes(race_key: Any) -> tuple[str, ...]:
    """The sex members one race may carry (every member for an unresolvable race)."""
    race = RACE_REGISTRY.get(race_key) if isinstance(race_key, str) else None
    return race.allowed_sexes if race is not None else SEX_VALUES


def resolve_sex(race_key: Any, sex: str | None) -> str:
    """Resolve a declared or omitted sex against the race's declared set."""
    allowed = permitted_sexes(race_key)
    if sex is None:
        return DEFAULT_SEX if DEFAULT_SEX in allowed else allowed[0]
    if sex not in SEX_VALUES:
        raise IdentityError("sex must be one of: " + ", ".join(SEX_VALUES))
    if sex not in allowed:
        raise IdentityError(f"sex {sex!r} is not available for race {race_key!r}")
    return sex


def ensure_entity_sex(entity: Any, sex: str | None = None) -> str:
    """Write the resolved sex on one entity and return it (the creation-path seam)."""
    resolved = resolve_sex(getattr(entity, "race", None), sex)
    entity.sex = resolved
    return resolved
```

```python
# world/rules/character_creation.py — _validate_sex (currently :285-302) delegates
def _validate_sex(value: Any, race_key: str) -> str:
    """Validate the sex channel against the race's declared set."""
    try:
        return resolve_sex(race_key, value)
    except IdentityError as error:
        raise CharacterCreationError(str(error)) from error

# preflight_character_creation: the single call site (:480) becomes
#   checked_sex = _validate_sex(sex, race)
# It MUST stay after the race resolution (:458-464), which proves the key exists.
```

```python
# world/rules/creation_messages.py — additions (both tables)
CREATION_REASON_MESSAGES: dict[str, str] = {
    ...,
    "sex_not_allowed_for_race": "所選種族不允許這個性別。",
}
_MESSAGE_CODE_MATCHES: tuple[tuple[str, str], ...] = (
    ...,
    ("is not available for race", "sex_not_allowed_for_race"),
    ("sex must be one of", "unknown_sex"),
)
```

```python
# world/lore/player_presets/validation.py — extend _validate_preset_sex (:249-261)
    for preset in registry.values():
        if preset.sex not in SEX_VALUES:
            raise ValueError(f"preset {preset.key!r} declares unknown sex {preset.sex!r}")
        race = RACE_REGISTRY.get(preset.race)
        if race is not None and preset.sex not in race.allowed_sexes:
            raise ValueError(
                f"preset {preset.key!r} declares sex {preset.sex!r} that race "
                f"{preset.race!r} does not permit"
            )
# .get keeps the validator standalone-testable; in the import-time chain
# _validate_preset_identities has already proven preset.race resolves.
```

```python
# world/lore/settlements/places.py — next to the existing host_sex membership check (:325-328)
        if not hostless and place.host_sex not in RACE_REGISTRY[place.host_race].allowed_sexes:
            raise ValueError(
                f"place {place.key!r} names host_sex {place.host_sex!r} that host_race "
                f"{place.host_race!r} does not permit"
            )
# Reached only after :321-324 has proven host_race resolves, and only for a complete host.
```

```python
# world/imports/validate.py — new semantic check, registered in validate_character
def _check_sex_for_race(record: dict[str, Any]) -> list[Issue]:
    """Reject a sex the record's race does not declare.

    Race-unresolvable records are left to ``_check_race_subrace``. The check runs for
    every character record regardless of target typeclass: the world's canon admits no
    male elf at all.
    """
    race = RACE_REGISTRY.get(record.get("race"))
    if race is None:
        return []
    sex = record.get("sex")
    if sex in race.allowed_sexes:
        return []
    return [Issue("sex", f"sex {sex!r} is not available for race {race.key!r}")]

# validate_character (:694): report.rejections.extend(_check_sex_for_race(record))
# immediately after `_check_race_subrace`. The structural phase already proved `race`
# and `sex` are strings (CHARACTER_SCHEMA_V1 requires both), so no lookup can raise.
```

```python
# world/quests/materializer.py — spawn_role_actor (:272)
    npc.race = tier.race_key
    ensure_entity_sex(npc)          # no declared sex on this path: the race decides
```

```python
# world/rules/namegen.py — the race bound
from world.lore.races import RACE_REGISTRY            # new import (rules may read lore)

def _resolve_race_bounded_sex(race_key: str | None, sex: Any) -> Any:
    """Bound a requested sex by the race's declared set (design D8)."""
    if isinstance(race_key, str):
        race = RACE_REGISTRY.get(race_key)
        if race is not None and len(race.allowed_sexes) == 1:
            return race.allowed_sexes[0]
    return sex

def roll_name_for_race(race_key: str | None, sex: str | None, rng: Random) -> str:
    return _roll_from_pack(
        _pick_pack_for_race(race_key, rng), _resolve_race_bounded_sex(race_key, sex), rng
    )
# _roll_from_pack and roll_name are unchanged, including the empty-pool fallback.
```

Test fixtures (the existing idioms, all `tools.test_data_lint`-clean):

```python
# a race row borrowed under the production key, with the singleton declared set
elf = replace(SYNTH_RACES["t_duskmari"], key="elf", allowed_sexes=("female",))
# make_race() rejects a non-"t_"-prefixed key, so never call make_race("elf", ...)
branch = make_subrace("t_dawn_herald_kin", race_key="elf")
kits = {branch.key: SubraceStartingKit(branch.key, (("t_thorn_knife", 1),))}
with synthetic_registries("races", "subraces", "starting_kits",
                          extra={"races": {"elf": elf},
                                 "subraces": {branch.key: branch},
                                 "starting_kits": kits}):
    ...
```

```python
# a live registry read without naming the symbol (unexempted behavior files)
module = importlib.import_module("world.lore.races")
registry = getattr(module, "RACE" + "_REGISTRY")
forbidden = next(sex for sex in SEX_VALUES if sex not in registry["elf"].allowed_sexes)
```

```python
# an elf import record from the shipped example, without naming a shipped subrace
record = example_record()
stand_in = make_subrace("t_ashward_subrace", race_key="elf")
record["race"], record["subrace"] = "elf", stand_in.key
record.pop("affinity_elements", None)
record["sex"] = forbidden                      # derived, never a literal
with synthetic_registries("subraces", extra={"subraces": {stand_in.key: stand_in}}):
    ...
```

## Risks / Trade-offs

- [A typo in a race's `allowed_sexes` silently forbids every sex for that race] → the
  `lore-registries` scenario plus a registry test assert every set is a non-empty `SEX_VALUES`
  subset; the failure mode is loud (every creation for that race rejects with the named error).
- [`resolve_sex` indexes `RACE_REGISTRY[race_key]`, so an unvalidated race key would raise
  `KeyError` instead of a named error] → `permitted_sexes` uses `.get` and falls back to
  `SEX_VALUES`, so an unresolvable race normalizes instead of crashing; the player path still
  proves the key at `:458-464` before calling it.
- [The seam could be bypassed by a future creation path] → the source-level test in D12 asserts no
  production module outside `world/rules/identity.py` assigns `sex`; a bypass would fail it.
- [Scene and encounter NPCs gain a write on a hot path] → the write happens once per spawn in the
  existing identity block, reads one dict, and adds no transaction or query.
- [Presets built in-process bypass the load validator] → the preflight arm rejects them too, and
  both arms are tested separately.
- [The namegen bound changes the elf roll stream] → intended; it removes the pool choice for a race
  that has exactly one outcome and keeps replay determinism for a given seed.
- [Three ADDED requirements are uncovered until the archive sync] → their tests are written now
  (unannotated), the mapping is recorded in D12, and the archive stage annotates with the
  tool-generated IDs.
- [Adding a field to `RaceProfile` could break an exact-field assertion] → no shipped test asserts
  the dataclass's field set (the registered `lore-registries` test asserts the power-gap ratios and
  the absence of the former magic fields), and the field carries a default so every constructor and
  the synthetic factory stay valid.
- [The `adding-npcs.md` doc scenario is not machine-enforced] → disclosed in D9 and covered by the
  review document plus the factual-consistency check in the tasks; no test claims otherwise.

## Migration Plan

None. No data migration, no repair command, no compatibility shim, no client rebuild:
`SEX_VALUES`, `DEFAULT_SEX`, the panel schema version and both client bundles are unchanged. The
only deployable artifact change is Python plus two developer guides, and the development database
may be discarded.

## Open Questions

None — every decision above is settled; the wording of the single new Traditional Chinese message is
reviewed via `review.md` (human-reviewed), not deferred.
