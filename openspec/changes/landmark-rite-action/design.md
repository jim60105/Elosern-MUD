# Design

## Context

Design document: `docs/superpowers/specs/2026-11-14-landmark-rites-design.md` §9.1 (action), §12.3 (text client), §13 (errors). Existing code, read on 2026-11-14:

- `world.rules.landmark_rites` (`landmark-rite-settlement`): `perform_rite(actor, option_key, member_id=None, *, operation_id=None) -> RiteResult`, `RiteRefused(code, message)`, `rite_site_for(owner)`, `record_owner_for(actor)`, `eligible_performers(actor)`; `world.rules.landmark_rite_record.seen_option_keys(owner, district_key)`.
- `web/webclient/actions/registry.py`: `ActionSpec(action_id, validate_payload, adapter, affected_panels)`; production specs are registered in `build_production_action_registry()`. The `explore.camp` registration is the model.
- `web/webclient/actions/exploration_actions.py`: `_rejected(code, message)`, `AFFECTED_FULL`, `ExplorationActionError`, and `_camp_adapter`, which reads `payload.get("request_identity")` (`{"epoch", "request_id"}`) and builds its operation identity with `server.camp_service.operation_identity(owner_dbid, epoch, request_id)`.
- `web/webclient/actions/dispatcher.py`: `_REQUEST_IDENTITY_ACTIONS = frozenset({"explore.camp"})` names the actions that receive `request_identity`.
- `commands/church.py`: the convention for a project command (English `key`, Chinese `aliases`, `locks = "cmd:all()"`, `help_category`), mounted in `commands/default_cmdsets.py`.
- `world.rules.party_scope.resolve_member_token(acting, token)` resolves a companion name; it raises `PartyScopeError` for zero or several matches.
- `tests/test_command_docs.py` fails when a mounted command has no reference entry.

## Goals / Non-Goals

**Goals**

- Two thin entry points over one settlement; identical refusal codes on both.

**Non-Goals**

- No `rite` panel, no stored delivery, no webclient store or component (`landmark-rite-panel`, `landmark-rite-stage`).
- No lighting change and no "explored" wording in the completion line (`landmark-rite-lighting`).
- No new settlement rule; every refusal comes from `perform_rite`.
- The text command stores no browser presentation state. A browser session on the same character sees a text-command rite in the experienced list, not as a delivery.

## Decisions

### D1. Shared text and delivery helpers (`web/webclient/actions/rite_actions.py`)

```python
def rite_delivery(result: RiteResult) -> dict: ...
def rite_scene_text(result: RiteResult) -> str: ...
def rite_completion_line(result: RiteResult) -> str: ...
```

`rite_delivery` returns exactly:

```python
{
    "kind": "formal",
    "delivery_id": f"rite:{district_key}:{option_key}:{tick}",
    "scene_id": scene.scene_id,
    "scene_revision": scene.revision,
    "actor_name": "你" if perspective == "self" else <body display key>,
    "guardian_name": archetype.guardian_name_zh,
    "lines": [world.lore.scenes.line_to_dict(line) for line in scene.lines],
}
```

For perspective `watch`, every line's `text` has each occurrence of the literal placeholder `{name}` replaced by the body display key before it is placed in `lines` (plain `str.replace`, never `str.format`). The `self` perspective's text is passed through unchanged, so a `{name}` there stays literal. This is how one authored watch scene names whichever companion performs.

The key is `scene_revision`, never `revision`: `web/webclient/presentation/protocol.py` `FORBIDDEN_RESULT_DATA_KEYS` rejects a result `data` that contains the key `revision` at any depth, and the dispatcher replaces such a result with the internal-error envelope after the rite already committed.

`rite_scene_text` renders every line of `rite_delivery(result)["lines"]` in order, one per text line: a narration line as its text; a speech line as `<name>：<text>` where `<name>` is `actor_name` for speaker `actor` and `guardian_name` for speaker `host`. `rite_completion_line` returns `你完成了<landmark_name>的儀式。` for perspective `self` and `<body display key>完成了<landmark_name>的儀式。` for `watch`. The body display key is `body.key`.

### D2. Action (`web/webclient/actions/rite_actions.py`)

```python
def validate_landmark_rite_payload(payload: Any) -> dict[str, Any]: ...
def landmark_rite_adapter(actor: Any, payload: dict[str, Any], session: Any = None) -> dict[str, Any]: ...
```

Validation (raise `ExplorationActionError` on any violation): the payload is an object with exactly the keys `option` and `member_id`; `option` is a string matching `world.lore.rites.loader.KEY_PATTERN`; `member_id` is `None` or a non-bool integer in `1..MAX_SAFE_INTEGER`. Return `{"option": ..., "member_id": ...}`.

Adapter:

1. `identity = payload.get("request_identity") or {}`; resolve the owner with `world.rules.landmark_rites.record_owner_for(actor)`; `operation_id = server.camp_service.operation_identity(int(owner.pk), "rite", identity.get("epoch", ""), identity.get("request_id", ""))`.
2. `result = perform_rite(actor, payload["option"], payload["member_id"], operation_id=operation_id)`.
3. `RiteRefused` (from step 1 or 2) -> `_rejected(error.code, error.message)`.
4. Any other exception -> `log_error("landmark_rite_failed", context={"char": actor.pk}, exc=error)` and `_rejected("rite_failed", "現在無法進行儀式。")`.
5. Success: `message = rite_completion_line(result)`; send it once with `owner.msg(message)`; return

```python
{
    "outcome": "success",
    "code": "explore.landmark_rite",
    "message": message,
    "data": {"delivery": rite_delivery(result), "first_completion": result.first_completion},
    "affected_panels": AFFECTED_FULL,
}
```

