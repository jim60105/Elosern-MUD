# Design

## Context

Current dialogue data consists of frozen Python rows assembled in world/lore/dialogue. Existing NPC profiles have stable keys, while service dialogue keys can differ. Shared contract v2 supplies the pure primitive parser, immutable declarations and identity/reference catalogs; this change supplies the filesystem boundary, not a second validator.

## Goals / Non-Goals

Deliver a complete tested `load_dialogue_snapshot(content_dir, *, profiles, bindings, references)` API in one workday. No live table migration, prose writing, startup behavior changes before runtime cutover, generated storage, hot reload or filesystem writes at runtime.

## Decisions

Implement `world/lore/dialogue/loader.py`. Scan sorted direct `*.yaml` regular files only. Reject symlinks, filenames not equal to a registered NpcProfile.key, duplicate canonical owner/dialogue bindings, absent required content directory, multi-document YAML, unsafe tags, aliases/merge keys and duplicate mapping keys at every nesting level. Use existing installed safe YAML library; cap each UTF-8 file at 262144 bytes before parse. Do not enable Python constructors. Non-YAML supporting files are ignored; no recursive traversal or manual filename inventory.

Root schema is exactly `{schema_version:1,greeting:string|null,topics:[...]}`. Derive owner from stem; an explicit npc_id/profile_key owner field is unknown and rejects. Use the common codec with `StaticDialogueIdentity(profile_key,dialogue_key)` and immutable canonical references. Profile membership validation is static-provider-only. Topic IDs retain existing dialogue-key prefix independently of filename. References/bindings derive from existing profile/service registries, including guild_staff -> altoria_guild_master, rather than a second hand-maintained mapping of files. Construct the complete candidate privately, freeze nested values, then return one MappingProxyType keyed by dialogue_key. Any invalid neighbor rejects the entire load; no partially registered rows or catch-and-skip behavior. Tests may call the API again with temporary directories, but production startup calls once in runtime's cutover.

A new registered profile's valid file is discovered without a file-index or binding edit. Where existing canonical service metadata declares a distinct dialogue alias, use it; otherwise dialogue_key defaults to the registered profile key. Existing host construction determines where an NPC appears and remains separate from file discovery. Do not require every nonconversable profile to own dialogue. Runtime's migration test owns complete coverage of the 25 current tables.

The alternative Python import registry requires manual file registration and is rejected. Generated files are rejected as an architecture because packages already have immutable DB publication. This exception is limited to dialogue content; architecture D9's other Python lore registries stay unchanged.

## Exact targets

- `world/lore/dialogue/loader.py` (new complete loader API)
- `world/lore/dialogue/codec.py` (reuse only; contracts owns parser)
- `world/lore/tests/test_dialogue_loader.py` (new synthetic temp-directory tests)
- Existing dialogue author documentation and `.github/evennia-shards.json` ownership entry at apply time

## Risks / Trade-offs

An invalid new file prevents startup snapshot publication; identity-named errors include safe filename/field paths so authors can repair the source. Safe parsing and whole-snapshot validation preserve deterministic read-only lore ownership. No hot reload means source edits require restart.

The loader derives neither the binding list nor any reference family: `profiles`, `bindings` and `references` are supplied by its caller (the runtime startup wiring) and are synthetic fixtures in this slice's tests. Exactly as contracts' Batch review resolutions fix them, `profiles` is the set of registered `NpcProfile.key` values, `bindings` maps `dialogue_key` to `profile_key`, and the returned snapshot maps `dialogue_key` to the immutable `AuthoredDialogue`. Completeness is checked in both directions: every binding must resolve to exactly one discovered file and every discovered file must name a registered profile, so a deleted or renamed file rejects the whole candidate instead of silently disabling a host. Profiles that ship no dialogue table are not bindings and need no file.

## Planned acceptance

Use untracked `.env.test` with MUD_TEST_SETTINGS=1 at apply time. Exercise sorted discovery with deliberately shuffled filenames, owner/profile mismatch, duplicate nested YAML keys, unsafe object tags, alias/merge, symlink escape, invalid UTF-8, unknown fields/references, filename service-key mismatch and atomic invalid-neighbor rejection. Verify frozen results cannot be mutated and a new valid registered file appears with zero registration edits. Test equivalent YAML primitives and JSON primitives through the same codec. Update existing author docs/test ownership with this behavior.

```text
uv run --locked --env-file=.env.test evennia test --settings test_settings.py --keepdb world.lore.tests.test_dialogue_loader world.lore.tests.test_authored_scenes
uv run --locked python -m tools.contract_gate
```

Commands are planned, not exercised during planning. Parent owns final proposal review/validation.
