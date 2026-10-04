"""Permissioned composition, rendered budget accounting, and immutable context snapshots.

Enforces:
1. Stable ordering: global_rules, world_digest, capability_contract,
   character_anchor, epoch_summary, turn_frames (including recall items and affordances).
2. One rendered representation for selection and assembly:
   headings and attribution count toward section and profile budgets.
3. Budget enforcement:
   Total context budget = profile context window.
   Reservations:
     - completion reservation (max_completion_tokens or max_tokens)
     - future Deep Recall reservation
     - estimation safety margin
   Section targets and hard bounds (both measured on the rendered representation):
     - Mandatory sections (global_rules, capability_contract, character_anchor) are never
       silently removed; exceeding a hard bound or the aggregate input budget rejects
       before generation.
     - Optional sections are deterministically reduced to the tighter of their soft
       target, hard bound, and remaining budget, or omitted.
     - Retry feedback messages are accounted against the captured input budget.
4. Immutable snapshots:
   Retains capability, prompt_version, schema_version, rendering_version, estimator
   version, source IDs, read revisions, section hashes, budget accounting, truncation
   decisions, and the reconstructible rendered payload (design decision 3: payload or
   reconstructible sources, never hashes alone). The narrative database is the
   controlled storage; prompt text never enters normal operational logs.
5. Invalidation and provenance:
   Owner memory-generation changes surface on every fresh assembly, so new
   generations see changed effective memory; historical snapshots are never rewritten.
   Retries re-read the authoritative persisted snapshot and reuse captured revisions.
6. Thin descriptors:
   Binds messages, validators, snapshot_id, trace_id, capability, versions, and
   rejects descriptors that mix a context with unrelated snapshot provenance.
"""

from __future__ import annotations

import hashlib
import json
import re
import uuid
from collections.abc import Mapping
from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Any, Callable, Sequence

from world.ai.profiles import LLMProfile
from world.ai.schemas.descriptor import ChatRequestDescriptor
from world.narrative.memory import MemoryRecordView, get_owner_generation
from world.narrative.models import NarrativeContextSnapshot
from world.narrative.threads import get_thread_revision
from world.observability import log_info, log_warn

# Rendering and estimator versions
RENDERING_VERSION = "rendering_v1"
ESTIMATOR_VERSION = "token_est_v3"

# Configured reservation defaults (in estimated tokens), per-profile overridable
DEFAULT_PROFILE_CONTEXT_WINDOW = 4096
DEFAULT_DEEP_RECALL_RESERVATION = 512
DEFAULT_ESTIMATION_SAFETY_MARGIN = 256

# Section order by stability per architecture doc §4.3
SECTION_ORDER = (
    "global_rules",
    "world_digest",
    "capability_contract",
    "character_anchor",
    "epoch_summary",
    "turn_frames",
)

MANDATORY_SECTIONS = frozenset(
    {"global_rules", "capability_contract", "character_anchor"}
)

OPTIONAL_SECTIONS = frozenset(
    {"world_digest", "epoch_summary", "turn_frames"}
)


class ContextBudgetExceededError(ValueError):
    """Raised when mandatory prompt sections or minimum required context exceeds budget."""


class ContextPermissionError(PermissionError):
    """Raised when context composition requests unauthorized sources or owner access."""


class SnapshotNotFoundError(KeyError):
    """Raised when a requested context snapshot does not exist."""


class ContextProvenanceError(ValueError):
    """Raised when a snapshot cannot reconstruct its captured messages or provenance disagrees."""


_CJK_CHAR_REGEX = re.compile(r"[一-鿿㐀-䶿豈-﫿]")
_WORD_REGEX = re.compile(r"[a-zA-Z0-9_-]+")


