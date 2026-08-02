"""Player-facing guild registration, board, quest-log, and turn-in commands."""

from evennia import Command

from typeclasses.components import GuildStaff
from world.quests.describe import describe_objective, describe_quest_detail
from world.quests.definitions import QUEST_DEFINITION_REGISTRY
from world.quests.runtime import (
    QuestDataError,
    QuestNotFound,
    QuestState,
    definition_for,
    find_record,
    read_records,
)
from world.rules.clock import get_world_clock
from world.rules.guild import (
    GuildDataError,
    GuildError,
    GuildServiceError,
    RewardClaimError,
    parse_guild_registration,
    parse_reward_claims,
    register_adventurer,
    turn_in_quest,
)
from world.rules.guild_offers import (
    BoardAccessError,
    GuildOfferError,
    GuildOfferNotFound,
    abandon_guild_quest,
    accept_guild_offer,
    get_guild_offer,
    list_guild_offers,
)
from world.rules.guild_config import get_catalog
from world.rules.surfaces import read_counter_trait


class _GuildCommandBase(Command):
    """Base for commands that resolve one local GuildStaff host."""

    locks = "cmd:all()"
    help_category = "Guild"

    def resolve_staff(self):
        try:
            from world.rules.guild import resolve_local_service_host

            return resolve_local_service_host(self.caller, GuildStaff)
        except GuildServiceError:
            self.caller.msg("這裡沒有公會服務人員。")
            return None


class CmdGuildRegister(_GuildCommandBase):
    """Register as an adventurer at rank F."""

    key = "guild register"
    aliases = ("guild 註冊", "註冊公會", "guild join")

    def func(self) -> None:
        staff = self.resolve_staff()
        if staff is None:
            return
        try:
            record = register_adventurer(self.caller, staff)
        except (GuildDataError, GuildError) as error:
            self.caller.msg(f"註冊失敗：{error}")
            return
        self.caller.msg(f"你已註冊為冒險者，階級 F。公會：{record['branch_key']}")


class CmdGuildList(_GuildCommandBase):
    """List board offers available to your guild rank."""

    key = "guild list"
    aliases = ("guild 任務", "任務列表")

    def func(self) -> None:
        staff = self.resolve_staff()
        if staff is None:
            return
        try:
            offers = list_guild_offers(self.caller, staff)
        except BoardAccessError as error:
            self.caller.msg(f"無法查看任務板：{error}")
            return
        if not offers:
            self.caller.msg("任務板上目前沒有適合你的任務。")
            return
        lines = ["任務板："]
        for offer in offers:
            definition = QUEST_DEFINITION_REGISTRY[offer.definition_key]
            lines.append(
                f"  {offer.definition_key} — {definition.display_name} "
                f"(銅 {offer.reward.copper} / 功績 {offer.reward.merit})"
                f" — {describe_objective(definition.stages[0].objective)}"
            )
        self.caller.msg("\n".join(lines))


class CmdGuildAccept(_GuildCommandBase):
    """Accept a board offer by definition key."""

    key = "guild accept"
    aliases = ("guild 接取", "接取任務")

    def func(self) -> None:
        staff = self.resolve_staff()
        if staff is None:
            return
        definition_key = self.args.strip().partition(" ")[0]
        if not definition_key:
            self.caller.msg("用法：guild accept <definition_key>")
            return
        try:
            record = accept_guild_offer(self.caller, staff, definition_key)
        except (BoardAccessError, GuildOfferError) as error:
            self.caller.msg(f"無法接取任務：{error}")
            return
        self.caller.msg(f"你接取了任務 {record.quest_id}。")


class CmdGuildLog(_GuildCommandBase):
    """Show your quest log."""

    key = "guild log"
    aliases = ("guild 記錄", "任務記錄")

    def func(self) -> None:
        try:
            records = read_records(self.caller)
        except Exception as error:
            self.caller.msg(f"任務記錄有誤：{error}")
            return
        if not records:
            self.caller.msg("你的任務記錄是空的。")
            return
        lines = ["任務記錄："]
        for record in records:
            lines.append(
                f"  {record.quest_id} [{record.state.value}] "
                f"階段 {record.stage_index + 1}"
            )
        lines.append("用 guild show <quest_id> 查看任務詳情。")
        self.caller.msg("\n".join(lines))


