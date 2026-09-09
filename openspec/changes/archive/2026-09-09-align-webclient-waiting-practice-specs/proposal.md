# Change: Align waiting and practice specifications with the shipped WebClient

## Why

`feat/webclient-obsidian-gold` shipped a three-operation waiting selector, an hours-based rest form, and a graphical declared-practice flow. The implementation passes its tests, but the corresponding main specifications still describe the previous surface or remain silent, so they would now fail if verified against the shipped client:

- `webclient-action-dispatch` enumerates an allowlist of registered actions that omits `explore.practice` (shipped by this branch) and `explore.deliver` (already present on `master`).
- `webclient-exploration-menu` still requires the waiting menu to offer four daypart boundaries; the player surface now offers dawn, full-recovery sleep, and a bounded custom-hours form.
- The graphical practice contract—`explore.practice`, its payload and rejection rules, and its skill-book entry point—has no requirement despite being a player-visible path that mutates world time and skill progression.
- The contextual HUD requires the skill-book drawer to *always* carry its cast-syntax footer, but the shipped practice screen deliberately hides it while that sub-screen is open.

This change is a specification reconciliation only. It changes requirements to describe the implemented, tested behavior; it deliberately does not weaken or alter the deterministic clock, safety gate, practice preflight, or whole-hour settlement rules, all of which the implementation already reuses.

## What Changes

- Expand the registered-action allowlist in `webclient-action-dispatch` to name both `explore.deliver` and `explore.practice`, and correct the stale “twelve exploration adapters” count in `webclient-exploration-menu` purpose text.
- The exhaustive-enumeration clause forced a full reconciliation: the shipped registry carries 40 action IDs, while the main spec lists 34 (it also silently missed `account.character.create`, `account.character.switch`, `creation.roll_name`, and `guild.quest_track`, a pre-existing `master` drift). The amended requirement and scenario list the complete authoritative set, equal to the dispatcher test's enumeration.
- Require the exploration waiting selector to present exactly:
  - 等待直到黎明,
  - 睡眠至完全恢復, and
  - a bounded custom-hours form.
- Require the custom form to accept hours, including fractional hours, convert to whole seconds once at the presentation boundary, and retain the authoritative server-side 1-second-to-12-hour bounds and clock ownership.
- Add the graphical practice contract:
  - the registered `explore.practice` action,
  - exact `{skill, seconds}` payload validation,
  - stable unknown/capped rejection before any clock advance,
  - skill-book discovery through the 修煉 screen, and
  - feedback that preserves the server-authored result.
- Clarify the contextual-HUD skill-book footer contract: the cast-syntax footer is always present in the skill book itself, while the nested practice sub-screen replaces the book and therefore does not display it.

Out of scope:
- Removing or restricting server-side daypart support; midnight, noon, and dusk remain valid `explore.wait` payloads for text commands and other authored surfaces.
- Any change to rest/sleep/wait text-command behavior.
- Any change to game rules, pricing, settlement, safety decisions, or the single-writer boundary.
- The separate visual-theme and navigation drift covered by `align-webclient-shell-theme-navigation-specs`.

## Capabilities

- `webclient-action-dispatch`
- `webclient-exploration-menu`
- `webclient-contextual-hud`

## Impact

- Spec: `openspec/specs/webclient-action-dispatch/spec.md`
- Spec: `openspec/specs/webclient-exploration-menu/spec.md`
- Spec: `openspec/specs/webclient-contextual-hud/spec.md`
- Verification only: the existing Python action, dispatcher, shell, store, and component suites that already exercise the shipped paths. No implementation files are planned to change.