A replayed result (same request identity) takes the same path; the message is sent again, which is the existing camp behaviour.

Command echo: `web/webclient/actions/tests/test_action_catalog_coverage.py` requires every registered action id to appear in `registeredMutationActionIds` of `web/static/webclient/js/tests/command_echo_coverage_manifest.json` and to resolve a display line (or sit in the silent list) in `web/static/webclient/js/elosern/command_echo.js`. Add the id to the manifest and add an echo entry beside the `explore.camp` entry that returns `join(["rite", payload.option])` for a string option and `null` otherwise (the member is not echoed), and extend the coverage fixture of `web/static/webclient/js/tests/command_echo.test.js` the way `explore.camp` is covered there.

Register in `build_production_action_registry()` directly after the `explore.camp` spec, with `affected_panels=()` (a full snapshot, as the camp does). Add `"explore.landmark_rite"` to `_REQUEST_IDENTITY_ACTIONS` in `dispatcher.py` and to the listed identifiers in `web/webclient/actions/tests/test_dispatcher/test_registry.py`.

### D3. Text command (`commands/rite.py`)

```python
class CmdRite(Command):
    key = "rite"
    aliases = ("儀式",)
    locks = "cmd:all()"
    help_category = "General"
```

`commands/skip.py` uses `"General"` for its wait command; use `help_category = "General"`. Mount it in the same player cmdset of `commands/default_cmdsets.py` that mounts `CmdChurchPray`.

Argument grammar: `self.args.split()`.

- No token (listing): `owner = record_owner_for(caller)`, `site = rite_site_for(owner)`; no site -> the `rite_no_landmark` message. Otherwise emit one message: line 1 `<landmark_name>・<guardian_name_zh>`, line 2 the guardian form, then one line per option `　<label_zh>（<key>）` with the suffix `　已體驗` when the option key is in `seen_option_keys(owner, site.district_key)`, then `用法：儀式 <選項> [隊友]`. A `LandmarkRiteRecordError` while reading the seen list -> the `rite_record_corrupt` message. The listing writes nothing.
- One token: the option. Two tokens: the option and a companion name. More than two -> `用法：儀式 <選項> [隊友]`.
- Option token: match an option of the site's archetype by exact `key` or exact `label_zh`; no site -> `rite_no_landmark` message; no match -> `rite_unknown_option` message.
- Companion token: `resolve_member_token(caller, token)`; `PartyScopeError` -> the `rite_member_unavailable` message. Pass `member.id` as `member_id`.
- Perform: `perform_rite(caller, option.key, member_id, operation_id=None)`; `RiteRefused` -> `caller.msg(error.message)`. Success: `caller.msg(rite_scene_text(result))`, then `caller.msg(rite_completion_line(result))`.

Messages come from `world.rules.landmark_rites.REFUSAL_MESSAGES`.

### D4. Documentation

- `docs/game/commands.md`: one row for `rite` in the exploration table, linked like its neighbours.
- `docs/game/command-reference.md`: one entry for `rite` in the same format as `church pray` (key, alias `儀式`, the three syntaxes, context: standing on a district landmark, description: costs a few minutes of world time, changes the performer's sexual state, records the completion, may be repeated; refusals change nothing). Written in the document's language.
- `docs/development/webclient-synchronization.md`: beside the `explore.camp` bullet, one bullet stating that `explore.landmark_rite` takes exactly `{option, member_id}`, that the server resolves everything else from the record owner's node, and that its result data is `{delivery, first_completion}`.

### D5. Tests

`web/webclient/actions/tests/test_rite_actions.py`:

- pure validator tests (`unittest.TestCase`): the exact payload; an extra key, a missing key, a malformed option, a boolean or negative `member_id` each rejected;
- result schema test: the success result of the adapter passes `web.webclient.presentation.protocol.validate_ui_action_result` (wrap it the way the dispatcher does; find the wrapper in `web/webclient/actions/dispatcher.py`), and a copy whose delivery uses the key `revision` is rejected by it;
- adapter tests (`EvenniaTest`, the synthetic landmark fixture of `world/rules/tests/test_landmark_rites.py`; move that fixture into a small shared helper module under `world/rules/tests/` if it is not importable as is): success returns the code, the delivery (`kind` `formal`, a `delivery_id` of 1..128 ASCII characters, lines equal to the synthetic scene's lines in order, `actor_name` `你`) and `first_completion`; a companion request yields the companion's key as `actor_name` and replaces `{name}` in the synthetic watch scene's lines with that key, while a `{name}` in the synthetic self scene stays literal; each of two refusals (`rite_no_landmark`, `rite_unknown_option`) returns a rejected outcome with that code and changes nothing; two calls with one request identity settle once; an unexpected exception inside `perform_rite` (patched) returns `rite_failed`;
- `rite_scene_text`: a synthetic three-line scene (narration, actor speech, host speech) renders three lines with the two names prefixed.

`commands/tests/test_rite_command.py` (`EvenniaCommandTest`, same fixture): the listing shows the guardian, both options and the experienced mark only after a completion; `儀式 <key>` and `儀式 <label>` both perform and emit the whole scene followed by the completion line, in that order; `儀式 <key> <companion>` performs with the companion; an unknown option, an unknown companion and a non-landmark location each emit their refusal message and change nothing.

Register both modules in `.github/evennia-shards.json` (the action test beside `web.webclient.actions.tests.test_travel_actions`, the command test beside `commands.tests.test_church_commands`).

## Risks / Trade-offs

- The action is registered before any browser surface uses it. It is reachable only by a hand-built request, which goes through the same validation and settlement.
