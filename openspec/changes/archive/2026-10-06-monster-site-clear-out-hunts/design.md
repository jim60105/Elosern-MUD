## Context

See proposal.md — Why. Four facts shape the approach:

- Bound clearing already exists and is already strict: `QuestObjective.requires_bound_targets` with the
  record's `objective_target_ids` as the complete counting set (`world/quests/planner.py`), and
  `world/quests/binding.py::bind_stage_runtime` as the only binding writer, accepting entity-only bindings
  (`room=None` means no instance pin). What does not exist is any way for a hand-written definition to
  obtain bound targets: today only the scene materializer binds, and it does so to occupants it spawned
  itself (`world/quests/scene_builder.py::_spawn_occupants` spawns monsters for a tier-based DEFEAT stage).
- The authored sites are real and owned: `world/lore/monster_placement.py::_SITE_DECLARATIONS` declares
  `ridge_burrow_nest` (nest, western_hills_valleys, one-shot, capacity 2, burrow_maker + nest_guard),
  `cliff_echo_camp` (camp, recoverable after 86400 ticks, cliff_stepper + pass_warden) and
  `tide_mouth_boss_site` (boss_site, southeast_coast, one-shot, capacity 1, bay_warden).
  `world/maps/monster_sites.py` owns their lifecycle: it computes `_living_members` privately, keeps
  `state`/`cleared_at_tick` on the wilderness script, populates a site on the first clock settlement, marks
  a populated site cleared when no member is left alive, and recovers only through its authored in-game
  condition. Its module docstring states the constraint this design must obey: the lifecycle settles
  "never on room entry, quest acceptance, or elapsed wall-clock time".
- The acceptance-time guarantee exists for regional hunts only:
  `world/quests/runtime.py::_provision_hunt_targets` calls
  `world/maps/monster_provisioning.py::ensure_hunt_targets`, which reads the ambient rule, tops up within
  per-coordinate capacity, and refuses through a closed vocabulary, raising the shared
  `QuestTargetsUnavailable` that `commands/guild.py` and the board path already handle.
- The board filters by rank and orders by (rank, key) only (`world/rules/guild_offers.py`), and the docs
  describe `guild list` as listing offers open to the player's rank — a sentence that becomes inaccurate
  once availability can also hide an offer.

## Goals / Non-Goals

**Goals:** a lawful way for a hand-written definition to name an authored site; acceptance-time
availability that respects the site's lifecycle and never writes to it; stage-zero binding of exactly the
site's living individuals inside the acceptance transaction; a board that never advertises work acceptance
would refuse; three published clear-outs whose prose and rewards are authored; the docs corrected.

**Non-Goals:** no new `ObjectiveKind`; no instance scene for a permanent-layer clear-out; no spawn,
population, or recovery triggered by a quest, the board, or room entry; no change to the strict-binding
counter, the site lifecycle, the recovery conditions, or the ambient guarantee; no second clear-out over
one site; no site display-name vocabulary added to lore; no item reward.

## Decisions

**D-C1 A site clear-out is `requires_bound_targets=True` plus `site_key`, not a new objective kind.** The
completion mechanic is unchanged — count the bound individuals' defeats once per persistent identity — and
the strict-binding requirement already landed. A new kind would fork the planner, the binder, `describe`,
and the compile payload for one field pair. Reusing `destination` was rejected: a `RoomLocator` says
*where*, not *which individuals*, and it cannot express the site's ownership or capacity.

**D-C2 The acceptance guarantee is a read, never a write.** The site lifecycle forbids populating or
recovering a site at quest acceptance, so acceptance asks the site owner which of its own living
individuals stand and refuses when they are fewer than the quantity. Every no-supply condition refuses:
world not provisioned, unknown site, never-populated site, cleared site, and fewer living individuals than
required. The consequence is deliberate and documented: an authoring that wants a clear-out to be
repeatable must use a recoverable site, and a player who has already killed part of a nest sees the
clear-out refused as short rather than receiving a commission that could not be completed.
A fresh world is the sharpest case of the never-populated branch: sites are populated by the site owner's
own settlement on the world clock's first advance, so before that no site has living individuals and all
three clear-outs are absent from the board. That is the honest answer — the world's authored encounters do
not exist yet — and it resolves within the first clock-advancing action rather than at boot, because
populating a site from anywhere but the owner's settlement would contradict the lifecycle the site
placement change established. The refusal is named (`site_unpopulated`) so a player who names a key
directly is told what is missing rather than receiving a generic ineligibility.

