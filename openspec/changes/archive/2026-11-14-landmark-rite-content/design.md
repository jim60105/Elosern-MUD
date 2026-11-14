# Design

## Context

Design document: `docs/superpowers/specs/2026-11-14-landmark-rites-design.md` §6 (document shape, bounds, archetype table) and §11 (adult content and authoring rules). `landmark-rite-content-model` provides `world.lore.rites.loader.load_rites`, `world.lore.rites.install` and `world.lore.rites.CONTENT_PATH`.

The published district world is `world.lore.map_districts.current().districts` (a mapping keyed by district key). The map world is adopted by the startup step `map_world_adoption` in `server/conf/at_server_startstop.py`. The district source document is `content/maps/districts.yaml`; each district carries `district_name_zh` and `landmark_name_zh`.

## Goals / Non-Goals

**Goals**

- A loadable shipped document that assigns every district shipped today, with the first five archetypes authored.
- The server never runs with an invalid or missing rite document.

**Non-Goals**

- No `watch` scene (every option ships `watch: null`), no third option, no art subject.
- No rule, panel, command or lighting change. Nothing reads the snapshot in this change.
- No test of prose, tone, counts of archetypes or options, or any authored value. The data-contract test proves only that the shipped document validates.
- No re-adoption when the map world is re-adopted at runtime by a development tool. The snapshot is loaded once per process start.

## Decisions

### D1. `load_published` (`world/lore/rites/__init__.py`)

```python
def load_published(path: Path | None = None, *, district_keys: frozenset[str] | None = None) -> RiteSnapshot:
    """Load the shipped document against the published districts and install it."""
```

`path` defaults to `CONTENT_PATH`. `district_keys` defaults to `frozenset(world.lore.map_districts.current().districts)`, imported inside the function. It calls `load_rites`, then `install`, and returns the snapshot. Every exception propagates; nothing is installed on failure and a previously installed snapshot stays current.

### D2. Startup step (`server/conf/at_server_startstop.py`)

Add, immediately after the `map_world_adoption` step and before `world_clock_init`:

```python
_startup_step("landmark_rites_adoption", lambda: _late("world.lore.rites", "load_published"))
```

Use the default fail-loud behaviour of `_startup_step` (do not pass `fail_loud=False`). Add `"landmark_rites_adoption"` to `STARTUP_STEP_ORDER` in the same module, immediately after `"map_world_adoption"`.

`server/conf/tests/test_startup_observability.py` stubs every step body through its `_BODY_TARGETS` tuple and asserts the order against `STARTUP_STEP_ORDER`; add `"world.lore.rites.load_published"` to `_BODY_TARGETS` so the new fail-loud step does not run for real under the stubbed map adoption. `tests/test_map_runtime_contract.py` also reads the order.

### D3. The document

Path `world/lore/rites/content/landmark_rites.yaml`, exactly the shape of the design's §6.1. This change authors the archetype keys `spring`, `statue`, `megalith`, `tower`, `tree`; `landmark-rite-content-completion` adds `grave`, `mine`, `gate`, `cliff`, `plaza`. Each archetype has `guardian_name_zh`, `guardian_form_zh` and exactly two options. Each option has `key`, `label_zh`, `seconds`, `shame`, `exposure`, a `self` scene of four to eight lines, and `watch: null`.

Scene identifiers are `rite.<archetype>.<option>.self` with `revision: r1`.

Assignment: list every district with
`uv run --locked python -c "from world.lore.map_districts import parse_districts_document, DISTRICTS_PATH; from pathlib import Path; d=parse_districts_document(Path(DISTRICTS_PATH).read_text(encoding='utf-8')).districts; [print(k, v.district_name_zh, v.landmark_name_zh) for k, v in d.items()]"`
(if `DISTRICTS_PATH` is repository-relative, run from the repository root). Assign by the landmark's kind, in this order of precedence:

1. The representative landmarks named in the first five rows of the design's §6.3 table take the archetype of their row.
2. Otherwise by what the landmark is: a spring, well or pool is `spring`; a statue or carved figure is `statue`; a standing stone, stone ring or rune stone is `megalith`; a tower is `tower`; a tree is `tree`.
3. Every other district is provisional: assign it the one of the five whose ritual register (the §6.3 third column) fits its landmark least badly, and put it under a YAML comment line `# provisional: reassigned by landmark-rite-content-completion` so the later change finds them. A waterfall or cliff goes to `spring` or `tower`, a tomb to `statue`, a cave or mine to `megalith`, a gate or bridge to `megalith`, the city plaza to `statue`.

The loader requires every declared archetype to be used; all five are.

### D4. Authoring rules

Every scene obeys the design's §11 in full. The points a writer most easily misses:

- The guardian is a woman, a non-human presence or a sexless force; never male or male-figured. No male or male-figured partner appears.
- The `self` scene is second person (你) and assumes a female acting body.
- Each option shows three beats through action and object response: the acting body gains information, interacts with the landmark object, and climaxes. Nothing is stated as "you learn" or "you feel".
- Traditional Chinese with full-width punctuation, JRPG sword-and-sorcery vocabulary, no 武俠 vocabulary, no mention of a command, mechanic or interface element.
- Speakers are only `actor` and `host`; every scene has at least one narration line.
- The two options of one archetype are different stories with different object interactions, not two wordings of one.

`seconds`, `shame` and `exposure` are authored within the loader's bounds; an option whose scene exposes the body to onlookers or open sky carries a higher `exposure` than one in an enclosed space, and an option built on being watched or on the dead speaking carries a higher `shame`.

### D5. Review document (`docs/lore/landmark-rites-review.md`)

Human-reviewed. Follow the layout of an existing review such as `docs/lore/guild-dialogue-review.md`: a header stating scope and date, then one section per archetype with a row per option stating the guardian, the object interaction, where the information beat and the climax beat occur (line numbers), and a pass or fail against each §11 rule. End with the count of provisional districts (rule 3 of D3). State at the top that the review is human judgement and is not asserted by any test.

### D6. Tests

- `world/lore/tests/test_rite_content.py` (existing, synthetic): add tests of `load_published` with an injected temporary path and injected `district_keys`: a valid document installs and becomes `current()`; an invalid document raises `RiteContentError` and leaves the previously installed snapshot current; a missing file raises and installs nothing. Wrap each in `installed(...)` or restore with `uninstall()` so nothing leaks.
- `world/lore/tests/test_rite_content_document.py` (new, plain `unittest.TestCase`): first docstring line `Data-contract test: the shipped rite document validates against the shipped districts`. One test: parse `content/maps/districts.yaml` with `world.lore.map_districts.parse_districts_document`, take its district keys, and call `load_rites(CONTENT_PATH, district_keys=...)`; assert it returns a snapshot whose `districts` keys equal those district keys. Assert nothing else. Register the module in `.github/evennia-shards.json` beside `world.lore.tests.test_rite_content`, and in both `tools/test_data_freeze.json` and `tools/test_data_lint_seed.json` with the reason `the shipped rite document validates against the shipped districts` (the data lint requires the ledger reason, the seed reason and the docstring rationale to be the same string).

## Risks / Trade-offs

- Content volume is the cost of this change: ten scenes and the assignment. The mechanism is two small functions.
- Until `landmark-rite-content-completion`, a provisional landmark is assigned a neighbouring family. No player can reach a rite before `landmark-rite-action`, which depends on the completion, so the provisional assignment is never visible.
- A district added to `content/maps/districts.yaml` later without a rite assignment stops the server at startup and fails the data-contract test. That is intended: no district may be unlit by construction.
