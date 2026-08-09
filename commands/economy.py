"""Player-facing shop stock, buy, and sell commands."""

from evennia import Command

from typeclasses.components import Merchant
from world.rules.economy import (
    TradeError,
    TradeReason,
    buy,
    parse_merchant_stock,
    sell,
    shop_is_open,
)
from world.rules.guild_config import get_catalog
from world.lore.items import ITEM_REGISTRY
from world.rules.npc_schedules import interaction_reason
from world.skills.equipment import list_items


class _ShopCommandBase(Command):
    locks = "cmd:all()"
    help_category = "Economy"

    def resolve_merchant(self):
        try:
            from world.rules.guild import resolve_local_service_host

            return resolve_local_service_host(self.caller, Merchant)
        except Exception:
            self.caller.msg("這裡沒有商人。")
            return None


class CmdShopStock(_ShopCommandBase):
    """List the merchant's current stock."""

    key = "shop stock"
    aliases = ("shop 庫存", "商店庫存")

    def func(self) -> None:
        merchant_host = self.resolve_merchant()
        if merchant_host is None:
            return
        merchant = merchant_host.components.get(Merchant.get_component_slot())
        shop_key = merchant.shop_key
        config = get_catalog().shop_configs.get(shop_key)
        if config is None:
            self.caller.msg("這間商店沒有設定。")
            return
        open_now = shop_is_open(shop_key)
        try:
            stock = parse_merchant_stock(merchant)
        except TradeError as error:
            self.caller.msg(f"商店資料有誤：{error}")
            return
        lines = [f"商店（{'營業中' if open_now else '休息中'}）："]
        for offer in config.offers:
            definition = ITEM_REGISTRY[offer.item_key]
            lines.append(
                f"  {offer.item_key} — {definition.display_name_zh} "
                f"買 {offer.buy_copper} / 賣 {offer.sell_copper} "
                f"（庫存 {stock.get(offer.item_key, 0)}）"
            )
        self.caller.msg("\n".join(lines))


class CmdBuy(_ShopCommandBase):
    """Buy an item from the merchant."""

    key = "buy"
    aliases = ("購買", "shop buy")

    def func(self) -> None:
        merchant_host = self.resolve_merchant()
        if merchant_host is None:
            return
        reason = interaction_reason(merchant_host, "service_shop")
        if reason is not None:
            self.caller.msg(reason)
            return
        parts = self.args.strip().split()
        if not parts:
            self.caller.msg("用法：buy <item_key> [數量]")
            return
        item_key = parts[0]
        try:
            quantity = int(parts[1]) if len(parts) > 1 else 1
        except ValueError:
            self.caller.msg("數量必須是正整數。")
            return
        try:
            result = buy(self.caller, merchant_host, item_key, quantity)
        except TradeError as error:
            reason = error.args[0]
            message = {
                TradeReason.CLOSED: "商店目前沒有營業。",
                TradeReason.UNKNOWN_ITEM: "商店不賣這個物品。",
                TradeReason.NOT_OFFERED: "商店沒有這個商品。",
                TradeReason.INSUFFICIENT_FUNDS: "你的銅幣不足。",
                TradeReason.INSUFFICIENT_STOCK: "商店庫存不足。",
                TradeReason.BAD_QUANTITY: "數量必須是正整數。",
            }.get(reason, f"購買失敗：{error}")
            self.caller.msg(message)
            return
        self.caller.msg(
            f"你買了 {result['quantity']} 個 {result['item_key']}，"
            f"花費 {result['total_copper']} 銅，剩餘 {result['wallet']} 銅。"
        )


class CmdSell(_ShopCommandBase):
    """Sell a held item to the merchant."""

    key = "sell"
    aliases = ("販賣", "shop sell")

    def func(self) -> None:
        merchant_host = self.resolve_merchant()
        if merchant_host is None:
            return
        reason = interaction_reason(merchant_host, "service_shop")
        if reason is not None:
            self.caller.msg(reason)
            return
        parts = self.args.strip().split()
        if not parts:
            self.caller.msg("用法：sell <item_key> [數量]")
            return
        item_key = parts[0]
        try:
            quantity = int(parts[1]) if len(parts) > 1 else 1
        except ValueError:
            self.caller.msg("數量必須是正整數。")
            return
        try:
            result = sell(self.caller, merchant_host, item_key, quantity)
        except TradeError as error:
            reason = error.args[0]
            message = {
                TradeReason.CLOSED: "商店目前沒有營業。",
                TradeReason.UNKNOWN_ITEM: "商店不收這個物品。",
                TradeReason.UNSELLABLE: "這個物品無法販賣。",
                TradeReason.INSUFFICIENT_ITEMS: "你沒有足夠的這個物品。",
                TradeReason.STOCK_OVERFLOW: "商店收購上限已滿。",
                TradeReason.BAD_QUANTITY: "數量必須是正整數。",
            }.get(reason, f"販賣失敗：{error}")
            self.caller.msg(message)
            return
        self.caller.msg(
            f"你賣了 {result['quantity']} 個 {result['item_key']}，"
            f"獲得 {result['total_copper']} 銅，目前 {result['wallet']} 銅。"
        )


class CmdInventory(Command):
    """Show your inventory and wallet."""

    key = "inventory"
    aliases = ("背包", "inv")

    def func(self) -> None:
        items = list_items(self.caller)
        wallet = int(self.caller.db.wallet or 0)
        self.caller.msg(f"錢包：{wallet} 銅")
        if not items:
            self.caller.msg("背包是空的。")
            return
        from collections import Counter

        counts = Counter(items)
        self.caller.msg(
            "\n".join(
                f"  {item_key} ×{count}"
                for item_key, count in sorted(counts.items())
            )
        )