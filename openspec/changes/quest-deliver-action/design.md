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

## Risks / Trade-offs

- **Recipient resolution differs between surfaces** → The action names an integer identity; the
  command parses a name. Both funnel into one rule that takes a resolved entity, so the divergence is
  confined to argument parsing, and the parity test pins that both produce identical outcomes.
- **`給` as an alias may later conflict with a general give verb** → Accepted and noted: when the
  general verb lands it takes the alias and the quest delivery becomes one of its branches. The
  shared rule is already the seam for that.
- **Combat gating** → Refused during an active combat session using the existing gate idiom, so a
  delivery cannot be used to shuffle items mid-fight.
