## Context

Two authored-guidance defects break the new-player arc.

1. **Wrong direction.** The `capital_altoria` xyzgrid places the guild exterior
   冒險者公會外 at `(3, 1)`, one block **east** of 南大道 `(2, 1)`; the player
   starts at 南門 `(2, 0)`. The correct route is north to 南大道, then east.
   The guard's authored `GUIDANCE_BEAT` prose, the 公會 keyword response, and the
   新手引導 help entry all tell the player to go north *through* 中央廣場 — a
   route that leaves the guild behind and is not map-accurate.
2. **No guild-staff dialogue.** The guild master NPC carries `GuildStaff` and
   `GuildExaminer` components but no dialogue component, so `talk` yields the
   generic "對方沒有理會你" line and a new player never learns the `guild *`
   commands exist.

The existing `talk` command (`commands/talk.py`) already resolves NPCs in the
caller's room and answers only `OnboardingGuide` hosts via
`world/rules/onboarding.py`; `guide_dialogue.py` is explicitly a *keyed*
dialogue-table home designed for reuse on any NPC.

## Goals / Non-Goals

**Goals:**

- Make every authored piece of guidance point to the guild correctly: north to
  南大道, then east to 冒險者公會外.
- Let the guild master answer `talk` and teach the guild commands
  (`guild register`, `guild list`, `guild accept`, `guild log`, `guild show`,
  `guild turnin`, `guild abandon`, `guild merit`), including a no-keyword
  greeting/topic line.
- Keep the guard's onboarding behavior (guide prompt, keyword tracking on
  `guide_progress`) byte-for-byte intact.

**Non-Goals:**

- No change to the city map, `GUIDED_CORRIDOR`, or guidance completion/skip
  semantics.
- No generative/LLM dialogue (change 19 owns that seam).
- No new quest, guild-economy, or rank mechanics.

## Decisions

**D1 — Correct direction via the map, not the prose.**
The grid is authoritative: 南門 → north → 南大道 → east → 冒險者公會外. Every
authored line uses the unambiguous route "先向北到南大道，再向東到冒險者公會外"
(never "沿著南大道往北", which implies continuing north toward the plaza).
`GUIDANCE_BEAT` prose, the 公會 keyword response, and the 新手引導 help entry are
rewritten to state that route. `GUIDED_CORRIDOR` is unchanged (it already
contains every room on the direct path). Because this amends the onboarding
design doc's Beat 5 ("north to the plaza and the guild") as the map wins for the
actual route, the change explicitly amends
`docs/superpowers/specs/2026-08-02-player-onboarding-design.md` (Beat 5 and the
§3 player journey) to record the two-step route.

**D2 — A generic `ScriptedDialogue` component and a richer immutable table.**
New `ScriptedDialogue` component (`name="scripted_dialogue"`, `dialogue_key`
DBField) in `typeclasses/components.py`, sibling to `OnboardingGuide`. The
dialogue-table registry in `world/onboarding/guide_dialogue.py` changes its value
type from `tuple[KeywordResponse, ...]` to a frozen
`DialogueDefinition(greeting: str | None, responses: tuple[KeywordResponse, ...])`
so a host can own both a no-keyword topic line and its keyword responses in one
immutable value. `dialogue_response`/`dialogue_has_keyword` read the
`responses` tuple; a missing `dialogue_key` resolves to the no-understanding
line. The guard's definition uses `greeting=None` (its no-keyword line is the
stateful guide prompt); the `guild_staff` definition carries a static greeting
that teaches the guild commands. Missing greeting on a generic host falls back
to the no-response line for no-keyword `talk`.

**D3 — A single read-only dialogue resolution service.**
New `world/rules/dialogue.py` is the single lookup point: it owns component
resolution (`resolve_dialogue_component(npc)`, `is_dialogue_host(npc)`,
`dialogue_key_for(npc)`), the keyword lookup (`dialogue_response(npc, keyword)`),
and `greeting_for(npc)`. It performs no writes (single-writer invariant
untouched). The guard's stateful behavior stays in `world/rules/onboarding.py`:
`talk_response` calls the same `dialogue.py` lookup for the guard, then records
the seen keyword on `guide_progress` only when the keyword is known and the host
is an `OnboardingGuide`. Dependency direction stays `rules -> onboarding`; no
cycle.

**D4 — `talk` branches on the host type.**
`commands/talk.py`: keyword present → both guard and generic hosts resolve
through the shared `dialogue.dialogue_response` lookup; for the guard the
onboarding service additionally records seen keywords. No keyword → guard shows
the active guide prompt, a `ScriptedDialogue` host shows `greeting_for(npc)`
(falling back to the no-response line when the greeting is None), and an NPC
with no dialogue component still gets the no-response line. Unknown keywords
still yield the no-understanding line with no state change.

**D5 — Idempotent sync attachment.**
`world/rules/guild_economy.py` `sync_service_content()` attaches
`ScriptedDialogue(dialogue_key="guild_staff")` to the guild master's component
specs. Component attachment is by name, so repeated startup never duplicates.

**D6 — Cross-change dependency.**
The `guild_staff` taught-command list includes `guild show`, which is introduced
by the separate change `guild-quest-detail-view`. This change declares that
dependency: it SHALL be applied and verified only after `guild-quest-detail-view`
has been implemented and validated, and an integration test asserts every taught
command resolves to a registered command. If the dependency cannot be satisfied,
`guild show` is omitted from the taught list.

## Risks / Trade-offs

- [Two dialogue components drift apart] → One `DIALOGUE_TABLE` registry plus a
  single resolution point in `world/rules/dialogue.py`; each component only
  carries a `dialogue_key`.
- [Guild dialogue data living in `world/onboarding/`] → Accepted legacy naming;
  the module is the established keyed dialogue-table home. A future refactor may
  relocate the registry without behavior change.
- [Table value type change breaks existing guard callers] → `guide.py`'s
  `dialogue_response`/`dialogue_has_keyword` and the onboarding tests are
  updated together in the same change; the guard's table gains `greeting=None`
  so its behavior is unchanged.
- [Prose rewording breaks tests asserting the old direction] → Data/journey
  tests are updated to assert the unambiguous two-step route and a map-path
  check (南門 → 南大道 → 冒險者公會外); the guard's guide-prompt mechanism is
  untouched.
- [Change B teaches `guild show` before it exists] → Declared dependency on
  `guild-quest-detail-view`; an integration test asserts every taught command is
  a registered command, and `guild show` is omitted when the dependency is
  unavailable.
- [New component on the guild master] → Sync attaches by name and is idempotent;
  `guild` commands and service resolution are unaffected.
