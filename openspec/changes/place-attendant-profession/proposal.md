## Why

`docs/lore/settlement-locations.md` names a functional NPC for every location type — 酒館老闆、旅店老闆娘、商會會長、浴場管理員、衛隊長、教頭、院長 — and states the rule plainly at line 83: if a player can walk up to it and `talk` it, it must carry an authored name and title. None of those hosts can exist today. The profession vocabulary is closed to four rows, and of those only `merchant` and the two guild rows are place-bound; `quest_issuer` is explicitly person-bound and `professions.yaml` states a person-bound row can never anchor a roster row. A place whose service is conversation, not trade, therefore has no blueprint to host.

This blocks nine of the twelve remaining 聖潔王都 locations and three of the six remaining 暗影谷村 ones. It is the single prerequisite the rest of the settlement build waits on.

## What Changes

- Add `attendant` to `world/rules/rulebook/professions.yaml`: one place-bound `scripted_dialogue` component. It is the talk-only counterpart to `merchant` — a host that carries authored identity and a dialogue table, and nothing else.
- Move the authored dialogue content out of `world/rules/dialogue.py` into a lore-side **package**, `world/lore/dialogue/`, split by domain: the shape, the guild row, the capital's hosts and the village's. Around eighteen tables are coming, and one file would end up the size the rules module is now. `DIALOGUE_TABLE` keeps its name, shape and every current lookup; only where the rows are authored moves.
- Make an unresolvable `dialogue_key` a load error. Today blueprint coverage proves the kwarg was *authored*; it does not prove it *resolves*. A place naming a dialogue table that does not exist currently degrades silently to a greetingless host at runtime — with one guild host that was invisible, with a dozen attendant hosts it is a content trap.
- **No shipped place adopts `attendant` in this change.** The roster, the interiors and every live NPC are bit-for-bit unchanged; the mechanism is proven over synthetic fixtures. The hosts arrive with their locations in the content changes that follow.

## Capabilities

### New Capabilities
- `place-attendant-hosts`: a place-bound, talk-only service host — the blueprint, the authored dialogue seam, and the fail-closed rule that binds a host to a dialogue table that exists.

### Modified Capabilities
- `profession-registries`: the requirement that enumerates the shipped profession table gains `attendant`. That requirement is also stale today — it says the table holds *exactly* `merchant`, `guild_staff` and `guild_examiner`, while `quest_issuer` has shipped in the YAML since the quest-issuer change with no spec naming it. The rewritten text enumerates all five rows.

`scripted-dialogue` is deliberately **not** modified. Its requirement constrains the registry's shape and read-only-ness, not where the rows are authored, and its "a missing table yields the no-understanding line" scenario stays true: runtime degradation is for hosts that arrive by other routes. The load-time rejection this change adds applies to an authored place row, and belongs to the new capability.

## Impact

- `world/rules/rulebook/professions.yaml` — one new row.
- `world/rules/dialogue.py` — `DIALOGUE_TABLE` assembled from the new lore module; `resolve_dialogue_component`, `dialogue_key_for`, `table_response`, `dialogue_has_keyword` and every caller untouched.
- `world/lore/dialogue/` (new package) — `shape.py` (the two dataclasses), `guild.py` (the existing row, moved with every contract-pinned substring retained and its prose re-authored in the clerk's in-character 正體中文 voice, capped at the panel's four pressable keywords), `altoria.py` and `ciaran.py` (empty until content changes fill them), and `__init__.py` assembling `DIALOGUE_ROWS`. No file is expected to pass 600 lines; if `altoria.py` approaches it, it splits by terrace the way the capital's place slices do.
- `world/rules/guild_config.py` — `validate_service_hosts` gains the dialogue-key resolution check.
- `world/lore/settlements/places.py` — untouched. A place already authors `dialogue_key` through `authored_kwargs`; `attendant` needs no new field.
- `world/rules/guild_economy.py`, `world/maps/bootstrap.py`, `commands/` — untouched.
