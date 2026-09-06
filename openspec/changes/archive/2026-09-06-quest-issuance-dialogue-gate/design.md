## Context

`_apply_offer_quest` is the one place the generative layer can cause a quest record to exist. Its
current gate is `GuildStaff` only. Widening it is the last connection the private-commission stack
needs, and the only one that moves an AI boundary — which is why it is its own change rather than
part of `quest-issuance-generative`.

Parent design: `docs/superpowers/specs/2026-09-06-quest-issuer-model-design.md` §4.4.

## Goals / Non-Goals

**Goals:**

- An authorized commissioner can hand out its own commission in conversation.
- The AI gains no new power to choose an issuer, invent a commission, or reach an unauthorized NPC.
- The guild path is byte-for-byte unchanged.

**Non-Goals:**

- No new intent kind — `offer_quest` covers both issuer kinds.
- No change to the payload, the whitelist, or the speech-preserved failure mode.
- No content pipeline work (owned by `quest-issuance-generative`).

## Decisions

### D1: The widening is an authorization change, not a permission relaxation

Before: the speaker must carry `GuildStaff`. After: the speaker must carry `GuildStaff` or
`QuestIssuer`. Both are authored components an author must deliberately attach, and in both cases the
applier verifies a registered issuance at the speaker's own resolved key before writing.

What the model can do is unchanged in kind: it names a `quest_key`, and the deterministic layer
decides whether that speaker holds that commission. The model cannot name an issuer, cannot register
an issuance, and cannot make an NPC carrying neither component issue anything.

### D2: A private commission's eligibility is the issuance's existence

Guild eligibility has a rank band because the guild has ranks. Inventing one for a shopkeeper's
errand — a minimum rank, an affinity floor — would be fabricating a rule nobody specified. The
authorization already happened when an author attached the component and registered the commission.

### D3: Ambiguity fails closed

A speaker carrying both components with the same quest key issued under both namespaces is a content
error. Picking one silently would make the reward and the settlement mode depend on an arbitrary
precedence rule that no spec states. Failing verification preserves the speech, changes nothing, and
surfaces the error.

### D4: Split from the content pipeline

`quest-issuance-generative` restructures `CompiledQuest`, the dual-registry dispatch, and the durable
store payload. This change touches one function and moves an AI boundary. Bundling them would put a
security-relevant edit inside a large refactor and would exceed one workday; separating them lets the
gate be reviewed on its own terms.

The two are siblings, not sequential: this change verifies whatever issuances exist, however they
were registered.

## Risks / Trade-offs

- **A widened AI-reachable gate is the highest-risk edit in the whole feature** → Mitigated by the
  authored-component requirement, the registered-issuance verification, the fail-closed ambiguity
  rule, and an explicit test that an NPC carrying neither component is refused even when an issuance
  exists elsewhere.
- **Two eligibility rules in one function** → Kept as an explicit dispatch on the resolved key's
  namespace, with the guild branch untouched, so the guild path's existing tests are the regression
  guard.