def estimate_tokens(text: str) -> int:
    """Deterministic, conservative token estimator (token_est_v3).

    Length-sensitive on every character class so no input can undercount without
    bound (fractions carry inside one call; the value floors once):
    - CJK characters: 2.0 tokens per character.
    - Latin/alphanumeric runs: max(1.3, 0.25 * length) tokens per run.
    - Punctuation / symbols: 1.0 token per character.
    - Whitespace: 0.25 token per character.
    """
    if not text:
        return 0

    cjk_count = len(_CJK_CHAR_REGEX.findall(text))
    non_cjk = _CJK_CHAR_REGEX.sub(" ", text)
    words = _WORD_REGEX.findall(non_cjk)
    word_est = sum(max(1.3, 0.25 * len(word)) for word in words)
    symbols = _WORD_REGEX.sub("", non_cjk)
    symbol_count = len([c for c in symbols if not c.isspace()])
    whitespace_count = len(symbols) - symbol_count

    est = int(cjk_count * 2.0 + word_est + symbol_count + whitespace_count * 0.25)
    return max(1, est) if text.strip() else 0


def _deep_freeze(value: Any) -> Any:
    """Recursively convert mappings (incl. nested) to read-only proxies."""
    if isinstance(value, Mapping):
        return MappingProxyType({key: _deep_freeze(item) for key, item in value.items()})
    if isinstance(value, (list, tuple)):
        return tuple(_deep_freeze(item) for item in value)
    return value


def _plain(value: Any) -> Any:
    """Recursively convert frozen proxies back to JSON-serializable containers."""
    if isinstance(value, Mapping):
        return {key: _plain(item) for key, item in value.items()}
    if isinstance(value, tuple):
        return [_plain(item) for item in value]
    return value


@dataclass(frozen=True)
class RenderedSection:
    """One rendered section with its heading, content, and token accounting."""

    name: str
    heading: str
    content: str
    mandatory: bool
    rendered_text: str = ""
    token_count: int = 0
    sha256: str = ""

    def __post_init__(self) -> None:
        if not self.rendered_text:
            rendered = f"### {self.heading}\n{self.content}".strip()
            object.__setattr__(self, "rendered_text", rendered)
        if not self.token_count:
            tokens = estimate_tokens(self.rendered_text)
            object.__setattr__(self, "token_count", tokens)
        if not self.sha256:
            digest = hashlib.sha256(self.rendered_text.encode("utf-8")).hexdigest()
            object.__setattr__(self, "sha256", digest)


@dataclass(frozen=True)
class BudgetProfile:
    """Configured budget for one capability and profile."""

    context_window: int = DEFAULT_PROFILE_CONTEXT_WINDOW
    completion_reservation: int = 250
    deep_recall_reservation: int = DEFAULT_DEEP_RECALL_RESERVATION
    safety_margin: int = DEFAULT_ESTIMATION_SAFETY_MARGIN
    section_targets: Mapping[str, int] = field(default_factory=dict)
    section_bounds: Mapping[str, int] = field(default_factory=dict)

    @property
    def total_reserved(self) -> int:
        return (
            self.completion_reservation
            + self.deep_recall_reservation
            + self.safety_margin
        )

    @property
    def max_input_budget(self) -> int:
        available = self.context_window - self.total_reserved
        if available <= 0:
            raise ContextBudgetExceededError(
                f"Reservations ({self.total_reserved}) exceed context window ({self.context_window})"
            )
        return available


@dataclass(frozen=True)
class SourceReference:
    """Immutable provenance record for a source utilized in context assembly."""

    source_id: str
    record_id: int
    revision_number: int
    knowledge_scope: str
    owner_id: str
    sha256: str
    thread_revision: int = 0


@dataclass(frozen=True)
class AssembledContext:
    """Detached, immutable plain-value representation of assembled cognition context."""

    capability: str
    prompt_version: str
    schema_version: str
    rendering_version: str
    owner_id: str
    owner_generation: int
    sections: tuple[RenderedSection, ...]
    sources: tuple[SourceReference, ...]
    budget_accounting: Mapping[str, Any]
    truncation_decisions: tuple[str, ...]
    system_prompt: str
    user_prompt: str
    thread_id: str = ""
    thread_revision: int = 0
    thread_revisions: Mapping[str, int] = field(default_factory=dict)

    def get_section_hashes(self) -> dict[str, str]:
        return {s.name: s.sha256 for s in self.sections}

    def to_messages(self) -> tuple[dict[str, str], ...]:
        return (
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": self.user_prompt},
        )


