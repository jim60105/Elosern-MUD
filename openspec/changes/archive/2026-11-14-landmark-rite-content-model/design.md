# Design

## Context

Design document: `docs/superpowers/specs/2026-11-14-landmark-rites-design.md` §5 and §6. Existing models this change reuses:

- `world/lore/scenes.py`: `Scene(scene_id, revision, lines)`, `Speech(speaker, text)`, `Narration(text)`, `STATIC_SCENE_ID_PATTERN`, `REVISION_PATTERN`. `Scene.__post_init__` already enforces 1..32 lines, 16000 code points and 8192 canonical bytes.
- `world/lore/dialogue/loader.py`: `StrictDialogueYamlLoader` (a `yaml.SafeLoader` that rejects duplicate mapping keys). Import and reuse it; do not copy it.

## Goals / Non-Goals

**Goals**

- One pure, deterministic loader: text in, immutable snapshot or a rejection out.
- Completeness proved in one pass: every district assigned once, every archetype used.

**Non-Goals**

- No shipped YAML document and no startup step (change `landmark-rite-content`).
- No art subject registration (change `landmark-rite-art`). The loader does not check that `rite_<archetype>` is a registered scene archetype.
- No check of tone, person, pronouns or the three narrative beats of the design's §11. A human reviews those in `docs/lore/landmark-rites-review.md` (change `landmark-rite-content`).
- No rules, settlement, panel or command code.

## Decisions

### D1. Shapes (`world/lore/rites/shape.py`)

Frozen, slotted dataclasses that only store values:

```python
@dataclass(frozen=True, slots=True)
class RiteOption:
    key: str
    label_zh: str
    seconds: int
    shame: int
    exposure: int
    self_scene: Scene
    watch_scene: Scene | None

@dataclass(frozen=True, slots=True)
class RiteArchetype:
    key: str
    guardian_name_zh: str
    guardian_form_zh: str
    options: tuple[RiteOption, ...]

    def option(self, key: str) -> RiteOption | None: ...

@dataclass(frozen=True, slots=True)
class RiteSnapshot:
    archetypes: Mapping[str, RiteArchetype]   # MappingProxyType
    districts: Mapping[str, str]              # district key -> archetype key, MappingProxyType

    def archetype_for(self, district_key: str) -> RiteArchetype | None: ...

def art_subject_key(archetype_key: str) -> str:
    return f"rite_{archetype_key}"
```

### D2. Loader (`world/lore/rites/loader.py`)

```python
MAX_RITES_FILE_BYTES = 1_048_576
KEY_PATTERN = re.compile(r"^[a-z][a-z0-9_]{0,31}\Z")

@dataclass(frozen=True, slots=True)
class RiteDiagnostic:
    field_path: str   # e.g. "archetypes.spring.options[1].seconds"
    code: str
    message: str

class RiteContentError(ValueError):
    diagnostics: tuple[RiteDiagnostic, ...]   # sorted by (field_path, code)

def parse_rites_document(text: str, *, district_keys: frozenset[str]) -> RiteSnapshot: ...
def load_rites(path: Path, *, district_keys: frozenset[str]) -> RiteSnapshot: ...
```

`load_rites` reads at most `MAX_RITES_FILE_BYTES` (a larger file: `document_shape`) and calls `parse_rites_document`. The parser collects every diagnostic of the document and raises once; it never raises on the first fault.

Top level: exactly the keys `version` (integer `1`), `kind` (`landmark_rites`), `id` (`landmark_rites`), `archetypes`, `districts`.

| Field | Rule | Code |
| --- | --- | --- |
| any mapping | unknown key / missing key or wrong container type | `unknown_field` / `document_shape` |
| `archetypes` | mapping of 1..16 entries | `archetype_count` |
| archetype key, option `key` | `KEY_PATTERN` | `key_format` |
| `guardian_name_zh` | string, 1..32 code points | `text_bound` |
| `guardian_form_zh` | string, 1..200 code points | `text_bound` |
| `options` | sequence of 2..3 | `option_count` |
| option `key` | unique within its archetype | `duplicate_option` |
| `label_zh` | string, 1..32 code points | `text_bound` |
| `seconds` | non-bool int, 120..900 | `seconds_bound` |
| `shame`, `exposure` | non-bool int, 0..2 | `level_bound` |
| `self` | scene document (D3) | `scene_invalid` |
| `watch` | scene document (D3) or explicit `null`; the key itself is required | `scene_invalid` |
| any scene | at least one narration line | `scene_no_narration` |
| `scene_id` | unique across the whole document | `duplicate_scene_id` |
| `districts` | mapping district key -> archetype key | `document_shape` |
| district key | member of `district_keys` | `district_unknown` |
| `district_keys` member | present in `districts` | `district_unassigned` |
| assigned archetype | declared in `archetypes` | `archetype_unknown` |
| declared archetype | assigned to at least one district | `archetype_unused` |

### D3. Scene document

A scene mapping has exactly `scene_id`, `revision`, `lines`. `scene_id` must match `STATIC_SCENE_ID_PATTERN`; `revision` must match `REVISION_PATTERN`. Each line is `{kind: narration, text}` or `{kind: speech, speaker: actor|host, text}` with no other key. Build `Narration`/`Speech`, then `Scene(...)`; a `ValueError` or `TypeError` from those constructors becomes one `scene_invalid` diagnostic carrying the constructor's message. The dialogue rule that a formal scene opens with an actor utterance is not applied.

### D4. Snapshot holder (`world/lore/rites/__init__.py`)

```python
CONTENT_PATH = Path(__file__).resolve().parent / "content" / "landmark_rites.yaml"

class RitesNotLoaded(RuntimeError): ...

def current() -> RiteSnapshot: ...                     # raises RitesNotLoaded when nothing is installed
def install(snapshot: RiteSnapshot) -> RiteSnapshot: ... # TypeError on any other type
def uninstall() -> None: ...
@contextmanager
def installed(snapshot: RiteSnapshot) -> Iterator[RiteSnapshot]: ...  # restores the previous value on exit
```

`current()` never loads implicitly. `installed()` is the test seam every later change uses to supply a synthetic snapshot.

### D5. Tests (`world/lore/tests/test_rite_content.py`)

Plain `unittest.TestCase`, no database. A module-level helper builds a minimal valid synthetic document (one archetype `alpha`, two options, district keys `{"d1", "d2"}`) as a Python dict and dumps it with `yaml.safe_dump(allow_unicode=True)`; each test mutates a deep copy. Cover:

- the valid document and the snapshot's read methods;
- every code of D2 with its field path asserted;
- three unrelated faults reported in one error;
- `watch: null` accepted and a missing `watch` key rejected;
- a narration-first scene accepted and a speech-only scene rejected;
- snapshot immutability (assigning into `archetypes` raises `TypeError`);
- `current()` before `install`, and `installed()` restoring the prior value.

All text in the synthetic document is placeholder text, never shipped prose.

## Risks / Trade-offs

- The holder is process-global like `world/lore/map_districts.py`. Tests must use `installed()` so no snapshot leaks between tests.
