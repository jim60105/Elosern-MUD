## 1. Codex module

- [x] 1.1 Create `world/rules/lore_knowledge.py` with `CODE_CATEGORIES` — a closed mapping from
      each category to exactly one registry (`race`→`RACE_REGISTRY`, `nation`→`NATION_REGISTRY`,
      `region`→`WILDERNESS_REGION_REGISTRY`, `monster`→`MONSTER_TIER_REGISTRY`,
      `element`→`ELEMENT_REGISTRY`, `magic`→`MAGIC_TIER_REGISTRY`, `anchor`→`ANCHOR_REGISTRY`,
      `guild`→`GUILD_RANK_REGISTRY`) — plus `record_lore_reveal(player, category, key)`,
      `list_discovered(player)`, and `lore_card(category, key)`.
- [x] 1.2 `record_lore_reveal` semantics: append-only namespaced set on `player.db.lore_discovered`,
      repeat reveal no-op, category outside the mapping rejects, key validated against that
      category's registry (subrace keys under `race` reject), sole writer (no other module mutates
      the record).
- [x] 1.3 `list_discovered` returns deterministic (mapping order, then key) pairs; malformed record
      degrades to an unavailable diagnostic without reset or fabrication.
- [x] 1.4 `lore_card` renders exactly each category's declared card fields (e.g. race key +
      description, region `terrain_flavor_zh`); unresolvable key raises a named error.
- [x] 1.5 Pure unit tests: closed mapping (one registry per category), first reveal, repeat no-op,
      unknown category, subrace-under-race rejection, deterministic listing, corrupt-record
      isolation, per-category card rendering, named error on unresolvable key.

## 2. reveal_lore applier

- [x] 2.1 Extend the `npc_dialogue` per-kind semantic validator so `reveal_lore` accepts exactly
      the `category` and `key` fields, each a non-empty string of at most 64 code points (shared
      named constant `MAX_INTENT_KEY_LENGTH`); missing, empty, over-length, non-text, or
      extra-field payloads reject and retry. Category allowlist and registry resolvability are NOT
      extraction checks — they belong to the deterministic applier (discard intent, keep speech).
- [x] 2.2 Implement `_apply_reveal_lore(npc, player, intent)` in `world/rules/npc_intents.py`:
      verify category in the mapping + key resolvable in that registry, then
      `record_lore_reveal`; repeat reveal is an applied no-op; no affinity granted; failure
      discards only the intent.
- [x] 2.3 Remove `reveal_lore` from `_FORWARD_DECLARED_KINDS`, leaving the tuple empty; wire the
      kind into `apply_npc_intent` dispatch.
- [x] 2.4 Applier tests: success records the discovery; unknown category / unresolvable key
      discards only the intent (speech preserved, no retry-exhausted degradation); repeat reveal
      no-op; no affinity record created; boundary tests for the 64-code-point cap.

## 3. lore command

- [x] 3.1 Add the `lore` command to the character cmdset: `lore` lists discovered entries grouped
      by category; `lore <category> <key>` checks discovered-membership then renders one
      discovered card; unknown category, unknown key, and undiscovered entries all return the same
      fixed not-found line.
- [x] 3.2 Update `docs/game/commands.md` and `docs/game/command-reference.md` for `lore` and update
      the `EXPECTED_COMMANDS` manifest in `tests/test_command_docs.py` (key, syntax, context) so
      the command-docs drift contract stays green.
- [x] 3.3 Command tests: listing groups, card rendering, undiscovered/unknown not-found line,
      no registry-existence leak.

## 4. Spec and contract updates

- [x] 4.1 Sync the `npc-dialogue` main spec from the delta (reveal_lore payload shape and
      executability; removed not-yet-executable scenario recorded) per the sync/archive workflow,
      together with `dialogue-offer-quest`'s delta so both land consistently.
- [x] 4.2 Annotate new `lore-knowledge` main requirements with `covers_requirement` (literal IDs
      from `python -m tools.spec_traceability list`) and keep `spec_traceability check` green.
- [x] 4.3 Run the affected Evennia test domains (world.rules, world.ai dialogue-layer tests) and
      confirm existing guild/quest/affinity suites stay green.
- [x] 4.4 Run `openspec validate --change lore-knowledge-codex --strict`.
- [x] 4.5 Run the affected test entry points with one shared `OPENSPEC_TEST_EVIDENCE` path, then
      run `python -m tools.spec_traceability verify --evidence` (AGENTS.md handoff gate).
