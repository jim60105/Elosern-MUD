#!/usr/bin/env python3
"""Authoring lint for authored NPC dialogue YAML.

Checks the prose and declarations of
``world/lore/dialogue/content/<NpcProfile.key>.yaml`` for the defects that the
dialogue loader cannot see: out-of-character tokens, 中式武俠 vocabulary,
zh-TW punctuation and spacing, invented proper nouns, and condition operands
that do not exist in the canonical registries.

Usage::

    uv run --locked python .agents/skills/npc-dialogue-content/scripts/npc_content_lint.py \
        world/lore/dialogue/content/altoria_merchant.yaml
    ... scripts/npc_content_lint.py world/lore/dialogue/content --json
    ... scripts/npc_content_lint.py <file> --no-registry   # skip project imports

Exit status is ``1`` when any ERROR is found, ``0`` otherwise. WARN findings are
review prompts and never fail the run. Load/schema limits belong to the real
loader; this lint only mirrors the cheap structural rules.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass, asdict
from pathlib import Path

try:
    import yaml
except ModuleNotFoundError:  # pragma: no cover - environment error
    sys.exit("pyyaml is required: run through `uv run --locked python`")

REPO_ROOT = Path(__file__).resolve().parents[4]

# --- high-confidence OOC and register violations ---------------------------

OOC_TOKENS = (
    "指令",
    "系統",
    "選單",
    "按鈕",
    "快捷鍵",
    "介面",
    "熟練度",
    "整點結算",
    "重新整理",
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
CALQUE_TOKENS = (
    "折入",
    "回填",
    "賦能",
    "拉齊",
    "深潛",
    "碰基地",
)
SOFT_TOKENS = ("落地",)  # legitimate for a physical landing; review by eye

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
BRACKETS = (("「", "」"), ("『", "』"), ("（", "）"), ("《", "》"))

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
        self._places: str | None = None

    # -- reporting ---------------------------------------------------------

    def error(self, topic: str, where: str, rule: str, detail: str) -> None:
        self._add("ERROR", topic, where, rule, detail)

    def warn(self, topic: str, where: str, rule: str, detail: str) -> None:
        self._add("WARN", topic, where, rule, detail)

    def _add(self, severity: str, topic: str, where: str, rule: str, detail: str) -> None:
        try:
            rel = self.path.resolve().relative_to(REPO_ROOT)
        except ValueError:
            rel = self.path
        self.findings.append(Finding(str(rel), topic, where, severity, rule, detail))

    # -- entry point -------------------------------------------------------

    def run(self, use_registry: bool) -> None:
        try:
            document = yaml.safe_load(self.path.read_text(encoding="utf-8"))
        except yaml.YAMLError as exc:
            self.error("<root>", "yaml", "yaml-parse", str(exc).splitlines()[0])
            return
        if not isinstance(document, dict):
            self.error("<root>", "yaml", "root-type", "root must be a mapping")
            return

        self._check_root(document)
        topics = document.get("topics")
        if not isinstance(topics, list):
            self.error("<root>", "topics", "root-type", "topics must be a list")
            return

        topic_ids: set[str] = set()
        scene_ids: dict[str, str] = {}
        for index, topic in enumerate(topics):
            if not isinstance(topic, dict):
                self.error(f"topic[{index}]", "topic", "topic-type", "topic must be a mapping")
                continue
            self._check_topic(topic, index, topic_ids, scene_ids, use_registry)

        greeting = document.get("greeting")
        if isinstance(greeting, str):
            self._check_text(greeting, "greeting", "greeting")

    def _check_root(self, document: dict) -> None:
        allowed = {"schema_version", "greeting", "topics"}
        extra = sorted(set(document) - allowed)
        if extra:
            self.error("<root>", "keys", "root-keys", f"unexpected root keys: {', '.join(extra)}")
        if document.get("schema_version") != 1 or isinstance(document.get("schema_version"), bool):
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
        use_registry: bool,
    ) -> None:
        topic_id = topic.get("topic_id")
        label = str(topic_id) if isinstance(topic_id, str) else f"topic[{index}]"
        if not isinstance(topic_id, str) or not topic_id:
            self.error(label, "topic_id", "topic-id", "topic_id is required")
        elif topic_id in topic_ids:
            self.error(label, "topic_id", "topic-id", "duplicate topic_id")
        else:
            topic_ids.add(topic_id)

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
            elif use_registry:
                self._check_condition(when, label, where, depth=0)

        requires = topic.get("requires")
        if requires is not None:
            if not isinstance(requires, dict):
                self.error(label, "requires", "requires", "requires must be a condition mapping")
            elif use_registry:
                self._check_condition(requires, label, "requires", depth=0)

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
            predecessors = topic.get("predecessors") or []
            if not predecessors:
                self.error(label, "disclosure", "pure-chain", "a pure_chain topic needs a predecessor")

        refusal = topic.get("refusal")
        if isinstance(refusal, dict):
            scenes.append(("refusal", refusal))

        for where, scene in scenes:
            self._check_scene(scene, label, where, scene_ids, require_actor_first=(where != "refusal"))

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

        speakers = set()
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

    # -- condition operands -------------------------------------------------

    def _check_condition(self, condition: dict, topic: str, where: str, depth: int) -> None:
        if depth > 4:
            self.error(topic, where, "condition", "condition nesting deeper than 4")
            return
        kind = condition.get("kind")
        if kind in ("all", "any"):
            children = condition.get("children")
            if not isinstance(children, list) or not children:
                self.error(topic, where, "condition", f"{kind} needs children")
                return
            for child in children:
                if isinstance(child, dict):
                    self._check_condition(child, topic, where, depth + 1)
                else:
                    self.error(topic, where, "condition", "child must be a mapping")
            return
        try:
            from world.lore.dialogue.conditions import (
                AffinityAtLeast,
                Carries,
                CompanionPresent,
                Exposure,
                GuildRankAtLeast,
                QuestIs,
                RaceIs,
                SkillOwned,
                SocialIdentityIs,
                TimePeriod,
            )
            from world.lore.player_presets import PLAYER_PRESET_REGISTRY
            from world.lore.races import RACE_REGISTRY
            from world.lore.sexual_vocab import EXPOSURE_LEVELS
            from world.lore.social_identities import SOCIAL_IDENTITY_REGISTRY
            from world.skills import SKILL_REGISTRY
        except Exception as exc:  # noqa: BLE001 - registry import is best effort
            self.warn(topic, where, "condition", f"registry checks skipped: {exc}")
            return

        if kind == RaceIs.kind:
            if condition.get("race_key") not in RACE_REGISTRY:
                self.error(topic, where, "condition", f"unknown race_key {condition.get('race_key')!r}")
        elif kind == SocialIdentityIs.kind:
            if condition.get("identity_key") not in SOCIAL_IDENTITY_REGISTRY:
                self.error(
                    topic, where, "condition", f"unknown identity_key {condition.get('identity_key')!r}"
                )
        elif kind == GuildRankAtLeast.kind:
            rank = condition.get("rank_key")
            if not isinstance(rank, str) or rank.upper() not in tuple("FEDCBA"):
                self.error(topic, where, "condition", f"unknown guild rank_key {rank!r}")
        elif kind == SkillOwned.kind:
            if condition.get("skill_key") not in SKILL_REGISTRY:
                self.error(
                    topic, where, "condition", f"unknown skill_key {condition.get('skill_key')!r}"
                )
            threshold = condition.get("min_proficiency")
            if threshold is not None and (not isinstance(threshold, int) or threshold < 0):
                self.error(topic, where, "condition", "min_proficiency must be a non-negative integer")
        elif kind == Exposure.kind:
            bounds = [condition.get("minimum"), condition.get("maximum")]
            if all(bound is None for bound in bounds):
                self.error(topic, where, "condition", "exposure needs minimum or maximum")
            for bound in bounds:
                if bound is not None and (
                    not isinstance(bound, int) or isinstance(bound, bool) or not 0 <= bound < len(EXPOSURE_LEVELS)
                ):
                    self.error(topic, where, "condition", f"exposure bound {bound!r} outside 0..4")
        elif kind == CompanionPresent.kind:
            source_kind = condition.get("source_kind")
            source_key = condition.get("source_key")
            if source_kind == "preset" and source_key not in PLAYER_PRESET_REGISTRY:
                self.error(topic, where, "condition", f"unknown companion preset {source_key!r}")
            elif source_kind not in ("preset", "profile", "package_role"):
                self.error(topic, where, "condition", f"unknown companion source_kind {source_kind!r}")
        elif kind in (QuestIs.kind, AffinityAtLeast.kind, TimePeriod.kind, Carries.kind):
            return  # keyed by registries the loader validates; nothing cheap to add here
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
        for token in SOFT_TOKENS:
            if token in text:
                self.warn(topic, where, "calque", f"「{token}」 may be a calque; confirm it is literal")
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
        for opener, closer in BRACKETS:
            if text.count(opener) != text.count(closer):
                self.error(topic, where, "brackets", f"unbalanced {opener}{closer}")
        if not plain and self.check_places:
            self._check_places(text, topic, where)

    def _check_places(self, text: str, topic: str, where: str) -> None:
        corpus = self._place_corpus()
        if corpus is None:
            return
        seen: set[str] = set()
        for run in CJK_RUN_RE.finditer(text):
            chunk = run.group(0)
            for suffix in PLACE_SUFFIX_RE.finditer(chunk):
                end = suffix.end()
                # Accept the run when any known place name ends at this suffix,
                # so a verb phrase in front of a real name stays quiet.
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
        if self._places is not None:
            return self._places
        sources = sorted(self.repo.glob("world/lore/settlements/places*.py"))
        doc = self.repo / "docs/lore/settlement-locations.md"
        if not sources and not doc.is_file():
            return None
        chunks: list[str] = []
        for path in [*sources, doc]:
            if path.is_file():
                chunks.append(path.read_text(encoding="utf-8", errors="ignore"))
        # Joining the harvested runs keeps a window from matching across lines.
        self._places = "\x00".join(re.findall(rf"[{CJK}]{{3,}}", "\n".join(chunks)))
        return self._places


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
    parser.add_argument("--repo", default=str(REPO_ROOT), help=argparse.SUPPRESS)
    args = parser.parse_args(argv)

    repo = Path(args.repo).resolve()
    if str(repo) not in sys.path:
        sys.path.insert(0, str(repo))
    findings: list[Finding] = []
    for path in expand_paths(args.targets):
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
        print(f"npc content lint: {errors} error(s), {warns} warning(s)")

    errors = any(f.severity == "ERROR" for f in findings)
    warns = any(f.severity == "WARN" for f in findings)
    return 1 if errors or (args.strict and warns) else 0


if __name__ == "__main__":
    raise SystemExit(main())
