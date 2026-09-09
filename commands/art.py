"""Staff-only ``@art`` command family for the deterministic art backend.

Restricted to staff: ``@art status`` (list/filter records), ``@art run``
(drain now, non-blocking), ``@art retry`` (re-enqueue failed records),
``@art requeue <full-subject-key>`` (forced regeneration — gallery-bearing
kinds through the validated gallery seam, scene keys through the classic
record reset), ``@art
options <kind>`` (list the live server's selectable option names), and
``@art health`` (forced connectivity verdict + scheduler/queue/gallery/
output-policy dashboard). ``@art status`` additionally reports per-subject
gallery STATE through the gallery module's read-only accessors, and
``@art retry`` re-drives every subject whose last gallery generation
failed. Status and health output never include persona text, prompt
content, credentials, URL userinfo, absolute filesystem paths, or the store
root (design D8).
"""

import time
import urllib.parse

from django.conf import settings
from commands.command import Command

from world.art import gallery as gallery_api
from world.art import gallery_kinds
from world.art.queue import failed_keys, is_gallery_job, record_key, requeue
from world.art.store import ArtAssetRecord
from world.art.subjects import (
    ArtSubjectError,
    ArtSubjectKind,
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
    """列出美術資產記錄與圖庫狀態。用法：art status [scene|portrait|monster]"""

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
            # Gallery job records are invisible here: the staff surface keeps
            # reporting the classic subject queue only.
            if not is_gallery_job(record)
            and (kind is None or record.db.kind.startswith(kind))
        ]
        records.sort(key=lambda record: record.db_key)
        # Gallery STATE (change gallery-failure-visibility): one line per
        # gallery record from the gallery module's read-only state accessor —
        # never a query of the record class, never a gallery JOB row. The
        # same kind filter applies: gallery kinds serialize under the
        # ``portrait`` prefix, so a ``scene`` filter yields no gallery rows.
        gallery_rows = [
            state
            for state in gallery_api.gallery_states()
            if kind is None or state.subject.kind.value.startswith(kind)
        ]
        gallery_rows.sort(key=lambda state: state.subject.full())
        if not records and not gallery_rows:
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
        if records:
            lines.insert(0, "經典資產記錄:")
        if gallery_rows:
            now = time.time()
            lines.append("圖庫狀態:")
            for state in gallery_rows:
                error = ""
                if state.error_code is not None:
                    error_at = (
                        state.error_at if state.error_at is not None else now
                    )
                    age = max(0, int(now - error_at))
                    error = f" 錯誤:{state.error_code}({age}s)"
                lines.append(
                    f"  {state.subject.full()} "
                    f"卡片:{state.card_count} "
                    f"預設:{'是' if state.has_default else '否'}{error}"
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
    """重新排入失敗記錄並重試圖庫生成失敗的主體。用法：art retry"""

    key = "art retry"

    def func(self) -> None:
        if not self.is_accessible():
            self.caller.msg("你沒有權限使用 art 指令。")
            return
        keys = failed_keys()
        from world.art.queue import ensure

        from world.art.service import retry_gallery_subject

        reenqueued = 0
        for full_key in keys:
            try:
                subject = parse_subject(full_key)
            except ArtSubjectError:
                continue
            record = ArtAssetRecord.objects.filter(
                db_key=record_key(subject)
            ).first()
            description = record.db.source_description if record else ""
            ensure(subject, description)
            reenqueued += 1
        # Gallery arm: every subject whose LAST generation attempt failed is
        # re-driven through the same validated request seam the automatic
        # paths use, so every precondition still applies. A typed rejection
        # (no living entity, ineligible ages, an unresolvable subject)
        # skips that subject with no record change; the moot-error clear
        # lives in the seam itself (declined because cards arrived).
        gallery_requested = 0
        for state in gallery_api.erroring_subjects():
            try:
                requested = retry_gallery_subject(state.subject)
            except ArtSubjectError:
                continue
            if requested:
                gallery_requested += 1
        self.caller.msg(
            f"已重新排入 {reenqueued} 個失敗記錄，"
            f"並重新請求 {gallery_requested} 次圖庫生成。"
        )


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
        # Gallery-bearing kinds (change ``gallery-monster-generation``) are
        # force-regenerated through the kind-neutral gallery seam, which
        # re-checks the kind's declared preconditions and respects the
        # declared card cap. Only no-gallery kinds (scene) keep the classic
        # fixed-identity record reset.
        if gallery_kinds.has_gallery(subject.kind):
            from world.art.service import requeue_gallery_subject

            try:
                requeue_gallery_subject(subject)
            except ArtSubjectError as error:
                self.caller.msg(f"無法重新排入：{error}")
                return
            self.caller.msg(f"已將 {subject.full()} 重新排入佇列。")
            return
        try:
            scene_subject_for(subject.key)
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
                if is_gallery_job(record):
                    continue
                status = str(record.db.status)
                counts[status] = counts.get(status, 0) + 1
            lines.append(
                "queue: "
                + " ".join(
                    f"{status}={counts.get(status, 0)}"
                    for status in ("pending", "in_progress", "failed", "done")
                )
            )
            # Section 4 of five (change gallery-failure-visibility): exact
            # gallery counts from the module's read-only state accessor —
            # records, total valid cards, subjects carrying an error. Pure
            # read: nothing is created, cleared, or touched.
            states = gallery_api.gallery_states()
            lines.append(
                "gallery: "
                f"records={len(states)} "
                f"cards={sum(state.card_count for state in states)} "
                f"erroring={sum(1 for state in states if state.error_code is not None)}"
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
