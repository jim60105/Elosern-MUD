## Why

You cannot talk to a shopkeeper. 瑪爾特·金秤 has run the capital's general store since the guild economy landed and has never had a line of dialogue, because the `merchant` blueprint carries one `Merchant` component and nothing else. Authoring a `dialogue_key` on a merchant place is rejected as a kwarg no component consumes.

Every other kind of host talks. The guild staff greets you and explains the guild commands — that greeting is how a new player learns `guild register` exists. A shopkeeper who cannot answer 「你這裡賣什麼」 is the one NPC in the world who stands behind a counter and says nothing.

The world document assumes otherwise throughout. Its shop sections describe haggling regulars and apprentices who eavesdrop; its NPC section states the rule at line 83 — if a player can walk up to it and `talk` it, it carries authored identity, and a merchant does.

## What Changes

- Extend the `merchant` blueprint to `[merchant, scripted_dialogue]`, both place-bound. Every merchant host gains a dialogue table and answers.
- **BREAKING for authoring**: every merchant place must now author a `dialogue_key`. Blueprint coverage rejects a merchant row without one, which is the desired failure — a silent greetingless shopkeeper is what this change exists to remove.
- Author dialogue for all eight shipped merchant hosts: the capital's four shops and the village's four homes. Each answers about what it stocks, and points at `shop stock`, `buy` and `sell`.
- The village hosts answer in their own register. They are not shopkeepers — the settlement's whole premise is that trading there is 「分享興趣與互助，不是營業」 — so 瓦爾溫 talks about what she has collected, not about her prices.

## Capabilities

### New Capabilities
- `merchant-dialogue`: a shopkeeper answers questions, the rule that every merchant host carries a dialogue table, and the rule that a trading host's register follows its settlement rather than a shop template.

### Modified Capabilities
- `profession-registries`: the `merchant` row's component tuple changes, and the requirement enumerating the shipped table describes it.

## Dependencies

This change lands after `place-attendant-profession`, whose dialogue package it fills and whose `profession-registries` delta its own delta is written against.

## Impact

- `world/rules/rulebook/professions.yaml` — the `merchant` row gains a component.
- `world/lore/dialogue/altoria.py` and `ciaran.py` — eight dialogue tables.
- `world/lore/settlements/places_altoria.py`, `places_ciaran.py` — eight rows gain a `dialogue_key`.
- `world/rules/guild_config.py` — untouched. Blueprint coverage and the dialogue-key resolution check already do the work; this change only changes what the blueprint contains.
- `world/rules/guild_economy.py` — untouched. Assembly already attaches whatever the blueprint declares.