@dataclass(frozen=True)
class NarrativeRequestDescriptor:
    """Thin companion descriptor binding LLM call parameters and snapshot provenance."""

    chat_descriptor: ChatRequestDescriptor
    capability: str
    prompt_version: str
    schema_version: str
    rendering_version: str
    snapshot_id: str
    trace_id: str
    owner_id: str
    owner_generation: int

    @property
    def messages(self) -> tuple[dict[str, str], ...]:
        return self.chat_descriptor.messages

    @property
    def output_schema(self) -> Mapping[str, Any] | None:
        return self.chat_descriptor.output_schema

    @property
    def schema_id(self) -> str | None:
        return self.chat_descriptor.schema_id

    @property
    def semantic_validators(self) -> Mapping[str, Callable[[Any], list[str]]] | None:
        return self.chat_descriptor.semantic_validators


def build_budget_profile(
    llm_profile: LLMProfile,
    *,
    context_window: int = DEFAULT_PROFILE_CONTEXT_WINDOW,
    deep_recall_reservation: int = DEFAULT_DEEP_RECALL_RESERVATION,
    safety_margin: int = DEFAULT_ESTIMATION_SAFETY_MARGIN,
    section_targets: Mapping[str, int] | None = None,
    section_bounds: Mapping[str, int] | None = None,
) -> BudgetProfile:
    """Build a BudgetProfile respecting LLMProfile completion settings."""
    completion_res = (
        llm_profile.max_completion_tokens
        if llm_profile.max_completion_tokens is not None
        else llm_profile.max_tokens
    )

    targets = dict(section_targets or {})
    bounds = dict(section_bounds or {})

    default_targets = {
        "global_rules": 200,
        "world_digest": 400,
        "capability_contract": 300,
        "character_anchor": 500,
        "epoch_summary": 400,
        "turn_frames": 1000,
    }
    default_bounds = {
        "global_rules": 400,
        "world_digest": 800,
        "capability_contract": 600,
        "character_anchor": 1000,
        "epoch_summary": 800,
        "turn_frames": 2000,
    }
    for k, v in default_targets.items():
        targets.setdefault(k, v)
    for k, v in default_bounds.items():
        bounds.setdefault(k, v)

    return BudgetProfile(
        context_window=context_window,
        completion_reservation=completion_res,
        deep_recall_reservation=deep_recall_reservation,
        safety_margin=safety_margin,
        section_targets=MappingProxyType(targets),
        section_bounds=MappingProxyType(bounds),
    )


def _reduce_optional_section(
    *,
    name: str,
    heading: str,
    parts: list[str],
    hard_limit: int,
    joiner: str,
    drop_oldest: bool,
    truncation_decisions: list[str],
) -> RenderedSection | None:
    """Deterministically reduce an optional section's rendered representation.

    Reduces on the SAME rendered representation used for final assembly (heading and
    attribution included) until the section fits ``hard_limit``, dropping oldest turn
    frames first and trailing content lines otherwise. Returns None when even the
    heading alone cannot fit or no content remains, per the caller's omission path.
    """
    sec = RenderedSection(name=name, heading=heading, content=joiner.join(parts), mandatory=False)
    while sec.token_count > hard_limit and parts:
        dropped = parts.pop(0) if drop_oldest else parts.pop()
        truncation_decisions.append(
            f"truncated_{name}:dropped_{estimate_tokens(dropped)}_tokens"
        )
        sec = RenderedSection(
            name=name, heading=heading, content=joiner.join(parts), mandatory=False
        )
    if not parts or sec.token_count > hard_limit:
        return None
    return sec


