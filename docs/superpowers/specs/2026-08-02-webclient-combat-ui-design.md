# WebClient Combat UI — Focused Design

**Date:** 2026-08-02
**Status:** Approved as part of the Browser-First MUD WebClient Suite
**Parent:** `2026-08-02-webclient-ui-design.md`
**Delivery unit:** `webclient-combat-menu`
**Depends on:** `webclient-oob-foundation`, existing persistent player combat sessions

---

## 1. Intent

Combat currently pauses correctly for player input, but the player is told to type a skill key without
being shown what the character owns. This unit makes one player-selected action per round discoverable
and keyboard-operable without creating a second combat system. Every choice remains an ordinary
`ActionRequest`, every rejection remains preflight-driven, and every terminal outcome remains the
existing persistent combat-session outcome.

---

## 2. Goals and Non-Goals

### Goals

- Show the complete owned active-skill list in stable stored order.
- Show costs, target shape, element/effect description, enabled state, and disabled reason.
- Support innate basic attack and flee.
- Support NONE, SELF, SINGLE, and AREA target flows.
- Expand the player combat-session facade from one optional target to an explicit target list or
  approved area shorthand.
- Give Telnet equivalent multi-target syntax.
- Keep HP/MP/SP and applied combat modifiers visible while choosing.
- Restore the same menu after disconnect/reconnect.
- Preserve preflight atomicity, initiative, NPC policy, overwhelm, examination nonlethal behavior, and
  one-time clock settlement.

### Non-Goals

- No client-side damage preview or hit percentage.
- No new defend mechanic.
- No combat item-use mechanic.
- No automatic player policy or auto-battle.
- No change to initiative, damage, status, flee, or overwhelm formulas.
- No drag-and-drop hotbar in this unit.

---

## 3. Combat Panel Model

The combat presenter reads the active `CombatSessionRecord`, reconstructs the battlefield through the
existing validated path, and emits:

- session ID, mode, round count, and whether input is expected;
- player status summary and active rule-provided modifiers;
- living/fled/knocked-out participants with opaque identity, team, display name, HP summary, and portrait
  subject key where allowed;
- the root action descriptors;
- the owned active-skill descriptors;
- valid target candidates or a stable reason that target selection is unavailable;
- terminal/paused/recovery diagnostics when the session cannot accept input.

The presenter is side-effect-free. A factored read-only preview API reuses `ActionResolver` validation,
but never rolls, stages effects, emits EventLogs, advances time, or writes session state.

### 3.1 Preview strategy

Availability is derived from the same validation functions as execution:

1. ownership and active skill kind;
2. combat-context legality;
3. resources;
4. action capability;
5. target candidates by target specification and faction constraint;
6. registered effect handlers and required metadata.

The implementation factors shared pure validation rather than copying formulas into a presenter.
Target-specific validation can be evaluated lazily when the player enters a target submenu. Skill lists
and participant lists are bounded by protocol limits.

---

## 4. Menu Hierarchy

### 4.1 Root

| Entry | Behavior |
|---|---|
| Attack | Open valid enemy targets for innate `basic_attack` |
| Skills | Open all owned active skills in stored order |
| Items | Disabled with `not_implemented` in this suite |
| Defend | Disabled with `not_implemented` in this suite |
| Flee | Submit innate `flee`, using its existing resolver target behavior |

A secondary menu contains Forfeit. Forfeit is not presented beside Flee because it does not attempt a
resolver-backed escape; it settles defeat or examination failure. It requires a confirmation screen.

### 4.2 Skill list

Each entry contains stable skill key, localized display label, kind, resource cost, target spec, element,
short effect description, enabled state, and disabled reason. The registry remains the source for static
facts. Current status and preflight provide dynamic facts.

Skills remain in stored order and are paginated. Passive skills never appear here. A disabled skill can
receive focus and expose its reason in the detail pane. Enter on it is a no-op and sends no packet.

### 4.3 Targets

| TargetSpec | Selection contract |
|---|---|
| NONE | No submenu; submit empty target list |
| SELF | Show actor binding; send no target field and let the server bind the session puppet |
| SINGLE | One focused valid candidate; Enter submits exactly one ID |
| AREA | Space toggles valid candidates; Enter submits explicit IDs; each applicable approved all-target shorthand is a separate server descriptor |

The browser never accepts a typed dbref in the graphical flow. Candidate IDs come from the presenter but
are still untrusted when returned. Dispatch reconstructs the active battlefield and verifies presence,
alive state, range, faction, cardinality, and duplicates.

The `combat.cast` payload has one shape per registry target spec:

- NONE and SELF contain `skill_key` and neither target field;
- SINGLE contains `target_ids` with exactly one opaque ID and no shorthand;
- AREA contains either a nonempty bounded `target_ids` list or one `target_shorthand`, never both.

Wrong/missing cardinality, a target field on NONE/SELF, a shorthand on SINGLE, or simultaneous IDs and
shorthand rejects with the existing stable `target_spec_mismatch` reason before initiative.

### 4.4 Focus and portrait

Each target descriptor references a portrait entry included in the current art payload's bounded catalog.
The selected target becomes the art panel's contextual portrait through a client-local focus event; no
focus request is sent to the server, and the browser never constructs the portrait data itself. Returning
from targets restores focus to the originating skill. A participant that disappears, flees, or becomes
invalid causes a newer revision; stale submission is rejected and focus returns to the nearest valid menu
entry in deterministic order.

---

## 5. Combat Session API Amendment

The current facade is logically:

```text
submit_player_action(actor, skill_key, target_or_none)
```

This unit replaces it with a caller-neutral target value compatible with `ActionRequest`:

```text
submit_player_action(actor, skill_key, targets_or_shorthand)
```

The accepted value is an explicit list of live objects or one of the existing `all-enemies`,
`all-allies`, and `all` shorthands. An empty list is normalized to actor only for SELF and remains empty
for NONE. The session facade still owns battlefield reconstruction, preflight, initiative round
execution, overwhelm dispatch, session persistence, terminal settlement, and recovery.

No compatibility overload is retained because the project is unreleased. Every current call site and
test is updated in the same change. The `cast` command gains an unambiguous multi-target syntax and keeps
existing single-target usage as ordinary syntax, not a deprecated adapter. Shorthands pass through the
same target expansion and validation as UI requests.

---

## 6. Action IDs

The combat unit registers a small fixed set of adapters:

| Action ID | Payload | Domain entry point |
|---|---|---|
| `combat.cast` | exact skill key plus bounded target IDs or approved shorthand | expanded `submit_player_action` |
| `combat.flee` | no arbitrary target; server builds innate request | expanded `submit_player_action` |
| `combat.forfeit` | session ID confirmation | existing `forfeit` |

Basic attack uses `combat.cast` with the server-provided innate skill key. The dispatcher does not expose
a generic method for clients to invoke arbitrary Python or Evennia command names.

Payload session ID is a stale-selection guard only. Actor and authoritative session are read from the
puppet. A mismatch rejects without settling or replacing the active session.

---

## 7. Round and Result Flow

1. Player enters combat mode from a full or changed-panel snapshot.
2. Player chooses root action, skill, and target values locally.
3. Browser submits once and locks the dock.
4. Dispatcher validates revision and invokes the combat adapter.
5. Session preflight rejects before initiative or starts exactly one ordinary round.
6. NPC turns and upkeep run through existing policies.
7. Overwhelm may run compressed resolver-backed rounds only after the selected first action.
8. Existing command-level text rendering or an equivalent event delivery adds every EventLog to the
   narrative log.
9. Server returns action result and replacement combat/status/art panels.
10. Nonterminal result focuses the root or prior logical position; terminal result switches to
    exploration mode after settlement and session cleanup.

The UI does not animate speculative HP. It updates from the committed result snapshot.

---

## 8. Rejections and Edge Cases

- A presenter-disabled skill sends no request.
- A tampered enabled skill can still be rejected by preflight without consuming a round.
- Mid-round invalidation remains a consumed round because earlier initiative actions are committed.
- A stale revision runs no adapter and receives a rebuilt combat panel.
- An invalid/missing participant follows existing deterministic recovery and does not strand the menu.
- Disconnect pauses the persistent session. Reconnect restores session ID, round count, participant
  state, action menu, and accumulated combat time.
- If the submitted result is lost during disconnect, the browser does not resubmit. The restored snapshot
  is authoritative.
- Examination mode shows nonlethal context and uses existing PASS/FAIL settlement; the UI cannot request
  lethal mode.
- A climax-in-progress or other zero-action state disables attack/skills/flee according to the core's
  capability output; Forfeit remains available through its separate confirmed path.

---

## 9. Telnet Parity

`combat actions` lists owned active skill keys and session-local participant tokens. Tokens are assigned
from the immutable participant order in `CombatSessionRecord`: allies use `a1`, `a2`, and enemies use
`e1`, `e2`. A token remains bound to the same participant for the life of that session and is never a
database dbref.

The command parser supports these exact forms:

```text
cast fire_ball=e1
cast wind_blade=e1,e2
cast wind_blade=all-enemies
```

Comma-separated multi-target input accepts session tokens only, eliminating display-name delimiter and
escaping ambiguity. Existing single-target name search remains valid for one target. `all-enemies`,
`all-allies`, and `all` are reserved complete right-hand-side values and cannot be mixed with tokens.
Unknown, duplicate, wrong-team, dead, or stale tokens pass no shortcut and reject through ordinary target
validation. Command help and tests define the same behavior. The WebClient provides a more convenient
selector but no rule capability unavailable to Telnet.

---

## 10. Tests and Acceptance

### Pure/presenter tests

- Stable stored skill order and pagination.
- Active only; passive exclusion; innate actions present.
- Every stable rejection code maps to a localized disabled reason.
- True resources and applied modifiers under disguise.
- NONE, SELF, SINGLE, and AREA descriptor construction.
- Participant/focus ordering is deterministic.
- Every focusable participant references one matching server-authored portrait catalog entry or an
  explicit no-portrait value.

### Domain/integration tests

- Expanded session facade accepts explicit AREA targets and all-target shorthands.
- Duplicate and forbidden targets reject before initiative.
- Preflight rejection consumes no round.
- Mid-round invalidation consumes one round.
- Normal, flee, overwhelm, defeat, forfeit, and exam outcomes preserve existing clock/session contracts.
- Stale UI revision and duplicate request ID do not run an additional round.
- Telnet multi-target and listing paths reach the same resolver behavior.
- Session target tokens remain stable across rounds/reconnect and reject duplicates, unknown tokens, and
  shorthand/token mixtures.

### Browser acceptance

- Use only arrow keys, Space, Enter, and Escape to complete basic attack, active skill, every target shape,
  and flee.
- Focus a disabled skill and read its reason without submitting.
- Items and Defend are visible, disabled, and described as unavailable.
- Target focus updates portrait overlay.
- Target focus switches only among current catalog entries and sends no mutation/focus packet.
- A reconnect during an active session restores the menu and committed state.
- 1280x720 retains visible narrative, status, and action controls without overlap.

The unit is complete only when all existing player-combat-session requirements still pass and all new
main requirements are traceably covered.
