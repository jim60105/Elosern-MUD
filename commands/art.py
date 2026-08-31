"""Staff-only ``@art`` command family for the deterministic art backend.

Restricted to staff: ``@art status`` (list/filter records), ``@art run``
(drain now, non-blocking), ``@art retry`` (re-enqueue failed records),
``@art requeue <full-subject-key>`` (forced regeneration), ``@art
options <kind>`` (list the live server's selectable option names), and
``@art health`` (forced connectivity verdict + scheduler/queue/output-policy
dashboard). Status and health output never include persona text, prompt
content, credentials, URL userinfo, absolute filesystem paths, or the store
root (design D8).
"""

from django.conf import settings
from evennia import Command
import urllib.parse

from world.art.adult import PortraitRejected
from world.art.queue import failed_keys, record_key, requeue
from world.art.store import ArtAssetRecord
from world.art.subjects import (
    ArtSubjectError,
    ArtSubjectKind,
    monster_subject_for,
    parse_subject,
    scene_subject_for,
)


class _ArtCommand(Command):
    """Base for the staff art command family."""

    locks = "cmd:perm(Developer)"
    help_category = "Admin"

    def is_accessible(self) -> bool:
        if self.caller is None:
            return False
        return bool(self.caller.check_permstring("Developer"))


def _kind_filter(subject_kind: str | None) -> str | None:
    if subject_kind is None or subject_kind == "all":
        return None
    if subject_kind == "scene":
        return ArtSubjectKind.SCENE.value
    if subject_kind in ("portrait", "character", "monster"):
        return "portrait"
    return None


class CmdArtStatus(_ArtCommand):
    """列出美術資產記錄。用法：art status [scene|portrait|monster]"""

    key = "art status"

    def func(self) -> None:
        if not self.is_accessible():
            self.caller.msg("你沒有權限使用 art 指令。")
            return
        args = self.args.strip().split()
        kind = _kind_filter(args[0] if args else None)
        if kind is None and args:
            self.caller.msg("用法：art status [scene|portrait|monster]")
            return
        records = [
            record
            for record in ArtAssetRecord.objects.all()
            if kind is None or record.db.kind.startswith(kind)
        ]
        records.sort(key=lambda record: record.db_key)
        if not records:
            self.caller.msg("沒有符合的美術資產記錄。")
            return
        lines = []
        for record in records:
            seed = record.db.seed
            lines.append(
                f"  {record.db_key.removeprefix('art:')} "
                f"[{record.db.status}] 次數:{record.db.attempt_count} "
                f"比例:{record.db.aspect_ratio or '-'} "
                f"錯誤:{record.db.last_error_code or '-'}"
                f"{' 提示詞變更' if record.db.hash_changed else ''}"
                f"{f' seed={seed}' if seed is not None else ''}"
            )
        self.caller.msg("\n".join(lines))


class CmdArtRun(_ArtCommand):
    """立即排空美術佇列。用法：art run [--limit N]"""

    key = "art run"

    def func(self) -> None:
        if not self.is_accessible():
            self.caller.msg("你沒有權限使用 art 指令。")
            return
        limit = settings.ART_SCHEDULER_LIMIT
        args = self.args.strip().split()
        if args:
            if args[0] == "--limit" and len(args) == 2:
                try:
                    limit = int(args[1])
                except ValueError:
                    self.caller.msg("--limit 需要整數。")
                    return
                if limit < 1:
                    self.caller.msg("--limit 必須至少為 1。")
                    return
            else:
                self.caller.msg("用法：art run [--limit N]")
                return
        from world.art.worker import drain

        try:
            dispatched = drain(limit)
        except Exception as error:  # noqa: BLE001 - bounded; named client errors settle records
            self.caller.msg(f"美術排空失敗：{error}")
            return
        self.caller.msg(f"已派送 {dispatched} 個美術工作。")
        self.caller.msg("美術工作在背景執行，不會阻擋遊戲。")


class CmdArtRetry(_ArtCommand):
    """重新排入所有失敗的美術記錄。用法：art retry"""

    key = "art retry"

    def func(self) -> None:
        if not self.is_accessible():
            self.caller.msg("你沒有權限使用 art 指令。")
            return
        keys = failed_keys()
        from world.art.queue import ensure

        from world.art.service import retry_character_portrait
        from world.art.subjects import ArtSubjectKind, description_for

        reenqueued = 0
        for full_key in keys:
            try:
                subject = parse_subject(full_key)
            except ArtSubjectError:
                continue
            if subject.kind is ArtSubjectKind.CHARACTER:
                try:
                    retry_character_portrait(subject.key)
                except (ArtSubjectError, PortraitRejected):
                    continue
                reenqueued += 1
                continue
            record = ArtAssetRecord.objects.filter(
                db_key=record_key(subject)
            ).first()
            description = record.db.source_description if record else ""
            ensure(subject, description)
            reenqueued += 1
        self.caller.msg(f"已重新排入 {reenqueued} 個失敗記錄。")


