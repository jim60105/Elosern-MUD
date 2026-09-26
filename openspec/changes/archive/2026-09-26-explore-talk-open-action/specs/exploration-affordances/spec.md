## MODIFIED Requirements

### Requirement: The canonical affordance vocabulary is shared and read-only
A shared module (`web/webclient/presentation/affordances.py`) SHALL own the canonical
affordance rules for a puppeted player in exploration mode, consumed by both the `exploration`
panel presenter and the `context_actions` exploration presenter. Every emitted entry SHALL be an
`AffordanceView` that is exactly one of two discriminated shapes:
- an **action entry** SHALL carry exactly `action_id`, `label`, `params`, `freeform`, `navigation`
  (false), `enabled`, and nullable `disabled_reason`; `action_id` SHALL be one member of
  `ACTION_CODE_ALLOWLIST`, which SHALL contain exactly `explore.move`, `explore.look`,
  `explore.talk_open`, `explore.talk_scripted`, `explore.talk_freeform`, `explore.party_invite`,
  `explore.party_leave`, `explore.engage`, `explore.wait`, `explore.possess`,
  `explore.possess_release`, and `explore.deliver` — there SHALL
  be no `explore.interact` entry (the exploration panel's interact group is a label over
  per-target affordances, not an action); there
  SHALL be no NPC or companion `explore.engage` (engagement is monsters-only);
- a **navigation entry** SHALL carry exactly `surface` (`"guild"` or `"shop"`), `label`,
  `navigation` (true), `enabled`, and nullable `disabled_reason`, and SHALL carry no
  `action_id` and no `params` — a navigation entry is a dock surface-opener with no dispatcher
  action code and SHALL never be dispatched as a `ui_action`.

`explore.move` SHALL be emitted once per present, traversable Exit with a bounded localized label;
`explore.look` SHALL be emitted per present non-exit object with `{"target_id": int}`;
`explore.talk_scripted` SHALL be emitted once per authored keyword of a present dialogue host
(resolved `ScriptedDialogue` component), `explore.talk_freeform` SHALL be
emitted once per present `LLMNPC`, `explore.party_invite` SHALL follow the existing party-bound
and full-party rules and `explore.party_leave` the companion-bound rule, `explore.engage` SHALL be
emitted once per present `Monster` (a living monster yields `enabled` true; a dead monster yields
a disabled entry with a stable `target_dead` reason — matching the v1 panel), guild/shop
navigation entries SHALL be emitted only for the exact local host, and the idle baseline SHALL
follow the idle-baseline requirement below. `explore.possess` SHALL be emitted once per present
bound companion with `params {"npc_id": int}`: `enabled` true when
`world/rules/possession.py`'s deterministic entry gates pass for that companion, otherwise a
disabled entry carrying the gate's stable reason code and fixed message. `explore.possess_release`
SHALL be emitted exactly once, only while the puppeted actor is a possessed NPC. While the
puppeted actor IS a possessed NPC, the vocabulary SHALL keep its refusal surface honest: talk
entries, `explore.engage`, and shop navigation entries SHALL be emitted disabled with stable
possession-refusal codes and safe Traditional Chinese messages — v1 possession refusals are
visible disabled states, not hidden entries. A schedule-blocked dialogue host SHALL NOT be omitted
from the vocabulary — the vocabulary preserves the v1 panel's emission semantics; schedule-gate
exclusion applies only to suggestion eligibility (suggestion-eligibility requirement below).
A dialogue host whose authored dialogue table cannot be resolved SHALL have no talk entries in
the vocabulary — no validator-normalized params exist for a keywordless host; the version-1
panel's disabled `dialogue_unavailable` affordance is a panel serialization degradation, not a
vocabulary entry. The vocabulary SHALL never emit an `explore.talk_open` entry: the allowlist
carries that code because the `exploration` panel serializes each conversable host's talk entries
(its per-keyword `explore.talk_scripted` entries and its `explore.talk_freeform` entry) as one 交談
`explore.talk_open` affordance, derived from the same host, presence, and possession gates, while
the `context_actions` form, suggestion eligibility, and the deterministic fallback keep consuming
the per-keyword and free-form entries unchanged. `explore.talk_open` SHALL NOT be in
`SUGGESTIBLE_ACTION_IDS`. Every entry with a disabled state SHALL carry a stable disabled code and safe
Traditional Chinese message. Nothing in this module SHALL mutate traits, knowledge, dialogue,
quests, inventory, combat sessions, party, or world time.

#### Scenario: The exploration panel and the context form share one vocabulary
- **WHEN** the same room is presented to the same puppeted actor through both the `exploration`
  panel and the `context_actions` exploration form
- **THEN** both surfaces enumerate the same eligible targets and the same non-talk actions with
  identical ids, labels, gates, and disabled states; every target that has talk entries in the
  context form carries exactly one 交談 `explore.talk_open` affordance in the panel with the same
  enabled state and possession reason; and both serializations are unchanged before and after a
  canonical-state comparison

#### Scenario: A dead monster stays visible as a disabled entry
- **WHEN** a present Monster is dead
- **THEN** the vocabulary contains its `explore.engage` action entry with `enabled` false and a
  stable `target_dead` disabled reason, exactly as the v1 panel rendered it

#### Scenario: A navigation entry carries no dispatcher code
- **WHEN** a guild or shop host is present
- **THEN** the vocabulary contains a navigation entry with `surface` `"guild"`/`"shop"`,
  `navigation` true, and no `action_id` and no `params`, and no `ui_action` registry lookup
  exists for it

#### Scenario: Possess entries mirror the deterministic gates
- **WHEN** a bound companion stands beside the player while a combat session is active
- **THEN** the vocabulary carries that companion's `explore.possess` entry disabled with the
  combat gate's stable code, and the same entry is enabled once combat ends

#### Scenario: Release is offered exactly once, only while possessing
- **WHEN** the actor possesses a companion and the vocabulary is emitted
- **THEN** exactly one `explore.possess_release` entry is present, and no unpossessed-emission
  vocabulary contains it

#### Scenario: The possessed actor's refusal surface stays visible
- **WHEN** the puppeted actor is a possessed NPC and a monster and a shop host are present
- **THEN** the engage and shop entries render disabled with stable possession-refusal codes and
  fixed messages rather than being omitted

#### Scenario: An available delivery is offered for the bound recipient
- **WHEN** the puppeted actor holds an active `DELIVER` stage bound to a co-located recipient and
  holds the objective's item
- **THEN** the vocabulary contains one `explore.deliver` action entry for that recipient, enabled,
  carrying validator-normalized params naming the recipient identity and the item key

#### Scenario: A delivery the actor cannot perform is not invented
- **WHEN** the bound recipient is co-located but the actor no longer holds the objective's item
- **THEN** the vocabulary contains that delivery entry disabled with a stable reason code and a safe
  Traditional Chinese message, and no enabled delivery entry exists

#### Scenario: No delivery entry exists without an active bound stage
- **WHEN** the actor has no active `DELIVER` stage bound to any co-located entity
- **THEN** the vocabulary contains no `explore.deliver` entry

#### Scenario: The conversation-opening code is allowlisted but never emitted
- **WHEN** the vocabulary is emitted for a room holding a scripted host and an `LLMNPC`
- **THEN** it contains the hosts' `explore.talk_scripted` and `explore.talk_freeform` entries and no
  `explore.talk_open` entry, `explore.talk_open` is a member of `ACTION_CODE_ALLOWLIST`, and it is
  absent from `SUGGESTIBLE_ACTION_IDS`
