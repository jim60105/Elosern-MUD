"""Regression checks that the player command documentation cannot drift.

The docs pages under ``docs/game/`` are the player-facing contract for every
typed in-game command. This module cross-checks the mounted command registry
(the project ``CharacterCmdSet`` plus the ``character`` creation command and
the nested ``XYZGridCmdSet``), the curated syntax/context manifest, the Evennia
default character/account cmdset key sets, the overview page, the sidebar, and
the ``AGENTS.md`` convention against the reference page. It follows the
top-level bootstrap pattern of ``tests/test_contrib_matrix.py`` and opens no
database.
"""

from tools.spec_traceability import covers_requirement

import os
import re
import unittest
from pathlib import Path

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "server.conf.settings")

import django

django.setup()

import evennia

evennia._init()

from evennia import default_cmds
from evennia.commands.cmdhandler import CMD_NOMATCH

from commands.character_creation import CharacterCreationCmdSet
from commands.default_cmdsets import AccountCmdSet, CharacterCmdSet
from commands.localized import (
    LOCALIZED_ACCOUNT_KEYS,
    LOCALIZED_CHARACTER_KEYS,
    LOCALIZED_ORIGINAL_KEYS,
    LOCALIZED_XYZGRID_KEYS,
    ProjectXYZGridCmdSet,
)


REPO_ROOT = Path(__file__).resolve().parents[1]
REFERENCE_PATH = REPO_ROOT / "docs" / "game" / "command-reference.md"
OVERVIEW_PATH = REPO_ROOT / "docs" / "game" / "commands.md"
SIDEBAR_PATH = REPO_ROOT / "docs" / "_sidebar.md"
AGENTS_PATH = REPO_ROOT / "AGENTS.md"
INDEX_PATH = REPO_ROOT / "docs" / "index.html"

EVENNIA_DOCS_POINTER = "https://evennia.com/docs/latest/Components/Commands.html"

CHARACTER_TABLE_HEADING = "Evennia 預設角色指令（CharacterCmdSet）"
ACCOUNT_TABLE_HEADING = "Evennia 預設帳號指令（AccountCmdSet）"
LOCALIZED_TABLE_HEADING = "本地化預設指令（Localized zh-tw Defaults）"