**D-C3 Refusals reuse the landed named-refusal discipline.** The quest layer raises the existing
`QuestTargetsUnavailable` with the site key and one reason from the closed set `world_unavailable`,
`unknown_site`, `site_unpopulated`, `site_cleared`, `site_short`, so the board path, the command surface,
and the rejection mapping need no new handling.

**D-C4 The stage-zero binding happens inside the acceptance transaction, with no instance pin.** The
record is written first, then `bind_stage_runtime` binds exactly the site's living individuals as its
objective targets; the acceptance's existing snapshot/restore covers the quest log, and no room pin exists
by construction because no room is supplied. Rejected alternative: bind when the player first enters the
site. A permanent-layer stage has no scene entry — `commands/scene.py` materializes instance-layer stages
only — and writing quest state on room entry is precisely what the site lifecycle forbids; binding at
acceptance also tells the player what they must defeat before they travel.
Two mechanics are pinned because they are easy to get wrong: the operation SHALL return the persisted,
bound record (the log replacement the binder performs is the second full-log write inside the same atomic
block, so a caller that returned the earlier value would hand out a record with an empty target set), and
the snapshot/restore discipline stays sufficient here *only because* a site binding creates no instance
pin — a future binding that pins a room must extend the acceptance snapshot, and the task records that as
a comment at the call site. `quest_transition`'s bound flag is derived from a bound room, so a site-bound
record is observed through the new `hunt_site_targets_bound` event instead; that event stays even though
the board rule is a listing filter.

**D-C5 One availability read, owned by the quest layer, shared with the board.** The predicate is
definition-driven ("can this clear-out be accepted right now?") and lives in `world/quests/runtime.py`,
which already delegates to `world/maps/monster_provisioning.py` function-locally; `list_guild_offers`
calls that predicate rather than reaching into `world/maps/` itself. There is therefore exactly one answer
to the question, and the board cannot advertise what acceptance would refuse.

**D-C6 At most one registered definition may declare a given site.** Two clear-outs over one site would
both bind the same living individuals, so two records would credit the same defeats; registration rejects
the second definition rather than leaving a silent double-count to the planner. This is a registration
invariant, cheap to check against the registry.

**D-C7 The site's identity reaches the player through the definition's display name.** The objective
one-liner keeps the landed bound-target rendering rather than inventing a site display vocabulary
(`MonsterSite` carries no display name, and adding one is lore content this change does not own). The
board row carries the definition key, the authored display name (for example 清剿掘巢兔巢穴), the reward,
and the bound-target line; `guild show` renders the authored rationale and flavor. The player-visible
change this change *does* make is the offer set: a cleared site's commission is absent.

**D-C8 Rank and prose are authored for the arrangement.** The one-shot nest is `E` (a low-tier bound pair,
including the stronger guard, in a narrow entrance); the recurrable camp and the single boss are `D` — the
rank whose own description is party-based work and whose calibration matches "a party of ordinary
adventurers". The camp's strongest individual is danger-graded `C` and the boss is graded `C`; both hunts
stay `D`, so the shipped content again demonstrates that a danger grade never becomes a rank. No rationale
or flavor asserts one of the six unimplemented abilities: the crocodile flavor states the conflict at the
berth instead of restating the bestiary example's mana-loss symptom, and the goat prose describes narrow,
loose-scree terrain rather than rockfall.

**D-C9 Observability: two new catalog rows, and the read itself stays silent.** The successful guarantee
emits one info event on the enclosing durable commit, and the refusal emits one warn event immediately
(the existing ambient precedent: the refusal path always ends in a rollback, which would discard an
on-commit callback). Site, region, species, variant, required, available, and reason ride the context dict;
no player-facing prose enters a log. The site owner's new read decides nothing and therefore emits
nothing — the owner's existing `monster_site_populated` / `monster_site_cleared` /
`monster_site_recovered` events keep their own meanings.