def assemble_narrative_context(
    *,
    capability: str,
    prompt_version: str,
    owner_id: str,
    requester_id: str,
    budget_profile: BudgetProfile,
    global_rules: str,
    capability_contract: str,
    character_anchor: str,
    world_digest: str = "",
    epoch_summary: str = "",
    turn_frames: Sequence[str] = (),
    recalled_memories: Sequence[MemoryRecordView] = (),
    affordances: Sequence[str] = (),
    schema_version: str = "",
    rendering_version: str = RENDERING_VERSION,
    trace_id: str = "",
    thread_id: str = "",
) -> AssembledContext:
    """Assemble reproducible cognition context obeying permission and budget rules."""
    clean_owner = str(owner_id).strip()
    clean_requester = str(requester_id).strip()

    # 1. Permission checks: requester must be authorized
    if clean_requester != clean_owner:
        # Cross-owner cognition access forbidden
        raise ContextPermissionError(
            f"Requester {clean_requester!r} cannot assemble cognition context for owner {clean_owner!r}"
        )

    # Monotonic generation check (fresh read: new generations see effective changes)
    owner_gen = get_owner_generation(clean_owner)

    # Thread revision read identities: the explicit recall scope plus every thread
    # referenced by a validated source memory. New assemblies read the current
    # revision; historical snapshots keep the revision they captured.
    explicit_thread = str(thread_id).strip()
    thread_revisions: dict[str, int] = {}
    if explicit_thread:
        thread_revisions[explicit_thread] = get_thread_revision(explicit_thread)

    # 2. Validate external sources against permission boundary
    sources_provenance: list[SourceReference] = []
    validated_memories: list[MemoryRecordView] = []
    rejected_source_count = 0

    for mem in recalled_memories:
        if mem.owner_id != clean_owner and mem.knowledge_scope != "public":
            # Inaccessible memory: excluded before scoring, counted without content
            rejected_source_count += 1
            continue
        source_thread = str(mem.relations.get("thread_id", "")).strip()
        if source_thread:
            thread_revisions.setdefault(source_thread, get_thread_revision(source_thread))
        mem_hash = hashlib.sha256(
            json.dumps(mem.content, sort_keys=True, ensure_ascii=False).encode("utf-8")
        ).hexdigest()
        sources_provenance.append(
            SourceReference(
                source_id=mem.source_id or f"mem:{mem.id}",
                record_id=mem.id,
                revision_number=mem.revision_number,
                knowledge_scope=mem.knowledge_scope,
                owner_id=mem.owner_id,
                sha256=mem_hash,
                thread_revision=thread_revisions.get(source_thread, 0),
            )
        )
        validated_memories.append(mem)

    # 3. Format Turn Frames combining turn history, recall items, and affordances.
    # Ordering: historical frames, recall results, affordances in current frame.
    turn_parts: list[str] = []
    for frame in turn_frames:
        turn_parts.append(frame.strip())

    if validated_memories:
        mem_lines = ["【記憶回想】"]
        for m in validated_memories:
            summary = m.content.get("summary", "")
            mem_lines.append(f"- [{m.knowledge_scope}] {summary}")
        turn_parts.append("\n".join(mem_lines))

    if affordances:
        aff_lines = ["【當前可行動作】"]
        for a in affordances:
            aff_lines.append(f"- {a}")
        turn_parts.append("\n\n".join(aff_lines))

    turn_frames_text = "\n\n".join(turn_parts)

    # 4. Construct raw sections in stable stability order
    raw_sections: dict[str, tuple[str, str, bool]] = {
        "global_rules": ("全域規範", global_rules, True),
        "world_digest": ("世界背景", world_digest, False),
        "capability_contract": ("能力契約", capability_contract, True),
        "character_anchor": ("人物定錨", character_anchor, True),
        "epoch_summary": ("紀元摘要", epoch_summary, False),
        "turn_frames": ("對話與行動歷程", turn_frames_text, False),
    }

    # 5. Enforce section soft targets and hard rendered bounds
    max_input_budget = budget_profile.max_input_budget
    truncation_decisions: list[str] = []
    final_sections: list[RenderedSection] = []

    # First pass: mandatory sections are never reduced or removed; they reject
    mandatory_tokens_total = 0
    mandatory_sections_map: dict[str, RenderedSection] = {}

    for name in SECTION_ORDER:
        if name not in MANDATORY_SECTIONS:
            continue
        heading, content, _mandatory = raw_sections[name]
        sec = RenderedSection(name=name, heading=heading, content=content, mandatory=True)
        bound = budget_profile.section_bounds[name]
        if sec.token_count > bound:
            log_warn(
                "narrative_context_budget_exceeded",
                context={
                    "capability": capability,
                    "section": name,
                    "tokens": sec.token_count,
                    "bound": bound,
                    "mandatory": True,
                },
            )
            raise ContextBudgetExceededError(
                f"Mandatory section {name!r} tokens ({sec.token_count}) exceeds hard bound ({bound})"
            )
        mandatory_tokens_total += sec.token_count
        mandatory_sections_map[name] = sec

    if mandatory_tokens_total > max_input_budget:
        log_warn(
            "narrative_context_budget_exceeded",
            context={
                "capability": capability,
                "mandatory_tokens": mandatory_tokens_total,
                "bound": max_input_budget,
                "mandatory": True,
            },
        )
        raise ContextBudgetExceededError(
            f"Mandatory sections total tokens ({mandatory_tokens_total}) exceeds max input budget ({max_input_budget})"
        )

    # Second pass: optional sections reduced deterministically on the rendered
    # representation to the tighter of soft target, hard bound, and remaining budget
    remaining_budget = max_input_budget - mandatory_tokens_total
    optional_sections_map: dict[str, RenderedSection] = {}

    for name in SECTION_ORDER:
        if name not in OPTIONAL_SECTIONS:
            continue
        heading, content, _mandatory = raw_sections[name]
        if not content:
            continue

        target = budget_profile.section_targets[name]
        bound = budget_profile.section_bounds[name]
        hard_limit = min(target, bound, remaining_budget)

        if name == "turn_frames":
            parts = list(turn_parts)
            joiner, drop_oldest = "\n\n", True
        else:
            parts = content.split("\n")
            joiner, drop_oldest = "\n", False

        sec = RenderedSection(name=name, heading=heading, content=content, mandatory=False)
        if sec.token_count > hard_limit:
            sec = _reduce_optional_section(
                name=name,
                heading=heading,
                parts=parts,
                hard_limit=hard_limit,
                joiner=joiner,
                drop_oldest=drop_oldest,
                truncation_decisions=truncation_decisions,
            )
            if sec is None:
                truncation_decisions.append(f"omitted_entire_section:{name}")
                continue

        if sec.token_count <= remaining_budget:
            optional_sections_map[name] = sec
            remaining_budget -= sec.token_count
        else:
            truncation_decisions.append(f"omitted_entire_section:{name}")

    # Final assembly in stable order: system prompt = global_rules + world_digest +
    # capability_contract + character_anchor; user prompt = epoch_summary + turn_frames.
    for name in SECTION_ORDER:
        if name in mandatory_sections_map:
            final_sections.append(mandatory_sections_map[name])
        elif name in optional_sections_map:
            final_sections.append(optional_sections_map[name])

    def _join(sections: list[RenderedSection]) -> tuple[str, str]:
        sys_text = "\n\n".join(
            s.rendered_text for s in sections
            if s.name in {"global_rules", "world_digest", "capability_contract", "character_anchor"}
        )
        user_text = "\n\n".join(
            s.rendered_text for s in sections if s.name in {"epoch_summary", "turn_frames"}
        )
        return sys_text, user_text

    # Authoritative aggregate bound on the EXACT joined messages that will be sent
    # (per-section estimates floor independently, so their sum can understate the
    # joined representation): least-stable optional sections drop deterministically
    # until the sent representation fits. Mandatory-only overflow rejects rather than
    # silently removing mandatory content.
    system_prompt, user_prompt = _join(final_sections)
    total_rendered_tokens = estimate_tokens(system_prompt) + estimate_tokens(user_prompt)
    while total_rendered_tokens > max_input_budget:
        droppable = [s for s in final_sections if not s.mandatory]
        if not droppable:
            log_warn(
                "narrative_context_budget_exceeded",
                context={
                    "capability": capability,
                    "mandatory_tokens": total_rendered_tokens,
                    "bound": max_input_budget,
                    "mandatory": True,
                },
            )
            raise ContextBudgetExceededError(
                f"Mandatory joined prompt ({total_rendered_tokens} tokens) exceeds "
                f"max input budget ({max_input_budget})"
            )
        victim = droppable[-1]
        final_sections.remove(victim)
        truncation_decisions.append(f"omitted_entire_section:{victim.name}")
        system_prompt, user_prompt = _join(final_sections)
        total_rendered_tokens = estimate_tokens(system_prompt) + estimate_tokens(user_prompt)

    section_accounting: dict[str, int] = {s.name: s.token_count for s in final_sections}

    budget_accounting: dict[str, Any] = {
        "context_window": budget_profile.context_window,
        "completion_reservation": budget_profile.completion_reservation,
        "deep_recall_reservation": budget_profile.deep_recall_reservation,
        "safety_margin": budget_profile.safety_margin,
        "max_input_budget": max_input_budget,
        "total_rendered_tokens": total_rendered_tokens,
        "section_tokens": section_accounting,
        "estimator_version": ESTIMATOR_VERSION,
    }

    assembled = AssembledContext(
        capability=capability,
        prompt_version=prompt_version,
        schema_version=schema_version,
        rendering_version=rendering_version,
        owner_id=clean_owner,
        owner_generation=owner_gen,
        sections=tuple(final_sections),
        sources=tuple(sources_provenance),
        budget_accounting=_deep_freeze(budget_accounting),
        truncation_decisions=tuple(truncation_decisions),
        system_prompt=system_prompt,
        user_prompt=user_prompt,
        thread_id=explicit_thread,
        thread_revision=thread_revisions.get(explicit_thread, 0),
        thread_revisions=_deep_freeze(thread_revisions),
    )

    # Observability log: normal log contains only IDs and counts, no private prompt text
    log_info(
        "narrative_context_assembled",
        context={
            "capability": capability,
            "owner_id": clean_owner,
            "generation": owner_gen,
            "sections_count": len(final_sections),
            "sources_count": len(sources_provenance),
            "rejected_sources": rejected_source_count,
            "rendered_tokens": total_rendered_tokens,
            "truncations": len(truncation_decisions),
            "trace_id": trace_id,
            "thread_id": explicit_thread,
            "thread_revision": thread_revisions.get(explicit_thread, 0),
            "threads_count": len(thread_revisions),
        },
    )

    return assembled


