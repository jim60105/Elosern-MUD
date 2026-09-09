"""Namespaced art-subject identity and deterministic subject descriptions.

Art subjects are the immutable identities the deterministic art backend keys
its records and jobs on. Three namespaces exist: ``scene:<archetype>``,
``portrait:character:<stable-key>``, and ``portrait:monster:<archetype>``.
Every access path -- queue, store, worker, command, presenter -- goes through a
parsed ``ArtSubject``; no raw full-key string is ever accepted.

Named-character portrait eligibility is explicit metadata (``portrait_policy``
on the character), never inferred from display-name uniqueness, quest role,
database key shape, or LLM authorship (design D2, focused design §3.3).
"""

from dataclasses import dataclass
from enum import StrEnum
import re
import unicodedata

from world.lore.monsters import MONSTER_TIER_REGISTRY
from world.lore.races import SUBRACE_REGISTRY
from world.lore.scene_archetypes import SCENE_ARCHETYPE_REGISTRY
from world.prompts.loader import PromptUnavailableError, render_prompt
from world.rules.persona import PersonaStore
from world.art.gallery_prompt import equipment_fragment

# The single shared stable-key contract (fix-art-pipeline-contracts D1): every
# producer of a portrait/scene stable key validates against these same rules.
# ``world/imports/schema.py`` (imported entity keys) and
# ``world/quests/characterization.py`` (quest portrait keys) consume this
# constant set so no producer set can drift. A valid key survives the queue
# record key, the worker output path, the media route, and the wire bound.
#
# Two independent length bounds: at most ``MAX_SUBJECT_KEY_LENGTH`` code
# points (the wire bound counts code points) and at most
# ``MAX_SUBJECT_KEY_BYTES`` UTF-8 bytes, so even 4-byte characters keep the
# worker output identity (``portrait/character/<key>.png`` = 23 bytes plus
# the key) and the queue record key (``art:<full key>``) within the 255-byte
# filesystem ``NAME_MAX`` and Evennia varchar bounds, with margin.
MAX_SUBJECT_KEY_LENGTH = 64
MAX_SUBJECT_KEY_BYTES = 200
FORBIDDEN_SUBJECT_KEY_CHARACTERS = frozenset("|/:{}")

# The digit-only region of the character-portrait keyspace is reserved for
# player characters, whose named-portrait stable keys are ``str(pk)`` (ASCII
# digit-only by construction). Every non-player producer -- the import schema
# pattern, the import key-contract check, and the quest characterization
# helper -- rejects a digit-only key through ``is_reserved_player_stable_key``
# below, so no import record, quest blueprint, or template can ever claim a
# player's portrait subject. The art layer itself keeps accepting digit-only
# keys: players are the legitimate owners and the policy dict cannot
# distinguish a player from an NPC.
DIGITS_ONLY_KEY_PATTERN = r"[0-9]+"


def is_reserved_player_stable_key(key: str) -> bool:
    """True when ``key`` occupies the digit-only region reserved for players.

    ASCII digits only: Django pks are ASCII-digit strings, so a key containing
    any non-ASCII digit (e.g. full-width ``０``) cannot equal a pk and stays
    legal. An empty string never matches and is handled by the callers' own
    non-empty checks.
    """
    return re.fullmatch(DIGITS_ONLY_KEY_PATTERN, key) is not None


class ArtSubjectError(ValueError):
    """Raised when an art subject is malformed or unresolvable."""


def character_ages(entity) -> tuple[int, int]:
    """Return the entity's validated canonical ``(age, apparent_age)`` pair.

    Portrait enqueue and presentation read the pair through here immediately
    before any queue write or payload render. The check is a pure function of
    the character's canonical attributes: each field must be present and an
    exact ``int`` (so booleans, strings, and ``None`` reject), and every
    integer is eligible. A rejection names the offending field in its
    diagnostic, produces no queue record and no prompt, and never reaches a
    worker fixture (design D3).
    """
    values: list[int] = []
    for field in ("age", "apparent_age"):
        value = entity.attributes.get(field)
        if value is None:
            raise ArtSubjectError(f"portrait rejected: {field} is missing")
        if type(value) is not int:
            raise ArtSubjectError(f"portrait rejected: {field} must be an integer")
        values.append(value)
    return values[0], values[1]


class ArtSubjectKind(StrEnum):
    """The three namespaced subject kinds (serialized prefix is the value)."""

    SCENE = "scene"
    CHARACTER = "portrait:character"
    MONSTER = "portrait:monster"


