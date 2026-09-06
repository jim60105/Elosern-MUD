## Context

`quest-issuance-registry` defined the `npc:` issuer-key namespace but nothing produces one yet. This
change supplies both the authority to issue and the authored identity to key by.

Parent design: `docs/superpowers/specs/2026-09-06-quest-issuer-model-design.md` §4.2.

## Goals / Non-Goals

**Goals:**

- Make "may this NPC issue a commission" an authored datum with exactly one carrier.
- Give authors a key they can write before any primary key exists.
- Reuse the existing service-host idiom end to end so no new plumbing is invented.

**Non-Goals:**

- No widening of the `offer_quest` dialogue gate (owned by `quest-issuance-generative`).
- No commission content — this change authors no actual commissions.
- No change to `resolve_local_service_host`, which is already generic.

## Decisions

### D1: A component, not a flag or a naming convention

The component's value is authorization, not key supply — a primary key would already give every NPC
a usable key. Marking authority in authored data means the dialogue applier can verify it, and the
model cannot make an arbitrary NPC hand out work. This mirrors how `GuildStaff` gates guild service
rather than inferring it from a name or location.

Alternatives rejected: a boolean attribute (no import authoring path, no vocabulary contract test);
reusing `Merchant.shop_key` or `ScriptedDialogue.dialogue_key` (conflates unrelated identities, and
a commissioner need be neither); a naming convention on `db.portrait_policy.stable_key` (that key is
the *art subject* identity, authored only for named imports and absent on scene-spawned NPCs — tying
commission identity to it would weld two unrelated concerns together permanently).

### D2: Two key forms with one field, not two fields

`issuer_key` present means an authored content key; absent means fall back to the primary key. One
field with one resolution rule is simpler than a discriminator plus a value, and it makes the
authored case the visible one in content files.

### D3: `service_id` is required, and the anchor invariant becomes enforced

The roster-sync reuse path resolves a profession row's existing host by reading `service_id` on the
row's FIRST component class (`guild_economy.py::_row_anchor_class` then `_find_service_host`). The
read is unconditional, so a row anchored on a class without the field raises `AttributeError` inside
`at_server_start` — crashing the whole guild-economy sync, not just quest issuance, on every restart
after such a row exists.

`QuestIssuer` therefore carries `service_id` like every other service component, which is what makes
"structurally identical to `GuildStaff`" actually true and lets a commissioner blueprint anchor a row.

The invariant behind this holds today only by convention: `ScriptedDialogue` also lacks `service_id`
and simply never appears first in any row. A contract test now states it — every row's first
component must define `service_id` — so the next component class that lacks it fails at authoring
time rather than at startup.

`issuer_key` deliberately stays OUT of `_IDENTITY_KWARGS`. That set is the REQUIRED-identity
contract: `missing_identity_kwargs` rejects an absent or blank value. An absent `issuer_key` is not a
defect — it is the identity form that resolves to the carrier's primary key. Adding it there would
make the authored form mandatory and destroy D2. The cost is that `project_row_kwargs` never projects
an authored key onto a roster-created commissioner, which resolves to `npc:#<pk>`; authored content
keys come through the import path, whose `resolve_component_plan` passes kwargs verbatim.

### D4: `person` binding

A commission travels with the commissioner: if the shopkeeper walks to the docks, the errand they
gave you is still theirs. `place` binding would tie the commission to a room, which is the wrong
model for a personal errand. The field is authored and validated today and consumed by the
service-anchoring gate.

## Risks / Trade-offs

- **An authored `issuer_key` could collide with another NPC's** → The grammar validates shape, not
  uniqueness; a duplicate would make two NPCs share a commission list. Mitigated by the same
  contract style used for entity keys: a startup contract test asserts authored issuer keys are
  unique across loaded carriers.
- **`npc:#<pk>` keys are instance-scoped** → A partial world re-import leaves orphan commissions
  pointing at reassigned primary keys. Accepted for a pre-release project; authored keys are the
  recommended form for durable content and the proposal says so.
- **Adding a vocabulary entry touches a contract-pinned mapping** → That contract test is exactly the
  guard: it fails loudly if the class and vocabulary drift, which is the behavior we want.
- **A roster-created commissioner cannot carry an authored content key** → Accepted and stated. It
  resolves to its identity form, which is a valid issuer key; content wanting a durable authored key
  uses the import path. Pinned by a test so the behavior is intentional rather than discovered.
