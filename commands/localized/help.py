"""Localized zh-tw wrapper of Evennia's default help command (localize-limbo-zhtw D-5).

The upstream ``CmdHelp`` is a large subsystem; the wrapper keeps its topic
collection, permission filtering, subtopics, search, and webclient popup
behavior intact and overrides only the presentation layer (index, entry view)
plus the inline prose strings in ``func()``.
"""

from collections import defaultdict
from itertools import chain

from evennia.commands.default.help import CmdHelp as _CmdHelp, HelpCategory
from evennia.help.utils import help_search_with_index, parse_entry_for_subcategories
from evennia.utils.ansi import ANSIString
from evennia.utils.utils import dedent, format_grid, inherits_from, pad

# zh-tw display names for the upstream English help categories, applied in the
# index so a player never sees an English category heading (D-5).
CATEGORY_LABELS = {
    "general": "一般",
    "comms": "通訊",
    "building": "建造",
    "admin": "管理員",
    "combat": "戰鬥",
    "guild": "公會",
    "economy": "經濟",
}


def _category_label(category: str) -> str:
    return CATEGORY_LABELS.get(category.lower(), category)


class CmdHelp(_CmdHelp):
    """開啟說明系統

    用法：
      說明
      說明 <主題、指令或分類>
      說明 <主題>/<子主題>
      說明 <主題>/<子主題>/<次子主題> ...

    單獨使用「說明」會顯示所有說明主題的分類索引。部分較大的主題還提供
    子主題。
    """

    key = "說明"
    aliases = ["help", "?"]
    arg_regex = r"\s|$"

    def format_help_entry(
        self,
        topic="",
        help_text="",
        aliases=None,
        suggested=None,
        subtopics=None,
        click_topics=True,
    ):
        separator = "|C" + "-" * self.client_width() + "|n"
        start = f"{separator}\n"

        title = f"|C說明：|w{topic}|n" if topic else "|r找不到說明|n"

        if aliases:
            aliases = " |C(別名：{}|C)|n".format("|C、|n ".join(f"|w{ali}|n" for ali in aliases))
        else:
            aliases = ""

        help_text = "\n" + dedent(help_text.strip("\n")) if help_text else ""

        if subtopics:
            if click_topics:
                subtopics = [
                    f"|lchelp {topic}/{subtop}|lt|w{topic}/{subtop}|n|le" for subtop in subtopics
                ]
            else:
                subtopics = [f"|w{topic}/{subtop}|n" for subtop in subtopics]
            subtopics = "\n|C子主題：|n\n  {}".format(
                "\n  ".join(
                    format_grid(
                        subtopics, width=self.client_width(), line_prefix=self.index_topic_clr
                    )
                )
            )
        else:
            subtopics = ""

        if suggested:
            suggested = sorted(suggested)
            if click_topics:
                suggested = [f"|lchelp {sug}|lt|w{sug}|n|le" for sug in suggested]
            else:
                suggested = [f"|w{sug}|n" for sug in suggested]
            suggested = "\n|C其他建議主題：|n\n{}".format(
                "\n  ".join(
                    format_grid(
                        suggested, width=self.client_width(), line_prefix=self.index_topic_clr
                    )
                )
            )
        else:
            suggested = ""

        end = start

        partorder = (start, title + aliases, help_text, subtopics, suggested, end)

        return "\n".join(part.rstrip() for part in partorder if part)

    def format_help_index(
        self, cmd_help_dict=None, db_help_dict=None, title_lone_category=False, click_topics=True
    ):
        def _group_by_category(help_dict):
            grid = []
            verbatim_elements = []

            if len(help_dict) == 1 and not title_lone_category:
                for category in help_dict:
                    entries = sorted(set(help_dict.get(category, [])))
                    if click_topics:
                        entries = [f"|lchelp {entry}|lt{entry}|le" for entry in entries]
                    grid.extend(entries)
            else:
                for category in sorted(set(list(help_dict.keys()))):
                    label = _category_label(category)
                    category_str = f"-- {label} "
                    grid.append(
                        ANSIString(
                            self.index_category_clr
                            + category_str
                            + "-" * (width - len(category_str))
                            + self.index_topic_clr
                        )
                    )
                    verbatim_elements.append(len(grid) - 1)

                    entries = sorted(set(help_dict.get(category, [])))
                    if click_topics:
                        entries = [f"|lchelp {entry}|lt{entry}|le" for entry in entries]
                    grid.extend(entries)

            return grid, verbatim_elements

        help_index = ""
        width = self.client_width()
        grid = []
        verbatim_elements = []
        cmd_grid, db_grid = "", ""

        if any(cmd_help_dict.values()):
            sep1 = (
                self.index_type_separator_clr
                + pad("指令", width=width, fillchar="-")
                + self.index_topic_clr
            )
            grid, verbatim_elements = _group_by_category(cmd_help_dict)
            gridrows = format_grid(
                grid,
                width,
                sep="  ",
                verbatim_elements=verbatim_elements,
                line_prefix=self.index_topic_clr,
            )
            cmd_grid = ANSIString("\n").join(gridrows) if gridrows else ""

        if any(db_help_dict.values()):
            sep2 = (
                self.index_type_separator_clr
                + pad("遊戲與世界", width=width, fillchar="-")
                + self.index_topic_clr
            )
            grid, verbatim_elements = _group_by_category(db_help_dict)
            gridrows = format_grid(
                grid,
                width,
                sep="  ",
                verbatim_elements=verbatim_elements,
                line_prefix=self.index_topic_clr,
            )
            db_grid = ANSIString("\n").join(gridrows) if gridrows else ""

        if cmd_grid and db_grid:
            help_index = f"{sep1}\n{cmd_grid}\n{sep2}\n{db_grid}"
        else:
            help_index = f"{cmd_grid}{db_grid}"

        return help_index

    def func(self):
        """執行說明（上游邏輯，zh-tw 訊息）。"""
        caller = self.caller
        query, subtopics, cmdset = self.topic, self.subtopics, self.cmdset
        clickable_topics = self.clickable_topics

        if not query:
            cmd_help_topics, db_help_topics, file_help_topics = self.collect_topics(
                caller, mode="list"
            )
            file_db_help_topics = {**file_help_topics, **db_help_topics}

            cmd_help_by_category = defaultdict(list)
            file_db_help_by_category = defaultdict(list)

            key_and_aliases = set(chain(*(cmd._keyaliases for cmd in cmd_help_topics.values())))

            for key, cmd in cmd_help_topics.items():
                key = self.strip_cmd_prefix(key, key_and_aliases)
                cmd_help_by_category[cmd.help_category].append(key)
            for key, entry in file_db_help_topics.items():
                file_db_help_by_category[entry.help_category].append(key)

            output = self.format_help_index(
                cmd_help_by_category, file_db_help_by_category, click_topics=clickable_topics
            )
            self.msg_help(output)
            return

        cmd_help_topics, db_help_topics, file_help_topics = self.collect_topics(
            caller, mode="query"
        )
        key_and_aliases = set(chain(*(cmd._keyaliases for cmd in cmd_help_topics.values())))

        file_db_help_topics = {**file_help_topics, **db_help_topics}
        all_topics = {**file_db_help_topics, **cmd_help_topics}

        all_categories = list(
            set(HelpCategory(topic.help_category) for topic in all_topics.values())
        )
        entries = list(all_topics.values()) + all_categories

        match, suggestions = self.do_search(query, entries)

        if not match:
            help_text = f"沒有符合 '{query}' 的說明主題。"

            if not suggestions:
                search_fields = [
                    {"field_name": "text", "boost": 1},
                ]
                for match_query in [query, f"{query}*", f"*{query}"]:
                    _, suggestions = help_search_with_index(
                        match_query,
                        entries,
                        suggestion_maxnum=self.suggestion_maxnum,
                        fields=search_fields,
                    )
                    if suggestions:
                        help_text += "\n……但在下列建議主題的內文中找到了相符內容。"
                        suggestions = [
                            self.strip_cmd_prefix(sugg, key_and_aliases) for sugg in suggestions
                        ]
                        break

            output = self.format_help_entry(
                topic=None,
                help_text=help_text,
                suggested=suggestions,
                click_topics=clickable_topics,
            )
            self.msg_help(output)
            return

        if isinstance(match, HelpCategory):
            category = match.key
            category_lower = category.lower()
            cmds_in_category = [
                key for key, cmd in cmd_help_topics.items() if category_lower == cmd.help_category
            ]
            topics_in_category = [
                key
                for key, topic in file_db_help_topics.items()
                if category_lower == topic.help_category
            ]
            output = self.format_help_index(
                {category: cmds_in_category},
                {category: topics_in_category},
                title_lone_category=True,
                click_topics=clickable_topics,
            )
            self.msg_help(output)
            return

        if inherits_from(match, "evennia.commands.command.Command"):
            topic = match.key
            help_text = match.get_help(caller, cmdset)
            aliases = match.aliases
            suggested = suggestions[1:]
        else:
            topic = match.key
            help_text = match.entrytext
            aliases = match.aliases if isinstance(match.aliases, list) else match.aliases.all()
            suggested = suggestions[1:]

        subtopic_map = parse_entry_for_subcategories(help_text)
        help_text = subtopic_map[None]
        subtopic_index = [subtopic for subtopic in subtopic_map if subtopic is not None]

        if subtopics:
            for subtopic_query in subtopics:
                if subtopic_query not in subtopic_map:
                    fuzzy_match = False
                    for key in subtopic_map:
                        if key and key.startswith(subtopic_query):
                            subtopic_query = key
                            fuzzy_match = True
                            break
                    if not fuzzy_match:
                        for key in subtopic_map:
                            if key and subtopic_query in key:
                                subtopic_query = key
                                fuzzy_match = True
                                break
                    if not fuzzy_match:
                        checked_topic = topic + f"{self.subtopic_separator_char}{subtopic_query}"
                        output = self.format_help_entry(
                            topic=topic,
                            help_text=f"沒有找到 '{checked_topic}' 的說明。",
                            subtopics=subtopic_index,
                            click_topics=clickable_topics,
                        )
                        self.msg_help(output)
                        return

                subtopic_map = subtopic_map.pop(subtopic_query)
                subtopic_index = [subtopic for subtopic in subtopic_map if subtopic is not None]
                topic = topic + f"{self.subtopic_separator_char}{subtopic_query}"

            help_text = subtopic_map[None]

        topic = self.strip_cmd_prefix(topic, key_and_aliases)
        if subtopics:
            aliases = None
        else:
            aliases = [self.strip_cmd_prefix(alias, key_and_aliases) for alias in aliases]
        suggested = [self.strip_cmd_prefix(sugg, key_and_aliases) for sugg in suggested]

        output = self.format_help_entry(
            topic=topic,
            help_text=help_text,
            aliases=aliases,
            subtopics=subtopic_index,
            suggested=suggested,
            click_topics=clickable_topics,
        )
        self.msg_help(output)
