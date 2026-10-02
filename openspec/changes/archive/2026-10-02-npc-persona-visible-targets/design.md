## Context

See proposal.md for P2-2. Current `_check_admission` (`npc_persona_actions.py:200–213`) retains possession/mode gates and uses `_present_by_id`; the shared resolver (`exploration_actions.py:335–342`) scans raw room contents. The current publication function is `_interact_targets` (`presentation/exploration.py:525–661`), not the review's historical `_interact_entries` name: its `present` list scans raw contents before sorting/capping. Editor data includes hidden identity and must not be constructed for a hidden target.

The installed Evennia 6.1.0 `DefaultObject.filter_visible` (`.venv/lib/python3.13/site-packages/evennia/objects/objects.py:1614–1635`) calls `obj.access(looker, "view")` and `obj.access(looker, "search", default=True)` and excludes the looker. Its `access` signature has default=False (1589–1590): the review's shorthand "view and search defaultTrue" is not the exact installed method. Do not recreate lock semantics or pass a permissive view default; use the existing room hook verbatim, including project overrides and ordinary configured view access. Explicit denied view OR search hides the target; an absent search lock remains permissive under the stock hook.

## Goals / Non-Goals

**Goals:** One canonical visible-room candidate policy for NPC editor admission and interaction publication, re-evaluated with the currently owned active actor each request.

**Non-Goals:** No custom invisibility mechanic, builder-only editor, view/search lock rewriting, schedule gating for author edits, global service authorization overhaul, or frontend-only authorization.

## Decisions

### Reuse room visibility filtering, not a new permission predicate

Use `location.filter_visible(location.contents, actor)` in the shared presence resolver and in `_interact_targets` candidate collection. Filter before sorting or MAX_INTERACT_TARGETS slicing so hidden objects neither leak ids/names/portraits nor crowd out visible targets. Keep `_present_by_id` as the shared imported seam; do not add an alternate unfiltered resolver or cached visibility token. Other id-based exploration actions that already depend on this helper therefore also reject hidden targets using their existing missing-target outcomes. Audit these consumers for intentional actor/self handling; the helper is for other room targets, not actor authorization.

The necessary local-host selection (`_resolve_single_host` in `presentation/affordances.py`) must select from the same visible candidates when it supplies per-target guild/shop navigation. Otherwise an invisible second host can make a visible host look ambiguous. Limit that adjustment to local candidate filtering; do not redesign remote service panels or schedule/capability rules.

### Preserve admission and fail closed without disclosure

Keep dispatcher session → activated account-owned puppet admission, possession rejection, and exploration/dialogue mode checks. NPC-family validation remains after current visible co-location resolution; Monster, player and arbitrary object ids remain invalid. Both read and update resolve immediately before card access/writer invocation, even if the draft opened while visible. Return existing `npc_persona.no_target` and generic missing-target message for hidden, remote, departed, deleted or unknown ids; no `data`, target description, greeting or version. Rejected saves leave all persisted persona/greeting/version state unchanged. Do not call `is_card_available` for excluded targets merely to publish a disabled row.

Author access remains independent of awake/talk schedule, relationship and service role. Sleeping but visible NPCs remain editable; invisible NPCs do not receive a disabled author row announcing their existence.

## Risks / Trade-offs

- [Shared helper affects other local target actions] → Exercise affected talk/deliver/invite/engage presence paths and preserve their existing capability/schedule gates and rejection codes; avoid unrelated action rewrites.
- [Tests use toy rooms without visibility hooks] → Use real room/lock-backed fixtures or meaningful supported test doubles implementing the policy; no production fallback that admits unfiltered content.
- [Publication cap masks visible NPCs] → Regression places denied targets before allowed ones and verifies allowed targets still publish within the cap.
- [Lock/default confusion] → Installed hook is authoritative; test explicit view denial, explicit search denial, and omitted search lock with ordinary allowed view. Respect subclasses that override the hook.

## Migration Plan

No persisted data or schema changes. Apply as a scoped server admission/presentation fix; existing editor drafts may become unavailable under current visibility, which is intended. No migrations or cutover. Companion characterization and player persona APIs remain unchanged.
