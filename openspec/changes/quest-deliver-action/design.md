## Context

`quest-deliver-objective` made `DELIVER` advance from a committed transfer, but the only transfer
path from player to NPC is the LLM-driven `take_item` intent. This change supplies the deterministic
player verb on both surfaces.

Parent design: `docs/superpowers/specs/2026-09-06-quest-issuer-model-design.md` §5.

## Goals / Non-Goals

**Goals:**

- A delivery quest is completable with every generative service down.
- One rule, two surfaces — the action and the command cannot diverge.
- Refusals are honest, coded, and change nothing.

**Non-Goals:**

- No general-purpose give verb for arbitrary items. This change delivers *quest* items to *bound*
  recipients only; a free-form give is a separate product decision.
- No drop, take, or trade verbs.
- No quest-drawer button (owned by `webclient-quest-drawer-split`, which consumes this action id).

## Decisions

### D1: Quest-scoped delivery, not a general give verb

Scoping the verb to bound quest recipients keeps this change inside a workday and avoids opening
questions a general give verb raises immediately: can you give money, can you give to a player, does
the recipient refuse, what happens to a full inventory, is it an economy exploit. The redesign lists
`給` under exploration interaction, and this is the first slice of it; the command's alias reserves
the natural name.

**Amended during implementation review.** The premise was wrong: a general give already exists —
`commands/localized/general.py::CmdGive` is the localized Evennia `give` with `key = "給"`, mounted
in `CharacterCmdSet` and documented in the command docs. `CmdDeliver` therefore ships with
`key = "交付"` and no alias, and reserves nothing. The shared deterministic rule remains the seam
for a future branch inside the general give.

### D2: The action registration requirement lives in `quest-delivery`

`webclient-action-dispatch` enumerates the production action set exhaustively, but the repo's
established pattern is for a later change to add its action IDs as a requirement of its *own*
capability — `webclient-service-menus` did exactly that for `inventory.use`, `inventory.toggle_equip`,
and `guild.quest_track`. Following that precedent avoids restating a long enumeration, and avoids
propagating the staleness already present in it (the base enumeration predates `guild.quest_track`).

### D3: The affordance requirement is a genuine MODIFIED delta

`ACTION_CODE_ALLOWLIST` is enumerated inside the affordance-vocabulary requirement, so admitting a
new code changes that requirement's text. The full requirement is copied and edited rather than
partially restated, per the delta rules.

### D4: The adapter re-resolves everything

The payload names only the recipient and the item. The quest ID, stage index, quantity, and reward
are all re-derived server-side from stored state. A client that could name its own quest ID could
advance a stage it does not hold.

### D5: One hand-over transfers exactly the remaining objective quantity

The payload carries no quantity, so the rule derives it: the remaining quantity
(`objective.quantity - stage_progress`) of the **selected** active stage. When several in-progress
records bind the same `(recipient, item_key)` pair, one shared selection helper — used by both the
rule and the affordance builder — picks the stage with the **lowest remaining** quantity (ties break
in quest-log order), so an enabled affordance is always satisfiable by the hand-over it advertises
and every enabled invocation makes progress. The delivery observer still advances every matching
active record by `min(transferred, its own remaining)`.

### D6: The combat gate lives in the shared rule

`is_in_active_session(actor)` is checked inside `deliver_quest_item`, not in the two surfaces, so
the action and the command refuse an in-combat delivery with the identical stable code and message
(parity requirement). The refusal precedes every other rule-level check: an in-combat actor learns
the combat refusal even when the recipient or item would also mismatch.

### D7: The exploration panel schema bumps to version 2 for the delivery payload

The dock's interact menu is built from the `exploration` panel, whose action affordances carried no
`params`: every existing target action's payload is re-derived from the target identity. A delivery
cannot be reconstructed that way — the item key exists only as server state — and parsing the
server label would be prose-guessing. Schema version 2 therefore admits exactly one conditional
field: the `explore.deliver` affordance carries `params` (the registered validator's normalized
output); every other action keeps the version-1 exact shape. The client panel validator mirrors the
version and the conditional field, so a stale client rejects the panel rather than dispatching a
guessed payload. The parity wording is scoped: both surfaces share one rule and produce identical
outcomes for a resolved recipient; recipient *resolution* failures are surface-specific by design
(the action rejects an unknown identity with `no_npc`, the command renders its search-miss line).

## Risks / Trade-offs

- **Recipient resolution differs between surfaces** → The action names an integer identity; the
  command parses a name with the ordinary local search (`caller.search`), which resolves any
  co-located entity type exactly like the action's present-entity lookup — a non-NPC bound recipient
  is deliverable from both surfaces. Both funnel into one rule that takes a resolved entity, so the
  divergence is confined to argument parsing, and the parity test pins that both produce identical
  outcomes.
- **The general give advances no delivery** (pre-existing): `CmdGive` transfers `db.inventory` keys
  through the inventory primitives without the delivery observer, so handing the parcel to the bound
  recipient with `給` moves the item but advances nothing. This hole predates the change (change 5
  wired only `_transfer_items`) and its delta specs own no general-give requirement; fixing it is a
  separate reviewed change that routes `CmdGive`'s registry-key path through the delivery advance.
- **Combat gating** → Refused during an active combat session using the existing gate idiom, so a
  delivery cannot be used to shuffle items mid-fight.
