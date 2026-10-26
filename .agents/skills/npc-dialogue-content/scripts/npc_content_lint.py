#!/usr/bin/env python3
"""Authoring lint for authored NPC dialogue YAML.

Focuses on what the dialogue loader cannot see: out-of-character tokens,
中式武俠 vocabulary, zh-TW punctuation and spacing, fake or mistyped condition
operands, and obvious declaration slips. The real loader stays authoritative for
schema, references and budgets; a clean run here is editorial evidence, not proof
that the snapshot loads.

Usage::

    uv run --locked python <checkout>/.agents/skills/npc-dialogue-content/scripts/npc_content_lint.py \
        world/lore/dialogue/content/altoria_merchant.yaml
    ... scripts/npc_content_lint.py <content-dir> --json
    ... scripts/npc_content_lint.py <file> --places     # heuristic place check
    ... scripts/npc_content_lint.py <file> --no-registry

The repository used for registry and place lookups is the checkout that contains
the target file (first ancestor with ``world/lore/dialogue/__init__.py``), so
running the primary checkout's script against a feature worktree's content still
reads that worktree's registries. ``--repo`` overrides it.

Exit status is ``1`` when any ERROR is reported, ``0`` otherwise. WARN findings
fail the run only under ``--strict``.
"""

from __future__ import annotations

import argparse
import datetime
import json
import re
import sys
from dataclasses import dataclass, asdict
from pathlib import Path

try:
    import yaml
except ModuleNotFoundError:  # pragma: no cover - environment error
    sys.exit("pyyaml is required: run through `uv run --locked python`")

SCRIPT_CHECKOUT = Path(__file__).resolve().parents[4]

# --- vocabulary -------------------------------------------------------------

OOC_TOKENS = (
    "指令",
    "系統",
    "選單",
    "按鈕",
    "快捷鍵",
    "介面",
    "熟練度",
    "整點結算",
)
WUXIA_TOKENS = (
    "過招",
    "劍招",
    "招式",
    "祕技",
    "拜師",
    "功夫",
    "江湖",
    "客官",
    "掌門",
    "內力",
    "輕功",
    "俠客",
)
CALQUE_TOKENS = ("折入", "賦能", "拉齊")
# Legitimate in literal senses (earthworks, diving, tidying); review by eye.
CONTEXT_TOKENS = ("回填", "深潛", "重新整理", "落地")

ASCII_COMMANDS = (
    "rest",
    "buy",
    "look",
    "score",
    "inventory",
    "who",
    "say",
    "tell",
    "shop stock",
    "guild list",
    "quest list",
)
ASCII_COMMAND_RE = re.compile(
    r"(?<![A-Za-z])(" + "|".join(re.escape(c) for c in ASCII_COMMANDS) + r")(?![A-Za-z])",
    re.IGNORECASE,
)

CJK = r"\u4e00-\u9fff"
SENTENCE_FINAL_DE_RE = re.compile(r"的[，。]")
CJK_LATIN_RE = re.compile(rf"[{CJK}][A-Za-z0-9]|[A-Za-z0-9][{CJK}]")
HALFWIDTH_PUNCT_RE = re.compile(rf"[{CJK}][,.;:!?]|[,.;:!?][{CJK}]")
MID_COLON_RE = re.compile(rf"[{CJK}][^，。！？：]*：(?![「『])")
REDUPLICATION_RE = re.compile(rf"([{CJK}])\1")
# Ordinary AA verb forms and the 分會會長 compound; 疊字 such as 慢慢 stay flagged.
REDUPLICATION_OK = {"謝", "會", "談", "說"}
BRACKETS = {"「": "」", "『": "』", "（": "）", "《": "》"}