**D-C10 The docs change with the behaviour they describe.** `docs/game/commands.md`'s `guild list` row and
`docs/game/command-reference.md`'s `guild list` section state that the board lists work that can be
completed now, so a cleared site's commission is absent until the site recovers; no key, alias, syntax, or
context row changes, and `tests/test_command_docs.py` stays green.

## The authored content

| definition key | display name | site | quantity | rank | copper / merit |
|---|---|---|---|---|---|
| `ridge_burrow_nest_clear_out` | 清剿掘巢兔巢穴 | ridge_burrow_nest | 2 | E | 250 / 60 |
| `cliff_echo_camp_clear_out` | 掃蕩回聲崖營地 | cliff_echo_camp | 2 | D | 1400 / 140 |
| `tide_mouth_boss_site_clear_out` | 清剿河口守灣鱷 | tide_mouth_boss_site | 1 | D | 1800 / 160 |

Each objective declares `requires_bound_targets=True`, its `site_key`, the quantity above, and no deadline;
each reward's copper sits inside its rank's band (`E` 100–500, `D` 500–5000).

Rating rationales (authored, composition and terrain only):

- nest: 據點入口狹窄，較強個體會擋在通道上；兩隻綁定目標必須一次清除，洞道又妨礙隊伍輪替。
- camp: 岩坡入口的營地，兩隻中階個體會守住通道；坡面狹窄、碎石鬆動，隊伍只能沿單側接近，撤退也不容易。
- boss: 單一個體，但佔據有遮蔽的泊岸入口；水深妨礙長兵器展開，近身纏鬥的風險集中在一次交手。

Background flavors (authored; the bestiary's example for the crocodile is restated without its
ability symptom):

- nest: 谷地的灌溉渠岸出現一整片加固過的土埂，渠水已被堵住。公會受託一次清出這個巢穴，讓下游恢復供水。
- camp: 採石場上方的營地再度聚集岩響山羊，運料路每天都有人被趕下山坡。業主請公會一次掃蕩整座營地。
- boss: 河口渡運站的側灣出現吞潮鱷，船員已停用該泊位。渡運站請公會清出這條水道，讓貨船重新靠岸。

## Event catalog rows to add

| event | context | level |
| --- | --- | --- |
| `hunt_site_targets_bound` | `site`, `region`, `species`, `variant`, `required`, `available` | info, on the enclosing durable commit |
| `hunt_site_targets_unavailable` | `site`, `region`, `species`, `variant`, `required`, `available`, `reason` (`world_unavailable` / `unknown_site` / `site_unpopulated` / `site_cleared` / `site_short`) | warn, emitted immediately, no persistent state changed |

## Risks / Trade-offs

- A one-shot site's clear-out is a once-per-world commission → intended: the site placement requirement
  already declares that a one-shot site stays cleared until an author re-issues it, and the board's
  availability rule is what keeps the two consistent instead of offering impossible work forever.
- A partially cleared site refuses the clear-out as short → documented (D-C2); the player completes the
  clearing they began and the site settles to cleared, which is the same outcome the commission
  wanted.
- The board now performs one site read per clear-out offer → bounded (three authored sites, and read-only),
  and it is the same read acceptance performs a moment later.
- A binding created at acceptance is a new lifecycle shape for a hand-written definition → it is the
  established binder with an entity-only binding, inside the acceptance transaction, and the delta
  restates the guarantee as a scenario per refusal path so a regression is a test failure rather than a
  silent partial state.
- One kill can legitimately credit two records: a site's individuals are ordinary species individuals, so
  defeating one advances both its bound clear-out and any active regional hunt of that species. That is
  intended (each record credits each persistent identity once) and the implementer SHALL NOT "fix" it by
  excluding another owner's individuals.

## Open Questions

None. A site display-name vocabulary, a richer recovery predicate, and any ability mechanics remain other
work's scope.