# Curated syntax/context manifest. The commands parse ``self.args`` by hand,
# so argument syntax cannot be derived mechanically and is the single
# human-review point; every other fact (keys, aliases, admin locks, help
# categories) is verified against the command classes instead.
EXPECTED_COMMANDS: dict[str, dict[str, str]] = {
    "talk": {
        "syntax": "talk <npc>、talk <npc> <keyword> [<quest_id>]",
        "context": "一般（需有交談對象）",
    },
    "invite": {
        "syntax": "invite <npc> [訊息]",
        "context": "一般（需有可邀請的 NPC）",
    },
    "leave": {"syntax": "leave <npc>", "context": "一般（需有同伴）"},
    "lore": {"syntax": "lore、lore <category> <key>", "context": "一般（隨時可用）"},
    "rest": {"syntax": "rest <duration> [practice <skill>]", "context": "一般"},
    "sleep": {"syntax": "sleep", "context": "一般"},
    "wait": {"syntax": "wait until <midnight|dawn|noon|dusk>", "context": "一般"},
    "進入": {"syntax": "進入", "context": "一般（需有任務場景入口）"},
    "cast": {
        "syntax": "cast <skill_key>[@<scale>][=<target_key>]",
        "context": "一般（戰鬥內外皆可施放技能）",
    },
    "lineage": {"syntax": "lineage", "context": "一般（戰鬥內外皆可用）"},
    "engage": {"syntax": "engage <target>", "context": "戰鬥（需有敵對魔物）"},
    "combat forfeit": {"syntax": "combat forfeit", "context": "戰鬥（需在進行中的戰鬥）"},
    "combat actions": {"syntax": "combat actions", "context": "戰鬥（需在進行中的戰鬥）"},
    "guild register": {
        "syntax": "guild register",
        "context": "公會（需當地公會服務人員）",
    },
    "guild list": {"syntax": "guild list", "context": "公會（需當地公會服務人員）"},
    "guild accept": {
        "syntax": "guild accept <definition_key>",
        "context": "公會（需當地公會服務人員）",
    },
    "guild log": {"syntax": "guild log", "context": "公會（需當地公會服務人員）"},
    "guild show": {
        "syntax": "guild show <quest_id>",
        "context": "公會（需當地公會服務人員）",
    },
    "guild abandon": {
        "syntax": "guild abandon <quest_id>",
        "context": "公會（需當地公會服務人員）",
    },
    "guild turnin": {
        "syntax": "guild turnin <quest_id>",
        "context": "公會（需當地公會服務人員）",
    },
    "guild merit": {"syntax": "guild merit", "context": "公會（需當地公會服務人員）"},
    "guild request": {
        "syntax": "guild request [討伐|採集|護衛|探索|緊急]",
        "context": "公會（需已註冊冒險者）",
    },
    "guild exam": {"syntax": "guild exam [<rank>]", "context": "公會（需當地考核官）"},
    "shop stock": {"syntax": "shop stock", "context": "經濟（需當地商人）"},
    "buy": {"syntax": "buy <item_key> [數量]", "context": "經濟（需當地商人）"},
    "sell": {"syntax": "sell <item_key> [數量]", "context": "經濟（需當地商人）"},
    "inventory": {"syntax": "inventory", "context": "一般（隨時可用）"},
    "使用": {"syntax": "使用 <item_key>", "context": "一般（探索與戰鬥中皆可用）"},
    "裝備": {"syntax": "裝備 <item_key>", "context": "一般（探索與戰鬥中皆可用）"},
    "art status": {
        "syntax": "art status [scene|portrait|monster]",
        "context": "管理員（需 Developer 權限）",
    },
    "art run": {
        "syntax": "art run [--limit N]",
        "context": "管理員（需 Developer 權限）",
    },
    "art retry": {"syntax": "art retry", "context": "管理員（需 Developer 權限）"},
    "art requeue": {
        "syntax": "art requeue <full-subject-key>",
        "context": "管理員（需 Developer 權限）",
    },
    "art options": {
        "syntax": "art options <models|samplers|schedulers|styles|modules>",
        "context": "管理員（需 Developer 權限）",
    },
    "art health": {"syntax": "art health", "context": "管理員（需 Developer 權限）"},
    "character": {
        "syntax": "character、character preset <key>、character create、character concept <構想>",
        "context": "角色建立（建立模式取代一般指令，仍可用 說明 與 登出）",
    },
    "character concept": {
        "syntax": "character concept <構想>",
        "context": "角色建立（建立模式取代一般指令，仍可用 說明 與 登出）",
    },
    "前往": {
        "syntax": "前往 <地點>、path <地點>、path clear",
        "context": "一般（探索與移動）",
    },
    "地圖": {"syntax": "地圖 [Z 座標]、地圖 list", "context": "一般（探索，需建造者權限）"},
    "看": {"syntax": "看、look", "context": "一般（隨時可用）"},
    "說明": {"syntax": "說明 [<主題>]", "context": "一般（隨時可用）"},
    "說": {"syntax": "說 <訊息>", "context": "一般"},
    "動作": {"syntax": "動作 <動作描述>", "context": "一般"},
    "拿": {"syntax": "拿 <物品>", "context": "一般"},
    "丟": {"syntax": "丟 <物品>", "context": "一般"},
    "給": {"syntax": "給 <物品> = <對象>", "context": "一般"},
    "回家": {"syntax": "回家", "context": "一般（需 home 權限或建造者權限）"},
    "耳語": {"syntax": "耳語 <角色> = <訊息>", "context": "一般"},
    "暱稱": {"syntax": "暱稱 <字串> = [<替換字串>]", "context": "一般"},
    "設定描述": {"syntax": "設定描述 <描述>", "context": "一般"},
    "設定背景": {"syntax": "設定背景 <文字>", "context": "一般（已啟用的角色）"},
    "title": {
        "syntax": "title list、title codex、title equip fixed <display|key>、title equip epithet <display>、title accept <1|2|3>、title decline、title remove epithet <display> [confirm]",
        "context": "一般（戰鬥內外皆可用）",
    },
    "登出": {"syntax": "登出", "context": "一般（隨時可用）"},
    "在線": {"syntax": "在線", "context": "一般"},
    "離開角色": {"syntax": "離開角色", "context": "一般"},
    "進入世界": {"syntax": "進入世界 [<角色>]", "context": "一般（需有可附身角色）"},
    "傳訊": {"syntax": "傳訊 <帳號> <訊息>", "context": "一般（通訊）"},
    "密碼": {"syntax": "密碼 <舊密碼> = <新密碼>", "context": "一般"},
    "選項": {"syntax": "選項 [名稱 = 數值]", "context": "一般"},
    "連線": {"syntax": "連線", "context": "一般"},
    "色彩": {"syntax": "色彩 ansi、xterm256、truecolor", "context": "一般"},
    "樣式": {"syntax": "樣式 [<選項> = <數值>]", "context": "一般"},
    "降權": {"syntax": "降權", "context": "一般"},
    "@teleport": {
        "syntax": "@teleport <目標位置>、@teleport (X,Y[,Z])、@teleport <物件> = <目標位置>",
        "context": "一般（探索與建造，需建造者權限）",
    },
    "@open": {
        "syntax": (
            "@open <新出口>[;別名;..] = <目的地>、"
            "@open <新出口>[;別名;..],<回程出口>[;別名;..] = <目的地>、"
            "@open <新出口> = (X,Y,Z)"
        ),
        "context": "一般（建造，需建造者權限）",
    },
}