PLACE_SUFFIXES = (
    "巷",
    "大道",
    "廣場",
    "神殿",
    "聖所",
    "旅店",
    "酒館",
    "谷地",
    "丘陵",
    "港灣",
)
PLACE_SUFFIX_RE = re.compile("|".join(PLACE_SUFFIXES))
CJK_RUN_RE = re.compile(rf"[{CJK}]{{2,}}")
# Leading function words that glue a verb phrase to the noun it governs.
FUNCTION_PREFIX = set(
    "在到由和與從沿順往向出進過這那每各是的走轉拐穿抵達通靠朝對把將就便再又還也"
    "我們你他她它們只途經指了朝向安靜沒回條著至跟叫讓給替幫寸步路邊前後左右中裡外上下"
)
GENERIC_PLACES = set(PLACE_SUFFIXES) | {"小巷", "街巷", "石板路", "大路上", "路上", "巷道"}

GUILD_RANKS = ("F", "E", "D", "C", "B", "A")


class DuplicateKeyError(yaml.YAMLError):
    pass


class StrictLoader(yaml.SafeLoader):
    """SafeLoader that refuses duplicate mapping keys and non-JSON scalars."""


def _construct_mapping(loader: "StrictLoader", node: yaml.MappingNode, deep: bool = False):
    seen = set()
    for key_node, _ in node.value:
        key = loader.construct_object(key_node, deep=deep)
        if isinstance(key, (dict, list)):
            raise yaml.constructor.ConstructorError(
                None, None, "mapping keys must be scalars", key_node.start_mark
            )
        if key in seen:
            raise DuplicateKeyError(f"duplicate mapping key {key!r}")
        seen.add(key)
    return yaml.SafeLoader.construct_mapping(loader, node, deep=deep)


def _construct_non_json(loader: "StrictLoader", node: yaml.ScalarNode):
    raise yaml.constructor.ConstructorError(
        None, None, "non-JSON scalar (date/time/binary) is not allowed", node.start_mark
    )


StrictLoader.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, _construct_mapping)
for tag in (
    "tag:yaml.org,2002:timestamp",
    "tag:yaml.org,2002:binary",
    "tag:yaml.org,2002:set",
    "tag:yaml.org,2002:omap",
):
    StrictLoader.add_constructor(tag, _construct_non_json)


@dataclass(frozen=True)
class Finding:
    path: str
    topic: str
    where: str
    severity: str
    rule: str
    detail: str

    def render(self) -> str:
        return f"{self.path}  {self.topic}/{self.where}  {self.severity} [{self.rule}] {self.detail}"