@dataclass(frozen=True)
class ArtSubject:
    """One typed, un-prefixed subject identity."""

    kind: ArtSubjectKind
    key: str

    def __post_init__(self) -> None:
        # Construction-time validation so the queue and store APIs can never
        # carry an unrepresentable key, even when a caller bypasses the typed
        # producer helpers (parse_subject / *_subject_for).
        _validate_subject_key(self.key)

    def full(self) -> str:
        """The serialized full subject key, e.g. ``scene:forest_path``."""
        return f"{self.kind.value}:{self.key}"


def _validate_subject_key(key: str) -> None:
    """Reject keys that cannot survive the queue, store path, or wire.

    The rule set is the shared producer contract: non-empty text, at most
    ``MAX_SUBJECT_KEY_LENGTH`` code points, at most ``MAX_SUBJECT_KEY_BYTES``
    UTF-8 bytes, no reserved separators (``|``, ``/``, ``:``, ``{``, ``}``),
    and no control characters. A key that passes here is always a single
    media-route segment, always fits the wire subject-key bound when combined
    with any kind prefix, and always keeps the worker output filename within
    the filesystem name-length limit.
    """
    if not isinstance(key, str) or not key:
        raise ArtSubjectError("an art subject key must be non-empty text")
    if len(key) > MAX_SUBJECT_KEY_LENGTH:
        raise ArtSubjectError(
            f"an art subject key must be at most {MAX_SUBJECT_KEY_LENGTH} characters"
        )
    if len(key.encode("utf-8")) > MAX_SUBJECT_KEY_BYTES:
        raise ArtSubjectError(
            f"an art subject key must be at most {MAX_SUBJECT_KEY_BYTES} UTF-8 bytes"
        )
    if any(char in FORBIDDEN_SUBJECT_KEY_CHARACTERS for char in key):
        raise ArtSubjectError(
            "an art subject key must not contain '|', '/', ':', '{', or '}'"
        )
    if any(
        not char.isprintable() or unicodedata.category(char).startswith("C")
        for char in key
    ):
        raise ArtSubjectError("an art subject key must not contain control characters")


def parse_subject(full_key: str) -> ArtSubject:
    """Parse a serialized full subject key into a typed ``ArtSubject``."""
    if not isinstance(full_key, str):
        raise ArtSubjectError("a full art subject key must be text")
    for kind in ArtSubjectKind:
        prefix = f"{kind.value}:"
        if full_key.startswith(prefix):
            key = full_key[len(prefix):]
            _validate_subject_key(key)
            return ArtSubject(kind, key)
    raise ArtSubjectError(f"unknown art subject prefix in {full_key!r}")


def scene_subject_for(archetype: str) -> ArtSubject:
    """Resolve and re-validate one scene subject from the immutable registry."""
    if archetype not in SCENE_ARCHETYPE_REGISTRY:
        raise ArtSubjectError(f"unknown scene archetype {archetype!r}")
    _validate_subject_key(archetype)
    return ArtSubject(ArtSubjectKind.SCENE, archetype)


def monster_subject_for(archetype: str) -> ArtSubject:
    """Resolve and re-validate one generic-monster subject from the bestiary."""
    if archetype not in MONSTER_TIER_REGISTRY:
        raise ArtSubjectError(f"unknown monster archetype {archetype!r}")
    _validate_subject_key(archetype)
    return ArtSubject(ArtSubjectKind.MONSTER, archetype)


def character_subject_for(entity) -> ArtSubject | None:
    """Derive a portrait subject only from an explicit named ``portrait_policy``.

    ``None`` and ``{"mode": "generic"}`` produce no unique portrait. Eligibility
    is never inferred from the display name, quest role, key shape, or LLM
    authorship.
    """
    policy = entity.db.portrait_policy if hasattr(entity, "db") else None
    if policy is None:
        return None
    if isinstance(policy, dict):
        policy = dict(policy)
    elif not hasattr(policy, "get"):
        raise ArtSubjectError("portrait_policy must be a mapping or None")
    mode = policy.get("mode")
    if mode == "generic":
        return None
    if mode == "named":
        stable_key = policy.get("stable_key")
        if not isinstance(stable_key, str):
            raise ArtSubjectError("a named portrait policy needs a text stable_key")
        _validate_subject_key(stable_key)
        return ArtSubject(ArtSubjectKind.CHARACTER, stable_key)
    raise ArtSubjectError(f"unknown portrait policy mode {mode!r}")


def _race_label(entity) -> str:
    subrace_key = entity.db.subrace
    if subrace_key:
        subrace = SUBRACE_REGISTRY.get(subrace_key)
        if subrace is not None:
            return subrace.display_name_zh
    return str(entity.db.race or "unknown race")


