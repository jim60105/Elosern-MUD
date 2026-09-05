# Design: companion-possession-webclient

Source design: `docs/superpowers/specs/2026-09-05-companion-possession-design.md` (D9, D10, §4
Presentation, §5). Changes 6/7 settled state and control; this design covers only how the Vue
webclient shows and drives possession without laundering A-keyed state through B's hands.

## D-W1: Honest hybrid is a banner requirement, not a panel fork
Panels keep their existing schemas and existing presenters. The wallet/quest/guild/status panels
keep reading the **acting account's character A** — not the session actor — because NPCs own none
of those fields; forking presenters to "unavailable while possessed" would hide information the
player legitimately owns and would break the three-allowlist panel contract for zero benefit. The
banner is what makes this honest: it is part of the snapshot, persists while possessed, and names
whose eyes the player is looking through. Tasks pin this by asserting the wallet payload while
possessing equals A's payload byte-for-byte plus a simultaneously-available banner.

## D-W2: Inventory/equipment need no new adapter — the actor-keyed path already works
`toggle_equip`/inventory presentation keys off the session actor, which during possession IS the
possessed NPC, and `toggle_equipment` already works on any `LivingEntity`. The hybrid is
therefore asymmetric by construction: A-keyed panels (wallet, quests, guild, status) read the
possession mirror's owner; actor-keyed panels (inventory, equipment, the map, the room) follow
the puppet automatically. No new read-model adapters — v1 ships with zero new presentation
surfaces beyond the banner.

## D-W3: Banner is a new registered panel, not a payload field on every panel
A `possession_banner` panel (schema v1, `available`+`host_name`+`since_tick`) rides the existing
presentation registry, so the server validator, the UMD mirror, and the Vue store mirror gain it
in lockstep (the three-allowlist contract test enforces this), and it re-pushes on the possession
seams the same way `party` re-pushes on membership seams. Adding a field to each existing panel
would bump several schema versions for one string.

## D-W4: Gate verdicts render from one shared evaluator
The affordance builder calls `world/rules/possession.py`'s gate evaluator (the same function
`enter_possession` uses — it must be exposed as a pure verdict function by change 6's writer or
tasks add the seam there) instead of re-implementing gate logic client-side; disabled_reason
codes/messages are the writer's registry entries, so the drawer, the exploration panel, and the
dispatch-time rejection can never disagree. Shop/talk/engage refusals follow the same rule:
adapters ask the rules side, never guess.

## D-W5: Refusals are adapter-level, stable codes, zero-write
`possessed_shop`/`possessed_talk`/`possessed_engage` rejection checks live inside the adapters
(after envelope validation, before any state read) so the epoch-guarded result contract is
inherited unchanged and the rejection cannot race the presentation transition. Vocabulary-side
disabled entries and adapter-side refusals assert the same verdict function, one source again.

## D-W6: The two action codes are party-actions for the suggestion layer
`SUGGESTIBLE_ACTION_IDS` is an exact enumeration; the possession codes do not join it, so the AI
proposal ladder and `default_cards()` deterministically never propose possession — matching the
design's "party actions are never suggestions" precedent with no new filter code.

## Cross-change seams
- Change 6 (`companion-possession-rules`): owns the gate evaluator and release writer this change
  calls; if the pure verdict function is not exposed there, this change's first task adds it as
  a read-only extraction (no behavior move).
- Change 7 (`companion-possession-transition`): owns the puppet/epoch sequencing; this change
  only consumes `send_unpuppet_transition`'s already-pushed transition and the re-pointed actor.
- multichar-05 (TopBar switcher, landed): the banner renders in the shell's top region beside the
  switcher; the switcher while possessing follows the multichar retirement semantics — switching
  OOC while possessing fires A's disconnect-equivalent release through the change-7 hook.
  Pinning test, no new logic.
