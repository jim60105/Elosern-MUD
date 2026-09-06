# Tasks: lore-deterministic-reveals

## 1. Best-effort reveal helper

- [ ] 1.1 Add a `reveal_lore_best_effort(player, category, key)` helper beside the sole writer in
  `world/rules/lore_knowledge.py`: call `record_lore_reveal`, and on any exception emit the facade
  event with `exc=` and the `char`, `category`, and `key` context rather than propagating. It returns
  whether the reveal landed; callers ignore the result.
- [ ] 1.2 Confirm the helper adds no second writer — it only wraps `record_lore_reveal`.

## 2. Arrival reveals

- [ ] 2.1 At the shared room-arrival observation point, resolve the entered room to a registered
  anchor and to a registered wilderness region, and reveal each that resolves. Reuse the existing
  anchor and region resolution used by the quest REACH matcher rather than adding a second lookup.
- [ ] 2.2 The reveal runs after the arrival's own state changes commit and never inside a transaction
  the arrival would roll back.

## 3. Defeat reveals

- [ ] 3.1 At the committed `target_defeated` consumption point already read by the DEFEAT planner,
  reveal the defeated monster's tier for the crediting character when the tier is registered.
- [ ] 3.2 Exclude simulated defeats, matching the existing exam-simulation exclusion.

## 4. Origin reveals

- [ ] 4.1 On character-creation completion, reveal the chosen `race` and `nation` entries; an
  unresolvable value reveals nothing and blocks nothing (a subrace key is not a race entry).
- [ ] 4.2 On guild registration completion, reveal the registrant's `guild` rank entry.

## 5. Tests

- [ ] 5.1 Offline test: with every `LLM_PROFILES` entry configured to fail, create a character,
  travel to a registered anchor, and defeat a registered-tier monster; assert the origin, anchor, and
  monster entries are present.
- [ ] 5.2 Arrival tests: anchor recorded; region recorded; unremarkable room records nothing;
  re-entry is a silent no-op.
- [ ] 5.3 Defeat tests: registered tier recorded; simulated defeat records nothing; untiered or
  unregistered tier records nothing.
- [ ] 5.4 Origin tests: race and nation recorded at creation; guild rank recorded at registration; an
  unresolvable value records nothing and the operation still completes.
- [ ] 5.5 Non-blocking tests: a malformed `lore_discovered` record does not break movement and is
  neither reset nor rewritten; a reveal exception does not roll back combat settlement; both log
  through the facade with the exception attached.
- [ ] 5.6 Silence test: a successful reveal sends no message to the character.
- [ ] 5.7 Sole-writer test: no new module assigns `db.lore_discovered` directly.
- [ ] 5.8 Annotate with `covers_requirement` against the added `lore-knowledge` requirement IDs;
  update `.github/evennia-shards.json` for new integration modules.
- [ ] 5.9 Run the observability lint plus the focused lore, room-observation, combat-settlement,
  creation, and guild-registration test modules in the same batch.