class CmdArtRequeue(_ArtCommand):
    """強制重新生成單一主體。用法：art requeue <full-subject-key>"""

    key = "art requeue"

    def func(self) -> None:
        if not self.is_accessible():
            self.caller.msg("你沒有權限使用 art 指令。")
            return
        parts = self.args.strip().split()
        if len(parts) != 1:
            self.caller.msg("用法：art requeue <full-subject-key>")
            return
        try:
            subject = parse_subject(parts[0])
        except ArtSubjectError as error:
            self.caller.msg(f"無效的 subject key：{error}")
            return
        if subject.kind is ArtSubjectKind.CHARACTER:
            from world.art.service import requeue_character_portrait

            try:
                requeue_character_portrait(subject.key)
            except (ArtSubjectError, PortraitRejected) as error:
                self.caller.msg(f"無法重新排入：{error}")
                return
            self.caller.msg(f"已將 {subject.full()} 重新排入佇列。")
            return
        try:
            if subject.kind is ArtSubjectKind.SCENE:
                scene_subject_for(subject.key)
            else:
                monster_subject_for(subject.key)
        except ArtSubjectError as error:
            self.caller.msg(f"無效的 subject key：{error}")
            return
        requeue(subject)
        self.caller.msg(f"已將 {subject.full()} 重新排入佇列。")


class CmdArtOptions(_ArtCommand):
    """列出 sd-webui 伺服器可選用的選項名稱。用法：art options <models|samplers|schedulers|styles|modules>"""

    key = "art options"

    # kind -> (display label, sd_worker list function suffix)
    KINDS = {
        "models": ("模型", "models"),
        "samplers": ("取樣器", "samplers"),
        "schedulers": ("排程器", "schedulers"),
        "styles": ("風格", "styles"),
        "modules": ("模組", "modules"),
    }

    def func(self) -> None:
        if not self.is_accessible():
            self.caller.msg("你沒有權限使用 art 指令。")
            return
        import world.art.sd_worker as sd_worker
        from twisted.internet import threads

        args = self.args.strip().split()
        if len(args) != 1 or args[0] not in self.KINDS:
            self.caller.msg("用法：art options <models|samplers|schedulers|styles|modules>")
            return
        kind = args[0]
        label, fn_name = self.KINDS[kind]
        host = urllib.parse.urlsplit(sd_worker._base_url()).hostname or "?"

        def _reply(names: list[str]) -> None:
            lines = [f"{label}（{len(names)} 項，來源 {host}）："]
            lines += [f"  {index}. {name[:256]}" for index, name in enumerate(names, start=1)]
            self.caller.msg("\n".join(lines))

        def _fail(error: object) -> None:
            value = getattr(error, "value", error)
            code = getattr(value, "code", None) or "sd_connection_error"
            self.caller.msg(f"無法取得 {label} 清單：{code}（伺服器未回應或回應超限）")

        # The enumeration is a synchronous blocking HTTP call; it must run on
        # a background Twisted thread, never the reactor thread. The reply is
        # sent from the deferred's callback (design D1, duck run-1 BLOCKER).
        deferred = threads.deferToThread(getattr(sd_worker, f"list_{fn_name}"))
        deferred.addCallback(_reply)
        deferred.addErrback(_fail)


class CmdArtHealth(_ArtCommand):
    """檢視 sd-webui 連線與美術管線狀態。用法：art health"""

    key = "art health"

    def func(self) -> None:
        if not self.is_accessible():
            self.caller.msg("你沒有權限使用 art 指令。")
            return
        from twisted.internet import threads

        from world.art import connectivity

        def _reply(result: connectivity.ProbeResult) -> None:
            lines = [self._server_line(result)]
            enabled = "enabled" if settings.ART_SCHEDULER_ENABLED else "disabled"
            lines.append(
                f"scheduler: {enabled} "
                f"interval={int(settings.ART_SCHEDULER_INTERVAL_SECONDS)}s "
                f"limit={int(settings.ART_SCHEDULER_LIMIT)}"
            )
            counts: dict[str, int] = {}
            for record in ArtAssetRecord.objects.all():
                status = str(record.db.status)
                counts[status] = counts.get(status, 0) + 1
            lines.append(
                "queue: "
                + " ".join(
                    f"{status}={counts.get(status, 0)}"
                    for status in ("pending", "in_progress", "failed", "done")
                )
            )
            metadata = "on" if settings.ART_SD_PRESERVE_GENERATION_METADATA else "off"
            lines.append(
                f"output: {settings.ART_SD_OUTPUT_FORMAT} "
                f"q={int(settings.ART_SD_OUTPUT_QUALITY)} metadata={metadata}"
            )
            self.caller.msg("\n".join(lines))

        # The probe is a blocking HTTP call; run it off-reactor like every
        # other art command seam (CmdArtOptions precedent). probe() never
        # raises, so the callback always receives a ProbeResult verdict.
        deferred = threads.deferToThread(connectivity.probe, force=True)
        deferred.addCallback(_reply)

    @staticmethod
    def _server_line(result) -> str:
        """The pinned reachability line (design D3)."""
        if result.from_cache:
            when = f"(checked {result.age_seconds:.1f}s ago)"
        else:
            when = "(checked just now)"
        if result.ok:
            return f"server: reachable {when}"
        return f"server: unreachable — {result.code} {when}"