# The context row SHALL be consistent with the class help_category when the
# latter is one of the project's owned categories.
CONTEXT_KEYWORD_BY_CATEGORY = {
    "combat": "戰鬥",
    "guild": "公會",
    "economy": "經濟",
    "admin": "管理員",
}

CANONICAL_HEADING = re.compile(r"^### (.+)$")
SECTION_HEADING = re.compile(r"^## (.+)$")
TABLE_ROW = re.compile(r"^\| (.+) \| (.+) \|$")
CANONICAL_FIELDS = ("指令", "別名", "語法", "情境", "說明")


def _command_aliases(command) -> set[str]:
    raw = command.aliases
    if isinstance(raw, str):
        return {raw}
    return set(raw)


def mounted_command_classes() -> dict[str, object]:
    """Return key -> command instance for every command the docs must cover.

    The project ``CharacterCmdSet`` and ``AccountCmdSet`` merged sets, filtered
    by class identity against the Evennia defaults, yield the project-authored
    surface (project overrides such as ``inventory`` collide with default keys,
    so key subtraction alone is insufficient); the nested project XYZGrid set
    is expanded explicitly so its ``@open``/``@teleport`` overrides are never
    lost to key collisions with the defaults, and ``CharacterCreationCmdSet``
    contributes ``character``. The non-typable ``CMD_NOMATCH`` gate is
    deliberately excluded.
    """
    merged = {
        command.key: command
        for cmdset in (CharacterCmdSet(), AccountCmdSet())
        for command in cmdset.commands
    }
    default_classes = {
        type(command)
        for cmdset in (
            default_cmds.CharacterCmdSet(),
            default_cmds.AccountCmdSet(),
        )
        for command in cmdset.commands
    }
    classes = {
        key: command for key, command in merged.items() if type(command) not in default_classes
    }
    classes.update({command.key: command for command in ProjectXYZGridCmdSet().commands})
    classes.update(
        {
            command.key: command
            for command in CharacterCreationCmdSet().commands
            if command.key != CMD_NOMATCH and type(command) not in default_classes
        }
    )
    return classes


def parse_canonical_entries(text: str) -> dict[str, dict[str, str]]:
    """Parse the `### <key>` canonical sections of the reference page.

    Any other heading level closes the current canonical section, so rows
    belonging to the `##`-level index tables are never attributed to it.
    """
    entries: dict[str, dict[str, str]] = {}
    current: str | None = None
    for line in text.splitlines():
        if line.startswith("#"):
            heading = CANONICAL_HEADING.match(line)
            if heading:
                current = heading.group(1).strip().strip("`")
                entries.setdefault(current, {})
            else:
                current = None
            continue
        if current is None:
            continue
        row = TABLE_ROW.match(line.strip())
        if row is None:
            continue
        field, value = row.group(1).strip(), row.group(2).strip().strip("`")
        if field in CANONICAL_FIELDS:
            entries[current][field] = value
    return entries


