# Spec Delta

## MODIFIED Requirements

### Requirement: A possessed NPC is autonomy-silent and unreachable by dialogue
An NPC with `db.possessed_by` set SHALL be autonomy-silent: `world/rules/service_gate.py::schedule_silenced(npc)` SHALL return true for it as the predicate's OR-ed second trigger, so `settle_npc_schedules` moves or re-states nothing for it; `LLMNPC.at_talked_to` (and the freeform dialogue seam behind it) SHALL refuse the possessed self with the fixed 「他現在無法回應你。」line and write no dialogue, memory, or affinity state.

This self-dialogue refusal SHALL NOT prohibit lawful authored conversations with a different present host. A lawfully controlled companion SHALL speak such scenes with its own body and portrait while the owner carries the session's relationship and reading identity, as specified by `authored-dialogue-possession`.

#### Scenario: The possessed companion's schedule stays silent
- **WHEN** a possessed guard-type companion crosses a full authored shift window
- **THEN** no entry settles, no event names it, and its state is unchanged

#### Scenario: Talking to the possessed self is refused without state
- **WHEN** the player (on character A) talks freely to companion B while possessing B
- **THEN** the fixed refusal line shows and no dialogue session, memory append, or affinity change occurs

#### Scenario: Possessed-companion combat still credits the owner's quest
- **WHEN** the possessed companion lands the killing blow on a quest-tracked monster
- **THEN** the owning player's quest progresses exactly as if the companion fought unpossessed

#### Scenario: The silence trigger rides the single service-gate site
- **WHEN** `schedule_silenced(npc)` evaluates a possessed NPC
- **THEN** possession is the predicate's OR-ed second trigger at the same single site the
  place-bound travel trigger lives

#### Scenario: Possessed-companion exploration keeps crediting the owner
- **WHEN** a possessed companion produces exploration results
- **THEN** they keep crediting the owning player's quests exactly as for any bound companion —
  a ratified feature: possession moves the camera, not the ownership

#### Scenario: Authored conversation with another host remains lawful
- **WHEN** a lawfully controlled possessed companion selects an authored topic of a different present host
- **THEN** the complete scene plays with the companion's name and portrait, host affinity changes only for the owning player, and the freeform self-dialogue refusal above stays in force
