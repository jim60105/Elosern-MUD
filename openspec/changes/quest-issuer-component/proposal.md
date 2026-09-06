# Proposal: quest-issuer-component

## Why

Private commissions need an answer to "which NPCs may issue a quest at all". Every NPC has a
database identity, so a primary key would suffice as a *key* — but it would not gate anything: any
NPC would become a potential commissioner, and the dialogue `offer_quest` intent could let the model
make a passer-by hand out work. Authority must be authored data, not an emergent property of
existing.

The project already has exactly this idiom: a closed component vocabulary marking "this NPC hosts
service X" (`guild_staff`, `guild_examiner`, `merchant`, `scripted_dialogue`), authored per record
through the import pipeline and read by runtime gates from the component instance. A fifth entry
gives private commissions the same authorization story, and supplies the authored content key that
lets authors write a commission list before any primary key exists.

## What Changes

- New `QuestIssuer` component with `service_id`, `issuer_key`, `service_binding`, and
  `anchor_room_id` — the same four-field shape `GuildStaff` carries, with `issuer_key` where
  `branch_key` sits. `service_id` is load-bearing, not decorative: the roster-sync reuse path
  (`guild_economy.py::_find_service_host`) reads it unconditionally on whichever class anchors a
  profession row, so a commissioner blueprint anchored on a field-less class would raise
  `AttributeError` inside `at_server_start`.
- `quest_issuer` added to the closed `PROFESSION_COMPONENT_TYPES` vocabulary, so the import
  pipeline's per-record `components` authoring path and the profession blueprint resolution accept
  it with no further plumbing.
- New profession rulebook row in `world/rules/rulebook/professions.yaml` for a commissioner
  blueprint, and `quest_issuer` permitted as an explicit per-record component entry alongside an
  existing profession (a shopkeeper who also issues commissions is `merchant` + an explicit
  `quest_issuer` entry).
- A new contract test pinning an invariant that currently holds only by convention: every profession
  row's FIRST component must name a class defining `service_id`. `scripted_dialogue` also lacks the
  field and is never placed first today; without the test, a future row anchored on either class
  would crash startup synchronization rather than failing at authoring time.
- `issuer_key` deliberately does NOT join the assembly helper's required-identity set, because that
  set means "must be authored and non-empty" and an absent `issuer_key` is the valid identity form.
  The accepted consequence: a roster-created commissioner resolves to `npc:#<pk>`, while authored
  content keys come through the import path, which passes kwargs verbatim.
- New `resolve_issuer_key(host)` in the issuer layer: a host carrying `QuestIssuer` with a non-empty
  authored `issuer_key` resolves to `npc:<authored key>`; one with an empty `issuer_key` resolves to
  `npc:#<pk>`; a host without the component resolves to nothing.
- `resolve_local_service_host(actor, QuestIssuer)` becomes usable with no change to that function —
  it is already generic over the component class.

## Capabilities

### New Capabilities

- `quest-issuer-authorization`: the `QuestIssuer` component as the sole authority for issuing a
  private commission — its vocabulary membership, authored identity, the two-form key resolution,
  and the rule that authority is authored rather than inferred.

### Modified Capabilities

(None. `profession-registries` already requires that every component class in
`typeclasses/components.py` has a vocabulary entry, enforced by a contract test, and no requirement
enumerates the rulebook's rows — so adding the class, its vocabulary entry, and a blueprint row
changes no requirement's behavior.)

## Impact

- `typeclasses/components.py`: new component class.
- `world/rules/profession_config.py`: vocabulary entry, rulebook row validation, and the
  anchor-must-carry-`service_id` contract.
- `world/rules/rulebook/professions.yaml`: commissioner blueprint row.
- `world/rules/quest_issuance.py`: `resolve_issuer_key(host)`.
- `world/imports/schema.py`: the component-entry description enumerates the identity fields each
  component class defines; `issuer_key` joins that list.
- No behavior change for any existing NPC: nothing carries the new component until content authors
  it.
