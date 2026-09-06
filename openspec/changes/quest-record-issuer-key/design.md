## Context

`quest-issuance-registry` provides `parse_issuer_key`, `guild_issuer_key`, `npc_issuer_key`, and
`resolve_issuance`. This change makes the stored record name its commission so every downstream
consumer — settlement, the read model, the drawer — can resolve reward and settlement mode from the
record alone.

Parent design: `docs/superpowers/specs/2026-09-06-quest-issuer-model-design.md` §4.3.

## Goals / Non-Goals

**Goals:**

- A record always states which issuance governs it.
- Acceptance can never create a record pointing at a non-existent commission.
- The guild acceptance path stays behaviorally identical apart from carrying the key.

**Non-Goals:**

- No private-commission acceptance path yet — nothing issues `npc:` keys until
  `quest-issuer-component` and `quest-issuance-generative` land.
- No settlement behavior change.
- No widening of the `offer_quest` intent gate.

## Decisions

### D1: Required field, not optional-with-default

`tracked` is the one optional-with-default key in `from_storage`, and it exists as a
backward-compatibility affordance. `AGENTS.md` rules those out: "The project has no released users.
Do not add backward-compatibility layers or data migrations unless a task explicitly requires them."

A default would also be wrong on its merits: there is no safe default issuer. Defaulting to a guild
key would invent a commission and could pay a reward the player never earned. The field is required
and the strict reader rejects a record without it. Existing development quest logs must be
recreated; that cost is one command in a pre-release project.

### D2: Resolve before create, not at settlement

`accept_quest` verifies `resolve_issuance(...)` is not `None` before writing. Validating only at
settlement time would let a player carry a quest for hours and then discover it pays nothing. This
also makes the failure mode a caller bug at the acceptance site, where it is diagnosable.

The reverse case — an issuance unregistered *after* acceptance, which the generative pipeline can
produce — is tolerated by `validate_record_runtime`: the record stays readable and the read model
reports no reward line, rather than making the whole quest log unreadable.

### D3: The guild key is constructed, never concatenated

`accept_guild_offer` calls `guild_issuer_key(branch_key)` rather than building `f"guild:{branch}"`.
One constructor means the acceptance path and the resolve seam cannot drift on spelling, which is
the class of bug that silently makes every reward unresolvable.

## Risks / Trade-offs

- **Existing development save data breaks** → Accepted and stated explicitly in the proposal. No
  migration is written; developers recreate quest logs.
- **Wide call-site sweep for `accept_quest`** → Bounded and enumerated: six direct `QuestRecord(...)`
  sites plus the two shared quest fixtures. The compiler and the strict reader both fail loudly on a
  missed site, so nothing degrades silently.
- **A record can outlive its issuance** → Deliberate. `validate_record_runtime` keeps the record
  readable and the read model omits the reward line rather than failing the whole log.