class CmdGuildShow(_GuildCommandBase):
    """Show full detail for one of your quests."""

    key = "guild show"
    aliases = ("guild 詳情", "guild detail", "任務詳情")

    def func(self) -> None:
        quest_id = self.args.strip().partition(" ")[0]
        if not quest_id:
            self.caller.msg("用法：guild show <quest_id>")
            return
        try:
            records = read_records(self.caller)
            record = find_record(records, quest_id)
            if record is None:
                raise QuestNotFound(quest_id)
            definition = definition_for(record)
            offer = self._resolve_offer(definition.key)
        except QuestNotFound:
            self.caller.msg("找不到這個任務。")
            return
        except (QuestDataError, GuildDataError) as error:
            self.caller.msg(f"無法顯示任務詳情：{error}")
            return
        detail = describe_quest_detail(
            record,
            definition,
            offer,
            get_world_clock().tick,
        )
        self.caller.msg(detail)

    def _resolve_offer(self, definition_key: str):
        """Return the branch offer for ``definition_key`` or ``None``.

        An unregistered player sees no reward section; a malformed
        ``guild_registration`` raises ``GuildDataError`` (caught by the
        caller); a missing offer for the player's branch is never an error.
        """
        registration = parse_guild_registration(self.caller)
        if registration is None:
            return None
        try:
            return get_guild_offer(definition_key, registration["branch_key"])
        except GuildOfferNotFound:
            return None


class CmdGuildAbandon(_GuildCommandBase):
    """Abandon an active guild quest."""

    key = "guild abandon"
    aliases = ("guild 放棄", "放棄任務")

    def func(self) -> None:
        staff = self.resolve_staff()
        if staff is None:
            return
        quest_id = self.args.strip().partition(" ")[0]
        if not quest_id:
            self.caller.msg("用法：guild abandon <quest_id>")
            return
        try:
            record = abandon_guild_quest(self.caller, staff, quest_id)
        except QuestNotFound:
            self.caller.msg("找不到這個任務。")
            return
        self.caller.msg(f"你放棄了任務 {record.quest_id}。")


class CmdGuildTurnIn(_GuildCommandBase):
    """Turn in a completed quest and claim its reward once."""

    key = "guild turnin"
    aliases = ("guild 回報", "回報任務", "guild turn-in")

    def func(self) -> None:
        staff = self.resolve_staff()
        if staff is None:
            return
        quest_id = self.args.strip().partition(" ")[0]
        if not quest_id:
            self.caller.msg("用法：guild turnin <quest_id>")
            return
        try:
            result = turn_in_quest(self.caller, staff, quest_id)
        except (RewardClaimError, GuildDataError) as error:
            self.caller.msg(f"無法回報任務：{error}")
            return
        self.caller.msg(
            f"你回報了任務 {result['quest_id']}，獲得 {result['copper']} 銅、"
            f"功績 {result['merit']} 與道具 {result['items']}。"
        )
        if result.get("onboarding_completed"):
            self.caller.msg(
                "你的第一個日子在這裡圓滿結束。冒險者，歡迎正式踏入伊洛瑟恩大陸。"
            )


class CmdGuildMerit(_GuildCommandBase):
    """Show your guild rank and cumulative merit."""

    key = "guild merit"
    aliases = ("guild 功績", "公會階級")

    def func(self) -> None:
        from world.lore.guild import GUILD_RANK_REGISTRY

        rank = self.caller.guild_rank
        if rank is None:
            self.caller.msg("你尚未註冊為冒險者。")
            return
        merit = read_counter_trait(self.caller, "guild_merit")
        threshold = get_catalog().merit_thresholds
        next_rank = next(
            (r for r in GUILD_RANK_REGISTRY.values() if r.order == GUILD_RANK_REGISTRY[rank].order + 1),
            None,
        )
        if next_rank is None:
            self.caller.msg(f"你的階級是 {rank}，累計功績 {merit}。")
            return
        self.caller.msg(
            f"你的階級是 {rank}，累計功績 {merit} / {threshold[next_rank.key]} "
            f"(升階 {next_rank.key})。"
        )