class Lint:
    def __init__(self, path: Path, repo: Path, check_places: bool = False) -> None:
        self.path = path
        self.repo = repo
        self.check_places = check_places
        self.findings: list[Finding] = []
        self._palette: dict[str, object] | None = None
        self._corpus: str | None = None
        self._registry_failed = False

    # -- reporting ---------------------------------------------------------

    def error(self, topic: str, where: str, rule: str, detail: str) -> None:
        self._add("ERROR", topic, where, rule, detail)

    def warn(self, topic: str, where: str, rule: str, detail: str) -> None:
        self._add("WARN", topic, where, rule, detail)

    def _add(self, severity: str, topic: str, where: str, rule: str, detail: str) -> None:
        try:
            rel = self.path.resolve().relative_to(self.repo)
        except (ValueError, OSError):
            rel = self.path
        self.findings.append(Finding(str(rel), topic, where, severity, rule, detail))

    # -- entry point -------------------------------------------------------

    def run(self, use_registry: bool) -> None:
        try:
            raw = self.path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError) as exc:
            self.error("<root>", "file", "file-read", f"{type(exc).__name__}: {exc}")
            return
        try:
            document = yaml.load(raw, Loader=StrictLoader)  # noqa: S506 - strict subclass
        except yaml.YAMLError as exc:
            self.error("<root>", "yaml", "yaml-parse", str(exc).splitlines()[0])
            return

        if not isinstance(document, dict):
            self.error("<root>", "yaml", "root-type", "root must be a mapping")
            return

        if use_registry and not self._load_registries():
            self.error(
                "<root>",
                "registry",
                "registry-unavailable",
                f"registry lookup failed under {self.repo}; rerun with --repo or --no-registry",
            )

        self._check_root(document)
        topics = document.get("topics")
        if not isinstance(topics, list):
            self.error("<root>", "topics", "root-type", "topics must be a list")
            return

        topic_ids: set[str] = set()
        scene_ids: dict[str, str] = {}
        precedent: dict[str, list[str]] = {}
        for index, topic in enumerate(topics):
            if not isinstance(topic, dict):
                self.error(f"topic[{index}]", "topic", "topic-type", "topic must be a mapping")
                continue
            self._check_topic(topic, index, topic_ids, scene_ids, precedent, use_registry)
        self._check_predecessors(precedent, topic_ids)

        greeting = document.get("greeting")
        if isinstance(greeting, str):
            self._check_text(greeting, "greeting", "greeting")

    def _check_root(self, document: dict) -> None:
        allowed = {"schema_version", "greeting", "topics"}
        extra = sorted(str(key) for key in set(document) - allowed)
        if extra:
            self.error("<root>", "keys", "root-keys", f"unexpected root keys: {', '.join(extra)}")
        version = document.get("schema_version")
        if not isinstance(version, int) or isinstance(version, bool) or version != 1:
            self.error("<root>", "schema_version", "schema", "schema_version must be the integer 1")
        greeting = document.get("greeting")
        if greeting is not None and not isinstance(greeting, str):
            self.error("<root>", "greeting", "greeting-type", "greeting must be a string or null")

    def _check_topic(
        self,
        topic: dict,
        index: int,
        topic_ids: set[str],
        scene_ids: dict[str, str],
        precedent: dict[str, list[str]],
        use_registry: bool,
    ) -> None:
        topic_id = topic.get("topic_id")
        label = topic_id if isinstance(topic_id, str) and topic_id else f"topic[{index}]"
        if not isinstance(topic_id, str) or not topic_id:
            self.error(label, "topic_id", "topic-id", "topic_id is required")
        elif topic_id in topic_ids:
            self.error(label, "topic_id", "topic-id", "duplicate topic_id")
        else:
            topic_ids.add(topic_id)
            ancestors = topic.get("predecessors")
            if isinstance(ancestors, list) and all(isinstance(item, str) for item in ancestors):
                precedent[topic_id] = ancestors

        for key in ("keyword", "label"):
            value = topic.get(key)
            if not isinstance(value, str) or not value:
                self.error(label, key, "topic-field", f"{key} is required")
            elif len(value) > 32:
                self.error(label, key, "topic-field", f"{key} exceeds 32 code points")
            else:
                self._check_text(value, label, key, plain=True)

        scenes: list[tuple[str, dict]] = []
        fallback = topic.get("fallback")
        if isinstance(fallback, dict):
            scenes.append(("fallback", fallback))
        else:
            self.error(label, "fallback", "scene", "fallback scene is required")

        variants = topic.get("variants") or []
        if not isinstance(variants, list):
            self.error(label, "variants", "variants", "variants must be a list")
            variants = []
        priorities: set[int] = set()
        for position, variant in enumerate(variants):
            where = f"variant[{position}]"
            if not isinstance(variant, dict):
                self.error(label, where, "variants", "variant must be a mapping")
                continue
            variant_id = variant.get("variant_id")
            priority = variant.get("priority")
            if not isinstance(priority, int) or isinstance(priority, bool):
                self.error(label, where, "variants", "priority must be an integer")
            elif priority in priorities:
                self.error(label, where, "variants", f"duplicate priority {priority}")
            else:
                priorities.add(priority)
            if not isinstance(variant_id, str) or not variant_id:
                self.error(label, where, "variants", "variant_id is required")
            scene = variant.get("scene")
            if isinstance(scene, dict):
                scenes.append((where, scene))
            else:
                self.error(label, where, "scene", "variant scene is required")
            when = variant.get("when")
            if not isinstance(when, dict):
                self.error(label, where, "variants", "when is required")
            else:
                self._check_condition(when, label, where, depth=1, use_registry=use_registry)

        requires = topic.get("requires")
        if requires is not None:
            if not isinstance(requires, dict):
                self.error(label, "requires", "requires", "requires must be a condition mapping")
            else:
                self._check_condition(requires, label, "requires", depth=1, use_registry=use_registry)

        unavailable = topic.get("unavailable")
        if unavailable not in (None, "hidden", "locked"):
            self.error(label, "unavailable", "disclosure", "unavailable must be hidden or locked")
        if unavailable == "locked":
            if requires is None:
                self.error(label, "requires", "disclosure", "a locked topic must declare requires")
            if not isinstance(topic.get("refusal"), dict):
                self.error(label, "refusal", "disclosure", "a locked topic must declare a refusal scene")

        disclosure = topic.get("disclosure")
        if disclosure not in (None, "qualified", "pure_chain"):
            self.error(label, "disclosure", "disclosure", "disclosure must be qualified or pure_chain")
        if disclosure == "pure_chain":
            if requires is not None:
                self.error(label, "disclosure", "pure-chain", "a pure_chain topic must not declare requires")
            if not topic.get("predecessors"):
                self.error(label, "disclosure", "pure-chain", "a pure_chain topic needs a predecessor")

        refusal = topic.get("refusal")
        if isinstance(refusal, dict):
            scenes.append(("refusal", refusal))

        for where, scene in scenes:
            self._check_scene(scene, label, where, scene_ids, require_actor_first=(where != "refusal"))

    def _check_predecessors(self, precedent: dict[str, list[str]], topic_ids: set[str]) -> None:
        for topic_id, ancestors in precedent.items():
            for ancestor in ancestors:
                if ancestor == topic_id:
                    self.error(topic_id, "predecessors", "cycle", "a topic cannot precede itself")
                elif ancestor not in topic_ids:
                    self.error(
                        topic_id,
                        "predecessors",
                        "unknown-predecessor",
                        f"{ancestor!r} is not a topic in this file",
                    )
        # Depth-first cycle detection over the declared graph.
        state: dict[str, int] = {}

        def visit(node: str) -> None:
            if state.get(node) == 2:
                return
            if state.get(node) == 1:
                self.error(node, "predecessors", "cycle", "predecessor chain is cyclic")
                return
            state[node] = 1
            for ancestor in precedent.get(node, []):
                if ancestor in precedent:
                    visit(ancestor)
            state[node] = 2

        for node in precedent:
            visit(node)

    def _check_scene(
        self,
        scene: dict,
        topic_label: str,
        where: str,
        scene_ids: dict[str, str],
        require_actor_first: bool,
    ) -> None:
        scene_id = scene.get("scene_id")
        if not isinstance(scene_id, str) or not scene_id:
            self.error(topic_label, where, "scene", "scene_id is required")
        elif scene_id in scene_ids:
            self.error(topic_label, where, "scene", f"duplicate scene_id (also in {scene_ids[scene_id]})")
        else:
            scene_ids[scene_id] = where
        revision = scene.get("revision")
        if not isinstance(revision, str) or not revision:
            self.error(topic_label, where, "scene", "revision is required")

        lines = scene.get("lines")
        if not isinstance(lines, list) or not lines:
            self.error(topic_label, where, "scene", "lines must be a non-empty list")
            return
        if len(lines) > 32:
            self.error(topic_label, where, "scene", "more than 32 lines")
        if require_actor_first:
            first = lines[0]
            if not (
                isinstance(first, dict)
                and first.get("kind") == "speech"
                and first.get("speaker") == "actor"
            ):
                self.error(topic_label, where, "actor-first", "formal scenes must start with an actor speech line")
        if where != "refusal" and not 3 <= len(lines) <= 8:
            self.warn(topic_label, where, "length", f"{len(lines)} lines (aim for 3..8 meaningful beats)")

        speakers: set[str] = set()
        for index, line in enumerate(lines):
            spot = f"line[{index}]"
            if not isinstance(line, dict):
                self.error(topic_label, where, "line", "line must be a mapping")
                continue
            kind = line.get("kind")
            text = line.get("text")
            if kind not in ("speech", "narration"):
                self.error(topic_label, where, "line", f"unknown kind {kind!r}")
            if kind == "speech":
                speaker = line.get("speaker")
                if speaker not in ("actor", "host"):
                    self.error(topic_label, where, "line", f"unknown speaker {speaker!r}")
                else:
                    speakers.add(speaker)
            elif "speaker" in line:
                self.warn(topic_label, where, "line", "narration carries a speaker field")
            if not isinstance(text, str) or not text.strip():
                self.error(topic_label, where, "line", "text is required")
                continue
            if len(text) > 2000:
                self.error(topic_label, where, "line", f"{len(text)} code points exceeds 2000")
            self._check_text(text, topic_label, f"{where} {spot}")
        if "host" not in speakers and where != "refusal":
            self.warn(topic_label, where, "length", "no host response in this scene")

    # -- registries --------------------------------------------------------

    def _load_registries(self) -> bool:
        """Import the lore registries the checks need, once per instance.

        Importing ``world.lore.dialogue`` is deliberately avoided: its package
        ``__init__`` loads the whole shipped snapshot, so one broken neighbour
        would make registry validation fail for an otherwise valid file.
        """
        if self._palette is not None:
            return True
        if self._registry_failed:
            return False
        if str(self.repo) not in sys.path:
            sys.path.insert(0, str(self.repo))
        try:
            from world.lore.player_presets import PLAYER_PRESET_REGISTRY
            from world.lore.races import RACE_REGISTRY
            from world.lore.sexual_vocab import EXPOSURE_LEVELS
            from world.lore.social_identities import SOCIAL_IDENTITY_REGISTRY
            from world.skills import SKILL_REGISTRY
        except Exception:  # noqa: BLE001 - reported as one ERROR by run()
            self._registry_failed = True
            return False
        self._palette = {
            "races": frozenset(RACE_REGISTRY),
            "identities": frozenset(SOCIAL_IDENTITY_REGISTRY),
            "skills": frozenset(SKILL_REGISTRY),
            "presets": frozenset(PLAYER_PRESET_REGISTRY),
            "exposure": EXPOSURE_LEVELS,
        }
        return True

    def _check_condition(
        self, condition: dict, topic: str, where: str, depth: int, use_registry: bool
    ) -> None:
        if depth > 4:
            self.error(topic, where, "condition", "condition nesting deeper than 4")
            return
        kind = condition.get("kind")
        if not isinstance(kind, str):
            self.error(topic, where, "condition", "condition kind is required")
            return
        if kind in ("all", "any"):
            children = condition.get("children")
            if not isinstance(children, list) or not children:
                self.error(topic, where, "condition", f"{kind} needs children")
                return
            for child in children:
                if isinstance(child, dict):
                    self._check_condition(child, topic, where, depth + 1, use_registry)
                else:
                    self.error(topic, where, "condition", "child must be a mapping")
            return

        palette = self._palette
        if kind == "race_is":
            key = condition.get("race_key")
            if palette is None:
                return
            if not isinstance(key, str) or key not in palette["races"]:
                self.error(topic, where, "condition", f"unknown race_key {key!r}")
        elif kind == "social_identity_is":
            key = condition.get("identity_key")
            if palette is None:
                return
            if not isinstance(key, str) or key not in palette["identities"]:
                self.error(topic, where, "condition", f"unknown identity_key {key!r}")
        elif kind == "guild_rank_at_least":
            key = condition.get("rank_key")
            if not isinstance(key, str) or key not in GUILD_RANKS:
                self.error(topic, where, "condition", f"unknown guild rank_key {key!r} (F..A)")
        elif kind == "skill_owned":
            key = condition.get("skill_key")
            if palette is None:
                return
            if not isinstance(key, str) or key not in palette["skills"]:
                self.error(topic, where, "condition", f"unknown skill_key {key!r}")
            threshold = condition.get("min_proficiency")
            if threshold is not None and (
                not isinstance(threshold, int) or isinstance(threshold, bool) or threshold < 0
            ):
                self.error(topic, where, "condition", "min_proficiency must be a non-negative integer")
        elif kind == "exposure":
            levels = palette["exposure"] if palette else ("",) * 5
            lower = condition.get("minimum")
            upper = condition.get("maximum")
            if lower is None and upper is None:
                self.error(topic, where, "condition", "exposure needs minimum or maximum")
                return
            for name, bound in (("minimum", lower), ("maximum", upper)):
                if bound is None:
                    continue
                if (
                    not isinstance(bound, int)
                    or isinstance(bound, bool)
                    or not 0 <= bound < len(levels)
                ):
                    self.error(topic, where, "condition", f"exposure {name} {bound!r} outside 0..4")
                    return
            if isinstance(lower, int) and isinstance(upper, int) and lower > upper:
                self.error(topic, where, "condition", "exposure minimum exceeds maximum")
        elif kind == "companion_present":
            source_kind = condition.get("source_kind")
            source_key = condition.get("source_key")
            if source_kind not in ("preset", "profile", "package_role"):
                self.error(topic, where, "condition", f"unknown companion source_kind {source_kind!r}")
            elif source_kind == "preset" and palette is not None:
                if not isinstance(source_key, str) or source_key not in palette["presets"]:
                    self.error(topic, where, "condition", f"unknown companion preset {source_key!r}")
        elif kind in ("quest_is", "affinity_at_least", "time_period", "carries"):
            return  # the loader validates these against its reference catalog
        else:
            self.error(topic, where, "condition", f"unknown condition kind {kind!r}")

    # -- prose --------------------------------------------------------------

    def _check_text(self, text: str, topic: str, where: str, plain: bool = False) -> None:
        if "`" in text:
            self.error(topic, where, "backtick", "text contains a backtick")
        for token in OOC_TOKENS:
            if token in text:
                self.error(topic, where, "ooc-token", f"game mechanic token 「{token}」")
        for token in WUXIA_TOKENS:
            if token in text:
                self.error(topic, where, "wuxia", f"中式武俠 vocabulary 「{token}」")
        for token in CALQUE_TOKENS:
            if token in text:
                self.error(topic, where, "calque", f"English calque 「{token}」")
        for token in CONTEXT_TOKENS:
            if token in text:
                self.warn(topic, where, "calque", f"「{token}」 is fine literally; confirm it is not a calque here")
        match = ASCII_COMMAND_RE.search(text)
        if match:
            self.error(topic, where, "ascii-command", f"command token {match.group(0)!r}")
        if "您" in text:
            self.error(topic, where, "pronoun", "uses 您; write 你")
        if SENTENCE_FINAL_DE_RE.search(text):
            self.error(topic, where, "de-tail", "sentence-final 的 before ，or 。")
        if CJK_LATIN_RE.search(text):
            self.error(topic, where, "spacing", "CJK adjacent to a Latin letter or digit without a space")
        if HALFWIDTH_PUNCT_RE.search(text):
            self.error(topic, where, "punctuation", "half-width punctuation beside Chinese")
        if MID_COLON_RE.search(text):
            self.warn(topic, where, "colon", "mid-sentence colon")
        for char in REDUPLICATION_RE.findall(text):
            if char not in REDUPLICATION_OK:
                self.warn(topic, where, "reduplication", f"reduplicated 「{char}{char}」")
                break
        if not self._brackets_balanced(text):
            self.error(topic, where, "brackets", "unbalanced or crossed 「」『』（）《》")
        if not plain and self.check_places:
            self._check_places(text, topic, where)

    @staticmethod
    def _brackets_balanced(text: str) -> bool:
        closers = {close: open_ for open_, close in BRACKETS.items()}
        stack: list[str] = []
        for char in text:
            if char in BRACKETS:
                stack.append(char)
            elif char in closers:
                if not stack or stack.pop() != closers[char]:
                    return False
        return not stack

    def _check_places(self, text: str, topic: str, where: str) -> None:
        corpus = self._place_corpus()
        if corpus is None:
            return
        seen: set[str] = set()
        for run in CJK_RUN_RE.finditer(text):
            chunk = run.group(0)
            for suffix in PLACE_SUFFIX_RE.finditer(chunk):
                end = suffix.end()
                known = any(
                    chunk[max(0, end - width) : end] in corpus
                    for width in range(3, min(8, end) + 1)
                )
                if known:
                    continue
                token = chunk[max(0, end - 8) : end]
                while len(token) > 1 and token[0] in FUNCTION_PREFIX:
                    token = token[1:]
                if token in GENERIC_PLACES or len(token) < 3:
                    continue
                if token in seen:
                    continue
                seen.add(token)
                self.warn(
                    topic,
                    where,
                    "place-name",
                    f"「{token}」 is not in the place corpus; confirm it exists in places*.py",
                )

    def _place_corpus(self) -> str | None:
        if self._corpus is not None:
            return self._corpus
        sources = sorted(self.repo.glob("world/lore/settlements/places*.py"))
        doc = self.repo / "docs/lore/settlement-locations.md"
        if not sources and not doc.is_file():
            return None
        chunks: list[str] = []
        for path in [*sources, doc]:
            if path.is_file():
                chunks.append(path.read_text(encoding="utf-8", errors="ignore"))
        self._corpus = "\x00".join(re.findall(rf"[{CJK}]{{3,}}", "\n".join(chunks)))
        return self._corpus