def parse_aliases(content: str) -> set[str]:
    """Parse a 別名 row: backticked tokens separated by 、, or （無）."""
    content = content.strip()
    if content in ("（無）", "無"):
        return set()
    return {token.strip().strip("`").strip() for token in content.split("、")}


def parse_default_tables(text: str) -> dict[str, dict[str, str]]:
    """Parse the `##`-level Evennia default index tables.

    Data rows are shaped `| `key` | 描述 |`; the GFM header (`| 指令 | 描述 |`)
    and delimiter rows are skipped because their first cell is not backticked.
    """
    tables: dict[str, dict[str, str]] = {}
    current: str | None = None
    for line in text.splitlines():
        heading = SECTION_HEADING.match(line.strip())
        if heading:
            current = heading.group(1).strip()
            tables.setdefault(current, {})
            continue
        if current is None:
            continue
        row = TABLE_ROW.match(line.strip())
        if row is None:
            continue
        first = row.group(1).strip()
        if not (first.startswith("`") and first.endswith("`")):
            continue
        tables[current][first.strip("`")] = row.group(2).strip()
    return tables


def docsify_slug(key: str) -> str:
    """Mirror docsify 4.13's heading slugifier for anchor verification."""
    slug = key.lower()
    slug = re.sub(r"[\u2000-\u206F\u2E00-\u2E7F\\'\"!#$%&()*+,./:;<=>?@\[\]^`{|}~]", "", slug)
    slug = re.sub(r"\s+", "-", slug)
    slug = re.sub(r"-+", "-", slug)
    return re.sub(r"^(\d)", r"_\1", slug)


def parse_overview_links(text: str) -> dict[str, str]:
    """Return key -> anchor fragment for every reference link in the overview.

    Links use root-relative docsify routes (``/game/command-reference?id=``);
    a page-relative href such as ``command-reference#`` would resolve against
    the site root instead of the current page directory.
    """
    return {
        match.group(1): match.group(2)
        for match in re.finditer(r"\[`([^`]+)`\]\(/game/command-reference\?id=([^)]+)\)", text)
    }


class DocsifySlugTests(unittest.TestCase):
    """Pin the docsify 4.13.1 slugifier mirror against known headings."""

    def test_known_heading_slugs(self):
        self.assertEqual(docsify_slug("進入"), "進入")
        self.assertEqual(docsify_slug("@teleport"), "teleport")
        self.assertEqual(docsify_slug("@open"), "open")
        self.assertEqual(docsify_slug("guild accept"), "guild-accept")
        self.assertEqual(docsify_slug("combat forfeit"), "combat-forfeit")