def persist_context_snapshot(
    context: AssembledContext,
    *,
    snapshot_id: str | None = None,
) -> NarrativeContextSnapshot:
    """Persist an assembled context as an immutable NarrativeContextSnapshot.

    The reconstructible rendered payload is ALWAYS retained (design decision 3):
    retries and offline reconstruction must not depend on debug retention. Prompt
    text stays inside the narrative database (controlled storage) and never enters
    normal operational logs, which carry IDs and counts only.
    """
    snap_id = snapshot_id or f"snap_{uuid.uuid4().hex}"

    sources_data = [
        {
            "source_id": s.source_id,
            "record_id": s.record_id,
            "revision_number": s.revision_number,
            "knowledge_scope": s.knowledge_scope,
            "owner_id": s.owner_id,
            "sha256": s.sha256,
            "thread_revision": s.thread_revision,
        }
        for s in context.sources
    ]

    rendered_payload_data = {
        "system_prompt": context.system_prompt,
        "user_prompt": context.user_prompt,
        "sections": [
            {
                "name": s.name,
                "heading": s.heading,
                "content": s.content,
                "rendered_text": s.rendered_text,
                "token_count": s.token_count,
                "sha256": s.sha256,
            }
            for s in context.sections
        ],
    }

    snapshot = NarrativeContextSnapshot.objects.create(
        snapshot_id=snap_id,
        capability=context.capability,
        prompt_version=context.prompt_version,
        schema_version=context.schema_version,
        rendering_version=context.rendering_version,
        owner_id=context.owner_id,
        owner_generation=context.owner_generation,
        sources=sources_data,
        thread_revisions=_plain(context.thread_revisions),
        section_hashes=context.get_section_hashes(),
        budget_accounting=_plain(context.budget_accounting),
        truncation_decisions=list(context.truncation_decisions),
        rendered_payload=rendered_payload_data,
    )

    log_info(
        "narrative_snapshot_persisted",
        context={
            "snapshot_id": snap_id,
            "capability": context.capability,
            "owner_id": context.owner_id,
            "generation": context.owner_generation,
            "sources_count": len(sources_data),
            "threads_count": len(context.thread_revisions),
        },
    )

    return snapshot


