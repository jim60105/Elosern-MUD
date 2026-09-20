## Why

Three of the locations `docs/lore/settlement-locations.md` calls for have no functional NPC by design, and the document says so outright. 市場街 (line 374): 「市場街本身不需要一位固定的『街長』型功能性 NPC，遊戲性功能都掛在各個攤販身上」. 精靈村落's 村中廣場 is 「全族共用空間」, a gathering clearing, not someone's workplace. And a capital worth walking through needs landmarks — a palace forecourt, a cathedral step, a river quay — that exist to be looked at, not talked to.

The place registry cannot express any of them. `PlaceDefinition` requires a host name, title, race, sex, profession, service id and component kwargs, and `validate_service_hosts` derives exactly one roster row per place. "A place exists" and "a place has a permanent NPC standing in it" are currently the same statement.

The workaround — inventing a caretaker NPC for a plaza — is worse than the gap. It contradicts the source document and puts a nameable, talkable body in a space the world says is empty.

## What Changes

- The host fields on `PlaceDefinition` become optional **as a single group**: a place either authors a complete host (name, title, race, subrace, sex, profession, service id, component kwargs) or authors none of them. A half-authored host is a load error naming the place and the fields that break the set.
- The derived service-host roster skips host-less places. It stays what it is — a projection of the places that declare a host — so a host-less place contributes no row rather than a blank one.
- Interior synchronization is unchanged in shape and still builds every place: the room, its tag, its description and both doorways. A host-less place is a real, walkable, permanent room; only the NPC is absent.
- A host-less place may not declare assortments, additions or exclusions. Goods need a merchant to sell them, and the existing shop-identity rule already says a place declares goods if and only if it declares a shop — this extends it to the host itself.
- **No shipped place becomes host-less.** All nine keep their hosts unchanged. The capability ships unused, the same way the attendant blueprint does.

## Capabilities

### Modified Capabilities
- `settlement-place-registry`: the record-shape requirement gains the all-or-nothing host rule; a place's host becomes optional where today it is mandatory.
- `place-driven-service-sync`: the end-to-end guarantee is restated so that a place without a host still yields a complete room, and the roster is stated to cover the host-declaring places rather than all places.

## Dependencies

This change lands after nothing. It shares `world/lore/settlements/places.py` with `altoria-capital-replan` and `altoria-place-slices`, so those three must not be worked in parallel, and it shares `world/rules/guild_config.py` with `place-attendant-profession` and `commerce-rulebook-slices`.

## Impact

- `world/lore/settlements/places.py` — host fields default to `None`; `validate_place_registry` gains the all-or-nothing check and the goods-need-a-host check.
- `world/rules/guild_config.py` — `validate_service_hosts` iterates the host-declaring places; `_place_for_shop` is unaffected because a host-less place can carry no `shop_key`.
- `world/maps/bootstrap.py` — untouched. It already iterates places and reads only room and doorway fields.
- `world/rules/guild_economy.py` — untouched.
- `world/tests/synthetic_data/` — the kit gains a host-less place fixture.
