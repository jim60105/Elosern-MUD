## Context

See proposal.md for motivation. Current declarations (declaring preset → partner preset, relationship label):

| Declaring preset | Partner (companion) | Partner race/sex | Label |
|---|---|---|---|
| `violet_altoria` 薇歐蕾特 | `lidzia_rosenthal` 莉茲婭 | human/female | 貼身近侍 |
| `lidzia_rosenthal` 莉茲婭 | `violet_altoria` 薇歐蕾特 | human/female | 殿下 |
| `yuka_darknight` 悠花 | `yuna_darknight` 悠奈 | elf/female | 雙胞胎姊姊 |
| `yuna_darknight` 悠奈 | `yuka_darknight` 悠花 | elf/female | 雙胞胎妹妹 |

`world/rules/starting_companions.py::_build_persona_record` returns `preset.persona.to_record()` with `social_connection[player.key] = relationship`. The builder has no transaction of its own and deletes the partial NPC on failure; `activate_player_character` wraps it in its atomic block. `world/lore/` must not import `world/rules/`, which is why the rules-side sweep exists.

## Goals / Non-Goals

**Goals:** companion NPC personas come only from NPC profiles plus a factual owner line; the companion is otherwise mechanically identical to its partner preset; every write goes through the shared persona writer with companion provenance.

**Non-Goals:** changing any player preset, `PresetPersona`, player activation, party/affinity mechanics, or companions already built in an existing database (the cutover owns those); voice routing (dialogue-consumption owns it).

## Decisions

### D1. One profile per partner, keyed `companion_<partner preset key>`

Each partner appears in exactly one declaration, so the declaration and the partner share one profile. The card is newly written for the NPC: identity, appearance, personality, and life story stay consistent with the partner preset's established facts (name, race, age band, role, family/court relationship) but are not copied; `speech_style` is new and explicit. The profile's `social_connection` describes non-owner relationships only (it may be empty); the owner relationship is composed at build time. `greeting` is authored (spoken offline when the generative layer degrades); `misunderstood` stays `None` (companions carry no scripted table).

### D2. The owner line is a fact, composed deterministically

`social_connection = f"{owner_key}：{relationship}"`, followed by `"\n" + profile_social` when the profile authors one. `owner_key` is the owning player character's key at build time. The rules sweep validates every declaration against a synthetic 64-code-point owner key (the player-name maximum, `NAME_MAX_LENGTH`): the composed leaf must be ≤ 600 code points and the composed card's rendered block ≤ 2,000, so a real build cannot fail the contract on a long name. Alternative rejected: storing the relationship only in metadata — the NPC's own prompt must know whose companion it is.

### D3. The builder writes through the shared initializer

`build_starting_companion` replaces `npc.db.persona = _build_persona_record(...)` with `initialize_npc_persona(npc, card, {"kind": "companion", "profile": key, "owner": player.pk})` at the same point in the build, inside the existing `try` whose `except` deletes the NPC. `_build_persona_record` is deleted. The preset is still read for every mechanical value.

### D4. Declaration shape

`StartingCompanion(preset_key, affinity, relationship, npc_profile_key)` — a required fourth positional field. Lore validation (`world/lore/player_presets/validation.py`) rejects an unregistered profile key or a profile whose key does not match `companion_<preset_key>`. The four declarations are updated in the same change.

## Risks / Trade-offs

- [Card drifts from the preset's facts] → the editorial review (task 4) checks each card against the partner preset's card and story text; the preset stays the mechanical and factual source.
- [Existing activated characters in a dev DB keep old companion personas] → expected; `npc-persona-roster-cutover` replaces them and recomputes the owner line from the existing binding.
- [Preset authoring docs contract pins the declaration shape] → update the documentation in the same change and run `tests.test_preset_authoring_docs_contract`.