def get_context_snapshot(snapshot_id: str) -> NarrativeContextSnapshot:
    """Retrieve an immutable NarrativeContextSnapshot by ID."""
    try:
        return NarrativeContextSnapshot.objects.get(snapshot_id=snapshot_id)
    except NarrativeContextSnapshot.DoesNotExist as exc:
        raise SnapshotNotFoundError(f"Context snapshot {snapshot_id!r} not found") from exc


def _check_descriptor_provenance(
    snapshot: NarrativeContextSnapshot,
    *,
    capability: str,
    owner_id: str,
    owner_generation: int,
    prompt_version: str,
    schema_version: str,
    rendering_version: str,
    thread_revisions: Mapping[str, int],
) -> None:
    """Reject descriptor construction that mixes inputs with unrelated snapshot provenance."""
    actual = (
        snapshot.capability,
        snapshot.owner_id,
        snapshot.owner_generation,
        snapshot.prompt_version,
        snapshot.schema_version,
        snapshot.rendering_version,
        dict(snapshot.thread_revisions or {}),
    )
    expected = (
        capability,
        owner_id,
        owner_generation,
        prompt_version,
        schema_version,
        rendering_version,
        _plain(thread_revisions),
    )
    if actual != expected:
        raise ContextProvenanceError(
            f"Snapshot {snapshot.snapshot_id!r} provenance {actual} does not match "
            f"assembled context provenance {expected}"
        )