def resolve_repo(target: Path, override: str | None) -> Path:
    if override:
        return Path(override).resolve()
    for candidate in [target.resolve(), *target.resolve().parents]:
        if (candidate / "world/lore/dialogue/__init__.py").is_file():
            return candidate
        if candidate == candidate.parent:
            break
    return SCRIPT_CHECKOUT


def expand_paths(targets: list[str]) -> list[Path]:
    paths: list[Path] = []
    for target in targets:
        path = Path(target)
        if path.is_dir():
            paths.extend(sorted(path.glob("*.yaml")))
        else:
            paths.append(path)
    return paths


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("targets", nargs="+", help="YAML file or directory of YAML files")
    parser.add_argument("--json", action="store_true", help="machine-readable output")
    parser.add_argument("--no-registry", action="store_true", help="skip project registry imports")
    parser.add_argument(
        "--places",
        action="store_true",
        help="heuristic place-name check against places*.py and settlement-locations.md",
    )
    parser.add_argument("--strict", action="store_true", help="treat WARN findings as failures")
    parser.add_argument(
        "--repo",
        help="checkout used for registry and place lookups (default: the target's checkout)",
    )
    args = parser.parse_args(argv)

    findings: list[Finding] = []
    checked: list[str] = []
    for path in expand_paths(args.targets):
        repo = resolve_repo(path, args.repo)
        checked.append(str(path))
        lint = Lint(path, repo, check_places=args.places)
        lint.run(use_registry=not args.no_registry)
        findings.extend(lint.findings)

    if args.json:
        json.dump([asdict(f) for f in findings], sys.stdout, ensure_ascii=False, indent=2)
        sys.stdout.write("\n")
    else:
        for finding in findings:
            print(finding.render())
        errors = sum(1 for f in findings if f.severity == "ERROR")
        warns = sum(1 for f in findings if f.severity == "WARN")
        print(f"npc content lint: {len(checked)} file(s), {errors} error(s), {warns} warning(s)")

    errors = any(f.severity == "ERROR" for f in findings)
    warns = any(f.severity == "WARN" for f in findings)
    return 1 if errors or (args.strict and warns) else 0


if __name__ == "__main__":
    raise SystemExit(main())
