## Context

Every place in `PLACE_REGISTRY` must name a profession, and `validate_service_hosts` derives one roster row per place. Of the four shipped professions only three are place-bound, and all three carry trade or guild capability. So today "a place exists" and "a place sells something or runs guild business" are the same statement. Twelve of the eighteen location types in `docs/lore/settlement-locations.md` are neither.

`ScriptedDialogue` already exists as a component, is already place-bound in the `guild_staff` and `guild_examiner` blueprints, and already declares exactly the identity fields a talk host needs (`service_id`, `dialogue_key`). Nothing needs inventing — the blueprint that combines it alone is simply missing.

## Goals / Non-Goals

**Goals.** One place-bound talk-only blueprint. An authoring home for dialogue rows that scales past one. A load-time guarantee that an authored host can actually speak.

**Non-Goals.** No shipped place adopts the blueprint here. No new component, no new dialogue mechanic, no change to how `talk` resolves or answers. Affinity, intents and the generative dialogue pipeline are untouched — an attendant host is an ordinary scripted-dialogue host and inherits all of it.

## Decisions

### `attendant`, not a per-role profession

The alternative was one profession per role — `innkeeper`, `bathhouse_keeper`, `trainer`. That reads better in the YAML and is wrong: a profession is an assembly-time component tuple, not an occupation label, and `professions.yaml` says so in its header. Twelve rows with identical component tuples would be twelve names for one blueprint, and the first time someone tried to read occupation off a profession the vocabulary would start lying. The occupation lives where it already lives — in the authored `host_title` and the dialogue table.

`attendant` names what the blueprint *is* (a host that attends a place and talks) rather than what any one host does.

### Dialogue rows move to a `world/lore/dialogue/` package

`DIALOGUE_TABLE` is authored prose keyed by a stable identifier — immutable identity, which the repo puts under `world/lore/`. It currently sits in `world/rules/dialogue.py` because there was exactly one row and no reason to split. Around eighteen more rows are coming, so it moves out and arrives already split.

The package is split by domain rather than dumped in one module: `shape.py`, `guild.py`, `altoria.py`, `ciaran.py`, and an `__init__.py` that assembles `DIALOGUE_ROWS` in a fixed order — exactly as `PLACE_REGISTRY` assembles from its per-settlement slices. Splitting now rather than when a file gets long means the five content changes that each add tables are not all editing one file.

The guild row moves verbatim and every existing lookup keeps its import.

`world/lore/` must not import `world/rules/`, so the dataclasses are imported the other way: `dialogue.py` imports the rows, not the reverse. That means the package needs the two dataclasses — and taking them from `dialogue.py`, a rules module, is backwards.

Resolved by moving `DialogueDefinition` and `KeywordResponse` into the package's `shape.py`, and re-exporting them from `dialogue.py` so no caller changes. The shape of authored data is authored data.

### Resolution is checked at load, degradation stays at runtime

Two rules that look contradictory and are not:

- A **place row** naming an unresolvable `dialogue_key` fails catalog load. The place registry is authored content validated fail-closed; a host that cannot speak is an authoring error, and the existing single guild host hid this because it was the only one.
- A **runtime lookup** of an unregistered key still returns the no-understanding line. Hosts reach the registry from routes the place registry does not own — imports, quest scene NPCs — and a raise there would turn a cosmetic gap into a crash mid-conversation.

The scripted-dialogue capability's existing scenario pins the second. This change pins the first in its own capability, so neither weakens the other.

### Where the check lives

In `validate_service_hosts`, beside the blueprint-coverage loop that already resolves each component's identity fields. It fires for any profession whose blueprint includes `scripted_dialogue` — so the guild hall's host is covered by the same rule, not just attendants. Putting it in `validate_place_registry` was rejected: that function is deliberately free of rules-layer imports, and the dialogue registry is a rules-layer read.

## Risks

**A content change forgets the dialogue row and the whole catalog fails to load.** That is the intended behaviour and the reason for the check, but it means each content change must land its dialogue row and its place row together. Stated in every downstream change's tasks.

**Moving the dataclasses ripples.** `DialogueDefinition`/`KeywordResponse` are imported by tests and possibly the webclient presentation layer. The re-export from `dialogue.py` keeps every existing import working; the task verifies by grep that no importer is left naming a moved symbol from a module that no longer defines it.