def _appearance_fragment(entity) -> str:
    """The persona ``appearance`` block as one bounded prompt fragment.

    Reads exactly the one ``appearance`` field through the read-only
    ``PersonaStore`` — personality, life_story, habit, background, identity
    (public or hidden), and social_connection are never touched — and reuses
    the store's shipped guarantees: ``_SUBKEY_ORDER`` declared sub-key order
    with the insertion-order tail, empty/numeric-value skipping, the per-field
    600-character cap, and a never-raising non-mapping record that renders as
    the empty string. The labeled block (``外觀：`` plus one line per sub-key)
    is appended after the base sentence, so a character with no appearance
    data contributes nothing.
    """
    block = PersonaStore(entity).flatten(("appearance",))
    if block is None:
        return ""
    return "\n" + block


def character_description(entity, age: int, *, fields, custom_prompt: str = "") -> str:
    """One deterministic description for a character portrait.

    The template (rendered from the prompt library) covers only stable,
    validated identity: the display name, race/subrace label, the age, and the
    approved-visual-style fragment, and — as the one admitted persona
    exception — the authored physical ``appearance`` block rendered in the
    declared ``_SUBKEY_ORDER`` order (portrait-prompt-appearance), admitted
    when and only when the caller selects the ``appearance`` field. The
    description is composable by the explicit ``fields`` selection (change
    ``gallery-prompt-composition``): selected equipment fields add the
    registry ``ItemPresentation`` visual text of the occupying items, and
    ``custom_prompt`` — already validated at the service boundary — is
    appended verbatim through its own template slot. Selecting nothing
    reproduces exactly the pre-appearance description. Every other persona
    key, secret state, mutable combat resources, and disguised stats are
    never included (design D6 as narrowed by that change). A broken library
    key degrades to a deterministic registry-driven fallback (design D3) so
    the art pipeline never stalls; the fallback reads no persona, no
    equipment, and no free text, which is why both library renders complete
    before any data read.
    """
    race = _race_label(entity)
    name = entity.db.display_name or entity.key or "<unknown>"
    try:
        style = render_prompt("art.style")
        base = render_prompt(
            "art.character_description",
            race=race,
            name=name,
            age=str(age),
            style=style,
            appearance="",
            equipment="",
            custom="",
        )
    except PromptUnavailableError:
        return f"{name}（{race}，{age} 歲）"
    appearance = _appearance_fragment(entity) if "appearance" in fields else ""
    equipment = equipment_fragment(entity, fields)
    custom = "\n" + custom_prompt if custom_prompt else ""
    if not (appearance or equipment or custom):
        return base
    try:
        return render_prompt(
            "art.character_description",
            race=race,
            name=name,
            age=str(age),
            style=style,
            appearance=appearance,
            equipment=equipment,
            custom=custom,
        )
    except PromptUnavailableError:
        # observability: ignore R2: the library is frozen after the startup
        # load, so a key can only turn unavailable between the two renders
        # when a test swaps it; the appearance-free base is a valid
        # deterministic description and must never lose the portrait.
        return base


def scene_description(subject: ArtSubject) -> str:
    """The immutable one-sentence registry description for a scene subject."""
    archetype = SCENE_ARCHETYPE_REGISTRY[subject.key]
    return archetype.scene_sentence


def monster_description(subject: ArtSubject) -> str:
    """The deterministic bestiary description for a generic-monster subject."""
    tier = MONSTER_TIER_REGISTRY[subject.key]
    examples = "、".join(tier.example_monsters_zh)
    try:
        return render_prompt(
            "art.monster_description",
            description=tier.description,
            display_name=tier.display_name_zh,
            examples=examples,
        )
    except PromptUnavailableError:
        return tier.description


def description_for(subject: ArtSubject, *, entity=None, age=None, fields=None, custom_prompt="") -> str:
    """Return the canonical deterministic description for a subject.

    A character description requires an EXPLICIT field selection (change
    ``gallery-prompt-composition``): ``fields`` is mandatory for a character
    subject so no seam can keep an implicit appearance default. Scene and
    monster descriptions are registry text and ignore ``fields`` and
    ``custom_prompt`` entirely.
    """
    if subject.kind is ArtSubjectKind.SCENE:
        return scene_description(subject)
    if subject.kind is ArtSubjectKind.MONSTER:
        return monster_description(subject)
    if entity is None or age is None:
        raise ArtSubjectError(
            "a character description requires the entity and age"
        )
    if fields is None:
        raise ArtSubjectError(
            "a character description requires an explicit field selection"
        )
    return character_description(entity, age, fields=fields, custom_prompt=custom_prompt)
