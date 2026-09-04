# Delta: exploration-affordances

## MODIFIED Requirements

### Requirement: The canonical affordance vocabulary is shared and read-only
A shared module (`web/webclient/presentation/affordances.py`) SHALL own the canonical
affordance rules for a puppeted player in exploration mode, consumed by both the `exploration`
panel presenter and the `context_actions` exploration presenter. Every emitted entry SHALL be an
`AffordanceView` that is exactly one of two discriminated shapes:
- an **action entry** SHALL carry exactly `action_id`, `label`, `params`, `freeform`, `navigation`
  (false), `enabled`, and nullable `disabled_reason`; `action_id` SHALL be one member of
  `ACTION_CODE_ALLOWLIST`, which SHALL contain exactly `explore.move`, `explore.look`,
  `explore.talk_scripted`, `explore.talk_freeform`, `explore.party_invite`, `explore.party_leave`,
  `explore.engage`, and `explore.wait` — there SHALL be no `explore.interact` entry (the
  exploration panel's interact group is a label over per-target affordances, not an action); there
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
follow the idle-baseline requirement below. A schedule-blocked dialogue host SHALL NOT be omitted
from the vocabulary — the vocabulary preserves the v1 panel's emission semantics; schedule-gate
exclusion applies only to suggestion eligibility (suggestion-eligibility requirement below).
A dialogue host whose authored dialogue table cannot be resolved SHALL have no talk entries in
the vocabulary — no validator-normalized params exist for a keywordless host; the version-1
panel's disabled `dialogue_unavailable` affordance is a panel serialization degradation, not a
vocabulary entry. Every entry with a disabled state SHALL carry a stable disabled code and safe
Traditional Chinese message. Nothing in this module SHALL mutate traits, knowledge, dialogue,
quests, inventory, combat sessions, party, or world time.

#### Scenario: The exploration panel and the context form share one vocabulary
- **WHEN** the same room is presented to the same puppeted actor through both the `exploration`
  panel and the `context_actions` exploration form
- **THEN** both surfaces enumerate the same eligible targets and actions with identical ids,
  labels, gates, and disabled states, and both serializations are unchanged before and after a
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
