## MODIFIED Requirements

### Requirement: Settlement stages run in the fixed order regen, buffs, sexual decay, magic study,
daily resets, then the five declared world-event seams
`world/rules/clock.py` SHALL define a single, ordered stage sequence — `gauge_regen`, `buff_ticks`,
`sexual_decay`, `magic_study`, `daily_resets`, `caravan_arrivals`, `shop_hours`, `quest_deadlines`,
`npc_schedules`, `instance_reclamation` — matching design doc §6.5's four built stages plus
`magic_study` (change 11b's `accrue_magic_study()`, inserted between `sexual_decay` and
`daily_resets`) plus `instance_reclamation` (change 14's `reclaim_due_instances()`, appended after
`npc_schedules` as the final stage), and SHALL execute every `advance()` call's stages in this order
with no configuration or call-site override capable of changing it.

#### Scenario: The stage order is exactly the fixed sequence, including magic_study and instance_reclamation
- **WHEN** the settlement stage sequence is inspected
- **THEN** it is exactly `("gauge_regen", "buff_ticks", "sexual_decay", "magic_study", "daily_resets",
  "caravan_arrivals", "shop_hours", "quest_deadlines", "npc_schedules", "instance_reclamation")`, in
  that order, with no duplicate or missing entry

#### Scenario: Transposing any of the four ordered stages is mechanically detected
- **WHEN** a test asserts `"buff_ticks"` appears strictly before `"sexual_decay"` and strictly after
  `"gauge_regen"` in the stage sequence, and `"magic_study"` appears strictly between `"sexual_decay"`
  and `"daily_resets"`
- **THEN** the assertion fails immediately if the stage sequence is ever edited to place any of these
  stages out of that relative order

#### Scenario: A transposed regen/buff order produces a different, incorrect final hp value
- **WHEN** a fixture entity starts with `hp` within one regen-step of its gauge `max`, an active
  `poisoned` buff, and a fixed elapsed time is settled once under the correct order (`gauge_regen`
  before `buff_ticks`) and once under a deliberately transposed order (`buff_ticks` before
  `gauge_regen`) constructed in the same test
- **THEN** the two resulting final `hp` values differ, because the regen-first order clamps against
  `max` on a step the buff-first order does not, proving the order has an observable, not merely
  documented, consequence

#### Scenario: No arithmetic transposition proof exists for magic_study, because it shares no
resource with its neighbors
- **WHEN** `magic_study`'s data dependencies are inspected (reads `entity.race`,
  `entity.skills.owned_keys()`, `entity.buffs`; writes only `entity.db.magic_xp`/
  `entity.traits.magic_level`) against `sexual_decay`'s (`entity.sexual`'s ordered-level fields) and
  `daily_resets`'s (`entity.sexual.climax_today` only)
- **THEN** no field is written by both `magic_study` and either neighbor, so the structural check above
  is `magic_study`'s only mechanical safeguard against transposition — this is a verified property, not
  an unexamined gap

#### Scenario: instance_reclamation running after quest_deadlines and npc_schedules reclaims within
one advance() call; running before either leaves the room existing for one extra call
- **WHEN** a test registers a synthetic `quest_deadlines` source that, when its deadline comes due
  within `(start_tick, end_tick]`, calls `unpin_instance_room()` on a target `InstanceRoom`, and that
  room is simultaneously due for TTL reclamation, unoccupied, unnamed, and pinned by exactly the
  reason the synthetic source releases
- **THEN** under the declared order (`quest_deadlines` before `instance_reclamation`), a single
  `advance()` call across both boundaries results in the room no longer existing; a test that
  constructs the transposed order (`instance_reclamation` before `quest_deadlines`) in isolation shows
  the same single `advance()` call leaves the room still existing, deferred, requiring a second call —
  an existence-differs proof, not merely a differently-ordered but equivalent outcome

#### Scenario: instance_reclamation position is not itself proof against every possible transposition,
and this is a stated, not silent, limitation
- **WHEN** `instance_reclamation`'s data dependencies are inspected (reads/writes `InstanceRoom.db.
  expire_tick`/`named`/`interacted`/`pin_reasons`/`owned_entities`, none of which any other stage reads
  or writes) against `caravan_arrivals`/`shop_hours`/`npc_schedules`, none of which has a registered
  source in this project's shipped codebase as of this change (and `npc_schedules`, once
  `instance_reclamation`'s own occupancy check was corrected during rubber-duck review to gate on
  `PlayerCharacter` rather than any `LivingEntity`, no longer has any concrete releasing mechanism this
  design depends on either — see design.md D-3's own correction note)
- **THEN** the transposition proof above is the sole mechanical safeguard for `instance_reclamation`'s
  position relative to `quest_deadlines` specifically; its position relative to `caravan_arrivals`/
  `shop_hours`/`npc_schedules` (all three still unregistered, no-op seams, and none with a concrete
  releasing story this design leans on) has no equivalent proof and is justified by "last, so nothing
  after it could still need the room" reasoning alone (design.md D-3), not by an arithmetic
  counter-example against any of the three
