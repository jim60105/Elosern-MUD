"""Player-facing landmark rite command (``rite``, alias ``儀式``).

The command is deliberately thin: ``world.rules.landmark_rites`` owns every
mechanic (site resolution, preflight, the atomic settlement, the stable refusal
codes), so listing and performing share the browser action's settlement exactly.
This module owns only the argument grammar and the presentation: the guardian
listing, the whole authored scene, and the one completion line — the same
renderings the ``explore.landmark_rite`` action returns, imported from
``web.webclient.actions.rite_actions`` so the two entry points cannot drift.

The command stores no browser presentation state: a text-client rite is visible
to a browser session as the experienced mark, never as a delivery.
"""

from __future__ import annotations

from typing import Any

from commands.command import Command

from web.webclient.actions.rite_actions import rite_completion_line, rite_scene_text
from world.rules.landmark_rite_record import LandmarkRiteRecordError, seen_option_keys
from world.rules.landmark_rites import (
    REFUSAL_MESSAGES,
    RiteRefused,
    perform_rite,
    record_owner_for,
    rite_site_for,
)
from world.rules.party_scope import PartyScopeError, resolve_member_token

#: The printed usage line (the command's only grammar).
USAGE = "用法：儀式 <選項> [隊友]"
#: The suffix one experienced option carries in the listing.
EXPERIENCED_SUFFIX = "　已體驗"


def _option_line(option: Any, seen: tuple[str, ...]) -> str:
    """One listing row: the authored label, its key and the experienced mark."""
    line = f"　{option.label_zh}（{option.key}）"
    return f"{line}{EXPERIENCED_SUFFIX}" if option.key in seen else line


class CmdRite(Command):
    """在地標前進行守護者傳授的儀式，或查看這裡能進行的儀式。"""

    key = "rite"
    aliases = ("儀式",)
    locks = "cmd:all()"
    help_category = "General"

    def _resolve_site(self) -> Any:
        """Return ``(record owner, rite site)``, or ``None`` after a refusal."""
        try:
            owner = record_owner_for(self.caller)
        except RiteRefused as error:
            # The record owner is the character whose rite record is written;
            # a caller without one has no rite to list or perform.
            self.caller.msg(error.message)
            return None
        site = rite_site_for(owner)
        if site is None:
            self.caller.msg(REFUSAL_MESSAGES["rite_no_landmark"])
            return None
        return owner, site

    def _show_listing(self, owner: Any, site: Any) -> None:
        """Print the guardian, its options and which were experienced."""
        try:
            seen = seen_option_keys(owner, site.district_key)
        except LandmarkRiteRecordError:
            self.caller.msg(REFUSAL_MESSAGES["rite_record_corrupt"])
            return
        archetype = site.archetype
        lines = [
            f"{site.landmark_name}・{archetype.guardian_name_zh}",
            archetype.guardian_form_zh,
        ]
        lines.extend(_option_line(option, seen) for option in archetype.options)
        lines.append(USAGE)
        self.caller.msg("\n".join(lines))

    def _option_for(self, site: Any, token: str) -> Any:
        """The authored option named by its exact key or exact label, or ``None``."""
        for option in site.archetype.options:
            if token in (option.key, option.label_zh):
                return option
        return None

    def _member_id(self, token: str) -> Any:
        """Resolve the named companion, or ``None`` after the shared refusal."""
        try:
            member = resolve_member_token(self.caller, token)
        except PartyScopeError:
            self.caller.msg(REFUSAL_MESSAGES["rite_member_unavailable"])
            return None
        return member.id

    def func(self) -> None:
        tokens = self.args.split()
        if len(tokens) > 2:
            self.caller.msg(USAGE)
            return
        resolved = self._resolve_site()
        if resolved is None:
            return
        owner, site = resolved
        if not tokens:
            self._show_listing(owner, site)
            return
        option = self._option_for(site, tokens[0])
        if option is None:
            self.caller.msg(REFUSAL_MESSAGES["rite_unknown_option"])
            return
        member_id = None
        if len(tokens) == 2:
            member_id = self._member_id(tokens[1])
            if member_id is None:
                return
        try:
            result = perform_rite(
                self.caller, option.key, member_id, operation_id=None
            )
        except RiteRefused as error:
            # The settlement's stable code carries its own player-facing line.
            self.caller.msg(error.message)
            return
        self.caller.msg(rite_scene_text(result))
        self.caller.msg(rite_completion_line(result))