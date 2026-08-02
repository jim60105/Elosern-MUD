## Context

A newly activated character is left standing in `Limbo` with no introduction and no guidance. The
world already provides the full deterministic first-day arc (guild registration, the 討伐低階魔物
quest, wilderness combat, turn-in), but nothing delivers the player to it. This change adds the
scripted arrival and the guard guide, plus the onboarding state that completes at the first hunt
turn-in. Everything must be deterministic and offline-playable.

## Goals / Non-Goals

**Goals:**
- Teleport a newly activated character to the South Gate of 聖潔王都 via the deterministic movement
  path.
- Play an authored arrival scene (the first event) and run a guard guide teaching `look` and movement
  toward the guild.
- Provide a deterministic `talk` command with a scripted keyword→response table on the guard.
- Persist onboarding state (`onboarded`, `onboarding_beat`, `guide_progress`, `first_arrival_seen`)
  written only through `world.rules/onboarding.py`.
- Hand off to the existing first-day arc; complete onboarding at the first 討伐低階魔物 turn-in.

**Non-Goals:**
- No LLM or image-service involvement anywhere in the flow.
- No new NPC typeclass; no combat changes; no quest, guild, shop, or clock mechanic changes.
- No generative dialogue (that is change 19, which uses the `NPC.dialogue_memory` seam).

## Decisions

**D1 — Arrival data is an immutable beat registry under `world/onboarding/scenes.py`.**
Each beat is a frozen dataclass: `beat_id`, prose (Traditional Chinese), a trigger kind
(`COMMAND_LOOK` / `ENTER_ROOM`), and the next-beat continuation. The arrival scene is a short
sequence; the `look` beat advances to the guidance beat. The module also declares the guided corridor
as a constant set of room keys (`GUIDED_CORRIDOR = {南門, 南大道, 中央廣場, 冒險者公會外}`), expressed
as data so the skip rule is testable and map-editable. No imports from `world.rules` anywhere in this
module.

**D2 — `world/onboarding/guide.py` is a pure coordinator, never a state writer.**
It exposes functions like `next_beat(state) -> BeatOutput | None` that take plain dataclasses (the
read snapshot of onboarding attributes) and return prose/prompts plus the requested state transition.
`GuideProgress` is a frozen dataclass with an explicit schema: `state: "active" | "completed" |
"skipped"` and `seen_keywords: tuple[str, ...]`; it serializes to the `guide_progress` attribute only
through the rules service. `guide.py` imports only the onboarding data modules and Python stdlib.
`world/rules/onboarding.py` is the only module that reads Evennia attributes, calls `guide` with a
snapshot, and applies the resulting writes. This breaks the would-be package cycle
(`rules → onboarding data` and `onboarding → rules`) in favour of `rules → onboarding data` only,
preserving the single-writer invariant.

**D3 — `world/rules/onboarding.py` is the sole state service.**
Public API:
- `relocate_to_starting_location(character)` — a best-effort relocation to 南門 performed ONLY after
  a successful activation commit. It never rolls activation back on failure, never advances the world
  clock, and emits no player-move EventLog (it is not a player action). If 南門 is missing the shell
  stays put and the player receives a degradation notice instead of the arrival welcome.
- `maybe_play_arrival(character)` — plays the arrival scene when the character is onboarding, at the
  South Gate, and has not completed the arrival beat. Invoked after relocation, from the extended
  `Account.at_post_login`, and from the South Gate room-entry observer.
- `advance_beat(character)`, `mark_guide_skipped(character)`, `set_onboarded(character)`.
- `observe_room_entry(character)` — the single room-entry observer: if the character is onboarding, a
  deviation into a room outside `GUIDED_CORRIDOR` marks the guide skipped, and arrival at
  冒險者公會外 completes guidance. Precise coordinate/room-key checks live in the service.
- `talk_response(npc, character, keyword)` — validates the component, looks up the table, returns
  prose, updates `guide_progress.seen_keywords`.
