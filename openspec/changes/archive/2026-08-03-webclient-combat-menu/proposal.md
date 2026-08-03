## Why

Persistent combat already pauses for one deterministic player action, but the player must know skill keys and target names before acting. With the OOB foundation now complete, the next approved UI slice can expose every legal combat choice without duplicating rules in the browser or granting it capabilities unavailable to Telnet.

## What Changes

- Add a versioned `context_actions` combat panel that presents the active session, participants, owned active skills, exact costs and target shapes, rule-derived availability, stable disabled reasons, and deterministic menu order.
- Register allowlisted `combat.cast`, `combat.flee`, and confirmed `combat.forfeit` UI actions that re-resolve session and participant identities, then call the existing deterministic combat-session APIs.
- Add the keyboard-first Attack, Skills, target-selection, Flee, and secondary Forfeit flows; keep Items and Defend visible but disabled, preserve narrative EventLog output, and restore canonical combat state after reconnect.
- Add a shared side-effect-free combat preview surface built from the resolver's existing validation stages, including zero-action capability and valid-target discovery, without rolling, staging effects, emitting logs, advancing time, or mutating state.
- **BREAKING** Replace the combat-session facade's single optional target with an explicit target list or approved AREA shorthand. Update all callers directly; add no compatibility overload.
- Tighten player-facing combat target validation so NONE and SELF accept no client-supplied target, SINGLE accepts exactly one explicit target, AREA accepts a nonempty unique list or one approved shorthand, and malformed shapes reject before initiative while existing trusted SELF `ActionRequest([actor])` callers remain valid.
- **BREAKING** Extend immutable skill definitions with bounded Traditional Chinese labels and short effect descriptions used by both browser and Telnet presentation. Update all definitions and constructors directly; add no legacy metadata path.
- Add Telnet `combat actions`, stable session-local `aN`/`eN` target tokens, comma-separated token targets, and the existing AREA shorthands while retaining one-target name search.
- Extend deterministic Node, Evennia, and managed Playwright gates for all target shapes, disabled reasons, duplicate/stale submissions, narrative delivery, viewport behavior, and active-combat reconnect.

## Capabilities

### New Capabilities
- `webclient-combat-menu`: Defines the combat panel schema and presenter, allowlisted combat adapters, keyboard menu hierarchy, reconnect behavior, EventLog delivery, Telnet-visible parity, and browser acceptance boundary.

### Modified Capabilities
- `player-combat-session`: Changes player submission to explicit target lists or approved AREA shorthands and adds stable Telnet participant tokens and action discovery while preserving one-round orchestration and settlement.
- `targeting-validation`: Enforces exact target shapes, rejects duplicate explicit targets, restricts shorthand to AREA, and distinguishes malformed AREA input from an expanded set with no valid targets.
- `action-resolution-pipeline`: Adds a shared side-effect-free preview query that exposes resolver-owned availability and target validation without weakening final preflight or resolution.
- `skill-registry`: Adds immutable bounded player-facing skill labels and effect descriptions while retaining registry ownership of targeting, cost, element, and effect metadata.
- `webclient-action-dispatch`: Replaces the foundation's mutation-empty production registry contract with the first three exact, allowlisted gameplay adapters.

## Impact

The change affects `world/rules/combat_session.py`, resolver/targeting preview seams, immutable skill definitions, `commands/action.py` and combat command help, the WebClient presentation and action registries, action-dock JavaScript/CSS, and Node/Evennia/Playwright tests. It reuses the locked Playwright dependency, isolated browser harness, OOB epoch/revision protocol, persistent combat records, and deterministic APIs; it adds no runtime dependency, database migration, LLM call, image-service call, mobile scope, or backward-compatibility layer.