def _snapshot_messages(snapshot: NarrativeContextSnapshot) -> tuple[dict[str, str], ...]:
    """Reconstruct the exact captured messages from the authoritative persisted payload."""
    payload = snapshot.rendered_payload or {}
    if "system_prompt" not in payload or "user_prompt" not in payload:
        raise ContextProvenanceError(
            f"Snapshot {snapshot.snapshot_id!r} lacks its reconstructible rendered payload; "
            "hashes alone cannot stand in for captured content"
        )
    return (
        {"role": "system", "content": payload["system_prompt"]},
        {"role": "user", "content": payload["user_prompt"]},
    )


def build_request_descriptor(
    context: AssembledContext,
    snapshot: NarrativeContextSnapshot,
    *,
    trace_id: str | None = None,
    output_schema: Mapping[str, Any] | None = None,
    schema_id: str | None = None,
    semantic_validators: Mapping[str, Callable[[Any], list[str]]] | None = None,
) -> NarrativeRequestDescriptor:
    """Create a thin request descriptor binding messages, validators, and snapshot provenance.

    The authoritative persisted row is re-read and BOTH its provenance metadata and
    its captured messages must agree with the supplied context, so a caller cannot
    pair a context with a same-metadata-but-different-content snapshot and obtain
    descriptors whose first request and retries disagree.
    """
    authoritative = get_context_snapshot(snapshot.snapshot_id)
    _check_descriptor_provenance(
        authoritative,
        capability=context.capability,
        owner_id=context.owner_id,
        owner_generation=context.owner_generation,
        prompt_version=context.prompt_version,
        schema_version=context.schema_version,
        rendering_version=context.rendering_version,
        thread_revisions=context.thread_revisions,
    )
    captured = _snapshot_messages(authoritative)
    if tuple(context.to_messages()) != captured:
        raise ContextProvenanceError(
            f"Snapshot {authoritative.snapshot_id!r} captured messages do not match "
            "the supplied assembled context"
        )
    actual_trace_id = trace_id or f"trace_{uuid.uuid4().hex}"

    chat_desc = ChatRequestDescriptor(
        messages=context.to_messages(),
        output_schema=output_schema,
        schema_id=schema_id,
        semantic_validators=semantic_validators,
    )

    return NarrativeRequestDescriptor(
        chat_descriptor=chat_desc,
        capability=authoritative.capability,
        prompt_version=authoritative.prompt_version,
        schema_version=authoritative.schema_version,
        rendering_version=authoritative.rendering_version,
        snapshot_id=authoritative.snapshot_id,
        trace_id=actual_trace_id,
        owner_id=context.owner_id,
        owner_generation=context.owner_generation,
    )


