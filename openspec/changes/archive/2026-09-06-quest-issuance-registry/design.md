## Context

`world/quests/` is already guild-agnostic. `QuestRecord` carries no guild field; `QuestDefinition`
carries `rank` only as a difficulty label; `accept_quest` needs no host; progress advances
automatically through `planner.py`, `room_observation.py`, and `acquire.py`, all converging on
`fulfill_record_for()`. The guild coupling lives in `world/rules/guild_offers.py` and
`world/rules/guild.py`.

The parent design is `docs/superpowers/specs/2026-09-06-quest-issuer-model-design.md` §4.1.

## Goals / Non-Goals

**Goals:**

- One validated grammar for issuer identity, shared by every later consumer.
- One normalized read seam so no consumer has to know whether a commission came from a guild branch
  or a private character.
- Additive-only: zero behavior change and zero edits to the guild offer surface.

**Non-Goals:**

- No `QuestRecord` change (owned by `quest-record-issuer-key`).
- No `QuestIssuer` component (owned by `quest-issuer-component`).
- No settlement execution (owned by `quest-auto-settlement`).
- No generative-pipeline emission of private commissions (owned by `quest-issuance-generative`).

## Decisions

### D1: A read seam, not a merged registry

The parent design originally made `GuildQuestOffer` a view over one unified
`QUEST_ISSUANCE_REGISTRY`. That was rejected after measuring the blast radius: twenty-five test
modules save, clear, and restore `GUILD_OFFER_REGISTRY` directly, and several index it expecting a
`GuildQuestOffer` value. Merging the storage forces churn through all of them for no behavioural
gain, and would not fit one workday.

Instead `QUEST_ISSUANCE_REGISTRY` stores private commissions only, and `resolve_issuance()`
dispatches on the issuer key's namespace. Each issuer kind keeps exactly one writer, so the stores
cannot drift, and every consumer reads through one function.

The parent design document is amended to record this.

### D2: `npc:#<pk>` is a distinct grammar form, not a free-form key

Runtime-registered commissions key on the issuing character's database identity. Spelling that as
an explicit `#`-prefixed form (rather than letting an arbitrary content key happen to be numeric)
means the parser can state which kind of remainder it holds, and a content key can never silently
collide with a database identity. This mirrors the existing entity-key contract, where the
digit-only region of the keyspace is reserved for player primary keys.

### D3: The merit rule is validated at construction, not at settlement

`reward.merit == 0` for private commissions is checked when the `QuestIssuance` value is built, so
an invalid commission can never reach the registry, the read seam, or a settlement path. Validating
later would let bad content sit in the registry until a player completed the quest.

### D4: Landing without a consumer is deliberate

This change registers a seam nothing reads yet. `AGENTS.md` explicitly sanctions this: "Keep
forward-declared seams and guarded tests intact when their owning change has not landed yet. A
deliberate skip is preferable to a fake implementation." The alternative — folding the registry into
the record change — produces a unit that does not fit one workday.

## Risks / Trade-offs

- **Two stores could drift** → Each kind has exactly one writer, the private registry refuses
  `guild:` keys outright, and the read seam is the only join. A test asserts that a guild key never
  reaches the private registry and vice versa.
- **The seam has no consumer, so a mistake ships unnoticed** → The delta spec's scenarios are the
  guard; the focused test module covers every grammar form, both registry writers, and all four
  resolution outcomes before any consumer exists.
- **`QuestReward` is reused for private commissions even though `merit` is always zero there** →
  Accepted deliberately. Introducing a second reward shape would fork the settlement code that
  `quest-auto-settlement` must share with the guild turn-in path.