class CommandDocsContractTests(unittest.TestCase):
    """Contract between the player command docs and the mounted registry."""

    def setUp(self):
        self.reference = REFERENCE_PATH.read_text(encoding="utf-8")
        self.overview = OVERVIEW_PATH.read_text(encoding="utf-8")
        self.sidebar = SIDEBAR_PATH.read_text(encoding="utf-8")
        self.agents = AGENTS_PATH.read_text(encoding="utf-8")
        self.entries = parse_canonical_entries(self.reference)
        self.mounted = mounted_command_classes()

    def _section_text(self, key: str) -> str:
        """Return the raw text of one canonical section (table plus trailing prose).

        ``parse_canonical_entries`` attributes only table rows to a key, so the
        section's trailing prose must be read from the raw file instead.
        """
        lines = self.reference.splitlines()
        start = next(
            index for index, line in enumerate(lines) if line.strip() == f"### {key}"
        )
        body: list[str] = []
        for line in lines[start + 1 :]:
            if line.startswith("#"):
                break
            body.append(line)
        return "\n".join(body)

    @covers_requirement("game-command-docs::complete-command-reference", "game-command-docs::drift-contract-test")
    def test_every_mounted_project_command_is_documented(self):
        manifest_keys = set(EXPECTED_COMMANDS)
        self.assertCountEqual(
            manifest_keys,
            self.mounted.keys(),
            "the curated manifest and the mounted command registry diverged",
        )
        for key in self.mounted:
            self.assertIn(
                key,
                self.entries,
                f"mounted command {key!r} has no canonical entry in {REFERENCE_PATH.name}",
            )

    @covers_requirement("game-command-docs::complete-command-reference")
    def test_character_creation_is_a_single_entry(self):
        entry = self.entries["character"]
        self.assertEqual(entry["指令"], "character")
        self.assertEqual(parse_aliases(entry["別名"]), {"角色"})
        self.assertIn("character preset <key>", entry["語法"])
        self.assertIn("character create", entry["語法"])
        self.assertIn("character concept <構想>", entry["語法"])
        self.assertIn("cancel", entry["說明"])
        self.assertIn("取代", entry["情境"])
        self.assertIn("說明", entry["情境"])
        self.assertIn("登出", entry["情境"])

    @covers_requirement("game-command-docs::complete-command-reference")
    def test_character_concept_entry_is_documented(self):
        entry = self.entries["character concept"]
        self.assertEqual(entry["指令"], "character concept")
        self.assertEqual(parse_aliases(entry["別名"]), {"構想"})
        self.assertIn("character concept <構想>", entry["語法"])
        self.assertIn("生成不可用，請手動創角", entry["說明"])
        self.assertIn("18", entry["說明"])

    @covers_requirement("game-command-docs::complete-command-reference")
    def test_contrib_commands_are_documented(self):
        for key in ("前往", "地圖", "@teleport", "@open"):
            entry = self.entries[key]
            self.assertEqual(entry["指令"], key)
            self.assertTrue(entry["語法"])
            self.assertTrue(entry["說明"])

    @covers_requirement("game-command-docs::complete-command-reference", "game-command-docs::drift-contract-test")
    def test_default_index_tables_match_evennia_cmdsets(self):
        tables = parse_default_tables(self.reference)
        character_keys = {command.key for command in default_cmds.CharacterCmdSet().commands}
        account_keys = {command.key for command in default_cmds.AccountCmdSet().commands}
        expected = {
            CHARACTER_TABLE_HEADING: character_keys - LOCALIZED_ORIGINAL_KEYS,
            ACCOUNT_TABLE_HEADING: account_keys - LOCALIZED_ORIGINAL_KEYS,
            LOCALIZED_TABLE_HEADING: set(
                LOCALIZED_CHARACTER_KEYS
                + LOCALIZED_ACCOUNT_KEYS
                + LOCALIZED_XYZGRID_KEYS
            ),
        }
        for heading, keys in expected.items():
            rows = tables.get(heading)
            self.assertIsNotNone(rows, f"index table {heading!r} is missing")
            self.assertEqual(
                rows.keys(),
                keys,
                f"index table {heading!r} drifted from the mounted cmdset",
            )
            for key, description in rows.items():
                self.assertTrue(
                    description.strip(),
                    f"index table {heading!r} row {key!r} has an empty description",
                )

    @covers_requirement("game-command-docs::complete-command-reference")
    def test_reference_points_to_evennia_documentation(self):
        self.assertIn(EVENNIA_DOCS_POINTER, self.reference)

    @covers_requirement("game-command-docs::the-command-reference-documents-the-title-commands")
    @covers_requirement("game-command-docs::the-command-reference-documents-the-lineage-command")
    @covers_requirement("game-command-docs::accurate-command-details")
    def test_key_and_aliases_match_command_classes(self):
        for key, command in self.mounted.items():
            entry = self.entries[key]
            self.assertEqual(entry["指令"], key)
            self.assertEqual(
                parse_aliases(entry["別名"]),
                _command_aliases(command),
                f"aliases for {key!r} drifted from the command class",
            )

    @covers_requirement("game-command-docs::the-command-reference-documents-the-title-commands")
    @covers_requirement("game-command-docs::the-command-reference-documents-the-lineage-command")
    @covers_requirement("game-command-docs::accurate-command-details")
    def test_syntax_and_context_match_manifest(self):
        for key, expected in EXPECTED_COMMANDS.items():
            entry = self.entries[key]
            self.assertEqual(
                entry["語法"].replace("`", ""),
                expected["syntax"],
                f"syntax for {key!r} drifted from the curated manifest",
            )
            self.assertEqual(
                entry["情境"],
                expected["context"],
                f"context for {key!r} drifted from the curated manifest",
            )

    @covers_requirement("game-command-docs::the-command-reference-documents-the-lineage-command")
    def test_lineage_entry_documents_the_ledger_surface(self):
        entry = self.entries["lineage"]
        self.assertEqual(entry["指令"], "lineage")
        self.assertEqual(parse_aliases(entry["別名"]), set())
        self.assertEqual(entry["語法"].replace("`", ""), "lineage")
        self.assertEqual(entry["情境"], EXPECTED_COMMANDS["lineage"]["context"])
        for token in ("見頂", "門檻", "熟練度"):
            self.assertIn(token, entry["說明"])
        row = next(
            line
            for line in self.overview.splitlines()
            if line.startswith("| [`lineage`](")
        )
        self.assertIn("見頂", row)
        self.assertIn("門檻", row)

    @covers_requirement("game-command-docs::the-cast-command-reference-documents-the-optional-scale-token")
    def test_cast_entry_documents_the_freeform_scale_token(self):
        entry = self.entries["cast"]
        self.assertEqual(
            entry["語法"].replace("`", ""),
            EXPECTED_COMMANDS["cast"]["syntax"],
        )
        self.assertEqual(
            entry["語法"],
            "cast <skill_key>[@<scale>][=<target_key>]",
        )
        for token in ("1/4", "1/2", "1", "2", "4"):
            self.assertIn(token, entry["說明"])
        self.assertIn("主宰", entry["說明"])
        self.assertIn("威力", entry["說明"])
        self.assertIn("MP", entry["說明"])

    @covers_requirement(
        "game-command-docs::the-command-reference-documents-the-sexual-act-system",
        "game-command-docs::the-command-reference-documents-the-resist-affinity-and-status-consequences",
    )
    def test_cast_and_combat_actions_document_sexual_acts(self):
        cast_description = self.entries["cast"]["說明"]
        self.assertIn("性愛", cast_description)
        self.assertIn("解鎖", cast_description)
        combat_description = self.entries["combat actions"]["說明"]
        self.assertIn("性愛", combat_description)
        cast_section = self._section_text("cast")
        for token in ("抵抗", "好感度", "解鎖", "興奮", "高潮", "露出", "戰鬥", "神之秘法"):
            self.assertIn(token, cast_section)
        for label in ("絕頂律令", "時姦", "神域搾取", "感度創世", "恥辱剝奪", "絕對從屬", "無垢回歸"):
            self.assertNotIn(label, cast_section)

    @covers_requirement(
        "game-command-docs::the-overview-page-describes-the-sexual-act-system-s-discoverability"
    )
    def test_overview_cast_row_mentions_sexual_acts(self):
        row = next(line for line in self.overview.splitlines() if line.startswith("| [`cast`]("))
        self.assertIn("性愛", row)
        self.assertIn("解鎖", row)

    @covers_requirement("game-command-docs::accurate-command-details")
    def test_context_consistent_with_help_category(self):
        for key, command in self.mounted.items():
            category = (command.help_category or "").lower()
            keyword = CONTEXT_KEYWORD_BY_CATEGORY.get(category)
            if keyword is not None:
                self.assertIn(
                    keyword,
                    EXPECTED_COMMANDS[key]["context"],
                    f"context for {key!r} is inconsistent with help_category {category!r}",
                )

    @covers_requirement("game-command-docs::accurate-command-details")
    def test_description_is_non_empty(self):
        for key, entry in self.entries.items():
            description = entry.get("說明", "").strip()
            self.assertTrue(description, f"canonical entry {key!r} has an empty 說明 row")
            self.assertRegex(
                description,
                r"[\u4e00-\u9fff]",
                f"canonical entry {key!r} 說明 is not Traditional Chinese prose",
            )

    @covers_requirement("game-command-docs::accurate-command-details")
    def test_rest_entry_documents_the_practice_clause(self):
        entry = self.entries["rest"]
        self.assertEqual(
            entry["語法"], "rest <duration> [practice <skill>]"
        )
        self.assertEqual(entry["語法"], EXPECTED_COMMANDS["rest"]["syntax"])
        description = entry["說明"]
        # Declared practice settles hourly proficiency, and a clause-less
        # rest is explicitly zero-growth (the delta scenario's two claims).
        self.assertIn("practice <技能>", description)
        self.assertIn("每整小時", description)
        self.assertIn("不帶來任何成長", description)
        overview_row = next(
            line
            for line in self.overview.splitlines()
            if line.startswith("| [`rest`]")
        )
        self.assertIn("`practice <技能>`", overview_row)
        self.assertIn("熟練度", overview_row)

    @covers_requirement("game-command-docs::accurate-command-details")
    def test_admin_marking_matches_class_locks(self):
        for key, command in self.mounted.items():
            context = EXPECTED_COMMANDS[key]["context"]
            locks = command.locks or ""
            marked_admin = "管理員" in context
            locked_developer = "perm(Developer)" in locks
            self.assertEqual(
                marked_admin,
                locked_developer,
                f"admin marking for {key!r} disagrees with its class locks",
            )
            marked_builder = "建造者權限" in context
            locked_builder = "perm(Builder" in locks
            self.assertEqual(
                marked_builder,
                locked_builder,
                f"builder marking for {key!r} disagrees with its class locks",
            )

    @covers_requirement("game-command-docs::drift-contract-test")
    def test_no_orphan_canonical_entries(self):
        for key in self.entries:
            self.assertIn(
                key,
                self.mounted,
                f"canonical entry {key!r} documents a command that is not mounted",
            )

    @covers_requirement("game-command-docs::the-command-reference-documents-the-title-commands")
    @covers_requirement("game-command-docs::the-command-reference-documents-the-lineage-command")
    @covers_requirement("game-command-docs::drift-contract-test")
    def test_overview_links_only_documented_keys_and_all_keys(self):
        links = parse_overview_links(self.overview)
        self.assertCountEqual(links.keys(), self.entries.keys())
        for key, fragment in links.items():
            self.assertEqual(
                fragment,
                docsify_slug(key),
                f"overview anchor for {key!r} would not match the rendered heading",
            )

    @covers_requirement("game-command-docs::complete-command-reference")
    def test_overview_groups_commands_by_category(self):
        for category in (
            "探索與移動",
            "對話",
            "時間跳躍",
            "戰鬥",
            "技能施放",
            "公會",
            "經濟",
            "角色建立",
            "管理員",
            "系統與建造",
        ):
            self.assertIn(f"## {category}", self.overview)

    @covers_requirement("game-command-docs::docsify-navigation", "game-command-docs::drift-contract-test")
    def test_sidebar_links_both_pages(self):
        self.assertIn("](/game/commands)", self.sidebar)
        self.assertIn("](/game/command-reference)", self.sidebar)
        index_html = INDEX_PATH.read_text(encoding="utf-8")
        self.assertIn("loadSidebar", index_html)

    @covers_requirement("game-command-docs::documentation-update-convention", "game-command-docs::drift-contract-test")
    def test_agents_md_has_update_convention(self):
        self.assertIn("docs/game/commands.md", self.agents)
        self.assertIn("docs/game/command-reference.md", self.agents)
        self.assertIn("tests/test_command_docs.py", self.agents)

    @covers_requirement("game-command-docs::drift-contract-test")
    def test_sidebar_overview_and_agent_guide_stay_consistent(self):
        self.assertIn("](/game/commands)", self.sidebar)
        self.assertIn("](/game/command-reference)", self.sidebar)
        links = parse_overview_links(self.overview)
        self.assertCountEqual(links.keys(), self.entries.keys())
        self.assertIn("docs/game/command-reference.md", self.agents)