def reuse_snapshot_for_retry(
    snapshot: NarrativeContextSnapshot,
    *,
    attempt: int,
    trace_id: str,
    output_schema: Mapping[str, Any] | None = None,
    schema_id: str | None = None,
    semantic_validators: Mapping[str, Callable[[Any], list[str]]] | None = None,
    validation_error_message: Mapping[str, str] | None = None,
) -> NarrativeRequestDescriptor:
    """Reuse an immutable captured snapshot for a retry attempt.

    Invariant:
    - The authoritative persisted row is re-read; a caller-mutated in-memory
      instance cannot substitute content for what history recorded.
    - Retries reuse the captured payload and provenance; they do NOT re-query
      owner memories or re-evaluate the current generation.
    - Retry feedback is accounted against the captured input budget on the rendered
      representation; feedback that cannot fit rejects before generation rather than
      silently overrunning the hard input bound.
    """
    authoritative = get_context_snapshot(snapshot.snapshot_id)

    log_info(
        "narrative_snapshot_reused",
        context={
            "snapshot_id": authoritative.snapshot_id,
            "capability": authoritative.capability,
            "owner_id": authoritative.owner_id,
            "generation": authoritative.owner_generation,
            "attempt": attempt,
            "trace_id": trace_id,
        },
    )

    messages: list[dict[str, str]] = list(_snapshot_messages(authoritative))

    if validation_error_message is not None:
        role = validation_error_message.get("role")
        content = validation_error_message.get("content")
        if not isinstance(role, str) or not isinstance(content, str):
            raise ContextProvenanceError(
                "validation_error_message must carry string role and content"
            )
        accounting = authoritative.budget_accounting or {}
        max_input = accounting.get("max_input_budget")
        base_tokens = sum(estimate_tokens(m["content"]) for m in messages)
        feedback_tokens = estimate_tokens(content)
        if max_input is not None and base_tokens + feedback_tokens > max_input:
            log_warn(
                "narrative_context_budget_exceeded",
                context={
                    "capability": authoritative.capability,
                    "snapshot_id": authoritative.snapshot_id,
                    "attempt": attempt,
                    "mandatory_tokens": base_tokens + feedback_tokens,
                    "bound": max_input,
                    "mandatory": True,
                },
            )
            raise ContextBudgetExceededError(
                f"Retry feedback ({feedback_tokens} tokens) plus captured context "
                f"({base_tokens} tokens) exceeds captured input budget ({max_input})"
            )
        messages.append({"role": role, "content": content})

    chat_desc = ChatRequestDescriptor(
        messages=tuple(messages),
        output_schema=output_schema,
        schema_id=schema_id,
        semantic_validators=semantic_validators,
    )

    return NarrativeRequestDescriptor(
        chat_descriptor=chat_desc,
        capability=authoritative.capability,
        prompt_version=authoritative.prompt_version,
        schema_version=authoritative.schema_version,
        rendering_version=authoritative.rendering_version,
        snapshot_id=authoritative.snapshot_id,
        trace_id=trace_id,
        owner_id=authoritative.owner_id,
        owner_generation=authoritative.owner_generation,
    )