- `sync_guard_npc()` — idempotent startup creation of the guard.

**D4 — The guard is an `NPC(LivingEntity)` with an `OnboardingGuide` component.**
The component follows the `GuildStaff`/`Merchant` pattern: a capability marker holding stable
identity data (`dialogue_key` pointing at the table in `world/onboarding/guide_dialogue.py`). Per-player
guide progress stays on the player character, owned by the rules service. The component name encodes
intent (onboarding), leaving room for the same NPC to gain unrelated dialogue later. Created by
`sync_guard_npc()` with a stable key/tag; the guard persists its adult identity (`age >= 18` and
`apparent_age >= 18`) as attributes asserted by the sync test, upholding the project-wide adult
invariant. Registered in `server/conf/at_server_startstop.py::at_server_start` next to the other
syncs.

**D5 — `CmdsTalk` dispatches through the rules service.**
Syntax: `talk <npc>` shows the guard's current topic plus the guidance line; `talk <npc> <keyword>`
yields that keyword's authored response. Missing or ambiguous target, a non-NPC target, and an NPC
without a dialogue component each produce a distinct error/no-response line. An unknown keyword on the
guard yields the no-understanding line. No dialogue state is stored on the NPC.

**D6 — Onboarding completes inside the existing turn-in transaction.**
`world/rules/guild.py::turn_in_quest` already atomically settles reward claims inside one transaction
with a snapshot/restore pattern. The onboarding completion for the `introductory_hunt` quest is
written INSIDE that same transaction and rollback scope, so a failure rolls back the claim together
with `onboarded` — never leaving a "claimed but not onboarded" state. `ALREADY_CLAIMED` already blocks
double settlement, so the completion (and its closing line) fires at most once.

**D7 — Reconnect replays only the arrival beat.**
The extended `Account.at_post_login` calls `maybe_play_arrival` for a character at the South Gate
whose arrival beat is incomplete. Completed beats and `guide_progress` are untouched, so no line is
ever said twice.

**D8 — Guard interaction is not combat.**
The guard has no combat component, so `engage` targeting rejects it under the existing rules; no
special case is added.

**D9 — The `look` beat completes through a `PlayerCharacter.at_look` seam.**
`PlayerCharacter.at_look` is overridden to detect a successful look while the character is onboarding
at the South Gate with the arrival beat active; it then calls `advance_beat` and appends the guidance
prompt to the returned look text. The service guards on room + state, so a look elsewhere (or a look
that fails) never advances the beat.

**D10 — Room entry is observed once, through the existing room mixin.**
`GridRoom` already runs `QuestObservableRoomMixin` on player entry. The onboarding service is reached
from the same entry path (`GridRoom.at_object_receive` after the quest observer), with the service
deciding what 南門/公會外/corridor entries mean — no per-room monkey-patching and no missed entry
paths.

## Risks / Trade-offs

- [Arrival scene firing repeatedly] → Guarded by `first_arrival_seen` (set on `look` completion) plus
  the `onboarded` flag; a returning, onboarded player at the gate never sees it.
- [`guide.py` accidentally importing rules and re-creating a package cycle] → Enforced by dependency
  direction and checked in review: `guide.py` and the data modules import nothing from `world/rules`,
  `typeclasses`, or Evennia.
- [Startup sync ordering] → `sync_guard_npc()` runs after `sync_grid()` in `at_server_start` so the
  South Gate room exists; if it does not, the sync logs a warning and skips (guidance degrades, arrival
  does not).
- [Turn-in hook coupling] → The onboarding service is called by `turn_in_quest`, not the reverse; the
  onboarding write lives inside the same transaction and rollback scope, so guild settlement semantics
  are unchanged and partial state is impossible.
- [Skip rule coupling to map topology] → The guided corridor is data (`GUIDED_CORRIDOR`), testable per
  room, and adjustable if the city layout changes; the service owns the precise room-key checks.
