"""One offline authoring-map image, published atomically by one invocation.

The command validates a capture request, reads the workspace once through
:func:`elosern_map_editor.capture_snapshot.load_capture_snapshot`, renders the
local map-only page in a disposable headless browser, encodes the exact map
rectangle losslessly with Pillow and replaces the destination only after the
complete image and the success document exist in memory.

Nothing here starts the editor service, talks to a network, writes authored
data or touches the partition job. ``--view``/``--bounds`` coordinate frames,
the layer vocabulary and the output rules are documented once in the
``map-data-authoring`` skill; this module is the implementation of that
contract, and ``.agents/skills/map-data-authoring/scripts/capture_map.py`` is
its thin entry point.

Exit status 0 means one image was produced. It never means the map is
game-ready and never stands in for reading the image.
"""

from __future__ import annotations

import argparse
import io
import json
import math
import os
import secrets
import sys
from collections.abc import Callable, Iterable, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .capture_snapshot import CaptureSnapshotError, load_capture_snapshot

#: The three authoring views a capture may select.
VIEWS = ("continent", "settlement", "interior")
#: Default and accepted lossless output formats.
DEFAULT_FORMAT = "webp"
FORMATS = ("webp", "png")
#: Default output size in pixels.
DEFAULT_WIDTH = 1280
DEFAULT_HEIGHT = 960
#: Every layer each view paints; all of them are visible unless hidden.
LAYERS: dict[str, tuple[str, ...]] = {
    "continent": ("terrain", "water", "ridge", "locations", "footprint", "partition", "labels"),
    "settlement": ("nodes", "roads", "labels"),
    "interior": ("rooms", "connections", "exterior", "labels"),
}
#: The map-only page produced by ``pnpm --dir tools/map-editor/frontend run
#: build:capture``; it loads from the filesystem with no server.
ENTRY_PATH = Path(__file__).resolve().parent.parent / "frontend" / "capture-dist" / "index.html"
#: The host element the entry sizes to the requested pixel frame.
STAGE_SELECTOR = "[data-capture-stage]"
#: Bound on fonts, terrain decode, layout and paint before the render is
#: refused. It covers readiness only; it is not a fixed sleep.
RENDER_DEADLINE_MS = 20_000
#: Bound on the page load and the element screenshot, in milliseconds.
ACTION_TIMEOUT_MS = 30_000

SETUP_GUIDANCE = (
    "prepare the locked capture environment: "
    "uv sync --locked --project tools/map-editor --group capture && "
    "uv run --locked --project tools/map-editor --group capture playwright install chromium"
)
BUILD_GUIDANCE = (
    "build the local capture page: "
    "pnpm --dir tools/map-editor/frontend install --frozen-lockfile && "
    "pnpm --dir tools/map-editor/frontend run build:capture"
)

#: Evaluate the entry's render promise under a finite deadline. A readiness
#: that never arrives rejects like any other entry error, so no image is
#: captured from a partially painted map. The payload is structured data, never
#: interpolated into executable source.
RENDER_SCRIPT = """
async (request) => {
  const { deadline, ...payload } = request;
  if (typeof window.renderMapCapture !== "function") {
    throw new Error("capture: window.renderMapCapture is missing from the local entry");
  }
  let timer;
  const expired = new Promise((_resolve, reject) => {
    timer = setTimeout(
      () => reject(new Error(`capture: the map was not ready within ${deadline} ms`)),
      deadline,
    );
  });
  try {
    return await Promise.race([window.renderMapCapture(payload), expired]);
  } finally {
    clearTimeout(timer);
  }
}
"""


class CaptureError(Exception):
    """One refused capture; ``code`` is the stable machine reason.

    ``guidance`` holds the one action that recovers, when there is one, and
    ``diagnostics`` the structured source diagnostics of a refused load.
    """

    def __init__(
        self,
        code: str,
        message: str,
        *,
        guidance: str | None = None,
        diagnostics: Iterable[dict[str, Any]] = (),
        exit_code: int = 1,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.guidance = guidance
        self.diagnostics = tuple(diagnostics)
        self.exit_code = exit_code

    def as_dict(self) -> dict[str, Any]:
        return {
            "code": self.code,
            "message": self.message,
            "guidance": self.guidance,
            "diagnostics": list(self.diagnostics),
        }


class _Parser(argparse.ArgumentParser):
    """``argparse`` that refuses with :class:`CaptureError` instead of exiting."""

    def error(self, message: str) -> None:  # type: ignore[override]
        raise CaptureError("invalid_argument", message, exit_code=2)


@dataclass(frozen=True)
class CaptureRequest:
    """One validated capture invocation."""

    view: str
    map_id: str | None
    bounds: tuple[float, float, float, float] | None
    width: int
    height: int
    hidden_layers: tuple[str, ...]
    format: str
    output: Path


def _parser() -> _Parser:
    parser = _Parser(
        prog="capture_map.py",
        description="Capture one authored map view as a lossless image.",
        allow_abbrev=False,
    )
    parser.add_argument("--view", required=True, choices=VIEWS)
    parser.add_argument("--map", dest="map_id", default=None, metavar="MAP_ID")
    parser.add_argument(
        "--bounds",
        nargs=4,
        type=float,
        default=None,
        metavar=("MIN_X", "MIN_Y", "MAX_X", "MAX_Y"),
    )
    parser.add_argument("--width", type=int, default=DEFAULT_WIDTH)
    parser.add_argument("--height", type=int, default=DEFAULT_HEIGHT)
    parser.add_argument(
        "--hide",
        action="extend",
        nargs="+",
        default=[],
        metavar="LAYER",
        help="layer to leave out; repeatable, all applicable layers are visible by default",
    )
    parser.add_argument("--format", choices=FORMATS, default=DEFAULT_FORMAT)
    parser.add_argument("--output", required=True, metavar="PATH")
    return parser


def _normalised_layers(view: str, requested: Iterable[str]) -> tuple[str, ...]:
    """The hidden layers of one view, sorted and de-duplicated.

    Unknown names and layers of another view are refused: the vocabulary is
    per view, and a silently ignored name would hide nothing.
    """

    applicable = LAYERS[view]
    names = tuple(requested)
    unknown = sorted(set(names) - set(applicable))
    if unknown:
        raise CaptureError(
            "unknown_layer",
            f"--hide names {', '.join(unknown)}; {view} layers are {', '.join(applicable)}",
            exit_code=2,
        )
    return tuple(sorted(set(names)))


def _validated_bounds(values: Sequence[float] | None) -> tuple[float, float, float, float] | None:
    if values is None:
        return None
    bounds = tuple(float(value) for value in values)
    if len(bounds) != 4 or not all(math.isfinite(value) for value in bounds):
        raise CaptureError(
            "invalid_argument", "--bounds needs four finite numbers", exit_code=2
        )
    min_x, min_y, max_x, max_y = bounds
    if not (max_x > min_x and max_y > min_y):
        raise CaptureError(
            "invalid_argument",
            "--bounds needs strictly increasing axes: MIN_X < MAX_X and MIN_Y < MAX_Y",
            exit_code=2,
        )
    return bounds  # type: ignore[return-value]


def _positive(value: int, name: str) -> int:
    if value <= 0:
        raise CaptureError(
            "invalid_argument", f"--{name} must be a positive integer pixel count", exit_code=2
        )
    return value


def _output_path(raw: str, image_format: str) -> Path:
    """The destination, resolved relative to the working directory.

    The parent directory must already exist; the suffix must spell the selected
    format. The final component is never resolved, so replacing a symlink
    replaces the link, not a different file elsewhere.
    """

    target = Path(raw)
    absolute = target if target.is_absolute() else Path.cwd() / target
    if not absolute.name or absolute.name in {".", ".."}:
        raise CaptureError("invalid_output", "--output needs a file name", exit_code=2)
    parent = absolute.parent.resolve()
    if not parent.is_dir():
        raise CaptureError(
            "invalid_output",
            f"--output directory does not exist: {parent}",
            exit_code=2,
        )
    destination = parent / absolute.name
    if destination.is_dir():
        raise CaptureError(
            "invalid_output", f"--output is a directory: {destination}", exit_code=2
        )
    if destination.suffix.lower() != f".{image_format}":
        raise CaptureError(
            "invalid_output",
            f"--output suffix must be .{image_format} for --format {image_format}",
            exit_code=2,
        )
    return destination


def parse_request(argv: Sequence[str]) -> CaptureRequest:
    """Parse and validate one invocation; raise :class:`CaptureError` otherwise."""

    arguments = _parser().parse_args(list(argv))
    view = arguments.view
    map_id = arguments.map_id
    if view == "continent":
        if map_id is not None:
            raise CaptureError(
                "invalid_argument",
                "the continent takes no --map; omit it or select a settlement/interior view",
                exit_code=2,
            )
    elif map_id is None:
        raise CaptureError(
            "invalid_argument",
            f"--view {view} needs --map with an authored document ID",
            exit_code=2,
        )
    bounds = _validated_bounds(arguments.bounds)
    width = _positive(arguments.width, "width")
    height = _positive(arguments.height, "height")
    hidden = _normalised_layers(view, arguments.hide)
    return CaptureRequest(
        view=view,
        map_id=map_id,
        bounds=bounds,
        width=width,
        height=height,
        hidden_layers=hidden,
        format=arguments.format,
        output=_output_path(arguments.output, arguments.format),
    )


def _require_runtime(entry: Path) -> Callable[[], Any]:
    """Import the capture dependencies; refuse with the setup action instead.

    Imports stay inside this function so the rest of the editor package works
    without the optional ``capture`` dependency group.
    """

    if not entry.is_file():
        raise CaptureError(
            "build_missing", f"the local capture page is not built: {entry}", guidance=BUILD_GUIDANCE
        )
    try:
        from PIL import features
    except ModuleNotFoundError as error:  # pragma: no cover - exercised by refusing
        raise CaptureError(
            "runtime_missing", f"Pillow is not installed in this environment ({error})", guidance=SETUP_GUIDANCE
        ) from error
    if not features.check("webp"):
        raise CaptureError(
            "codec_missing",
            "this Pillow has no WebP encoder support",
            guidance=SETUP_GUIDANCE,
        )
    try:
        from playwright.sync_api import sync_playwright
    except ModuleNotFoundError as error:  # pragma: no cover - exercised by refusing
        raise CaptureError(
            "runtime_missing",
            f"Playwright is not installed in this environment ({error})",
            guidance=SETUP_GUIDANCE,
        ) from error
    return sync_playwright


def _render(
    entry: Path,
    payload: dict[str, Any],
    *,
    width: int,
    height: int,
    deadline_ms: int = RENDER_DEADLINE_MS,
    playwright_factory: Callable[[], Any] | None = None,
) -> tuple[dict[str, Any], bytes]:
    """Draw one request in a disposable browser and return its PNG pixels.

    The browser, its context and its page are closed on every path, including a
    refused render. A page that attempts any network request is refused: the
    entry is a local file and its assets are files beside it.
    """

    if playwright_factory is None:
        from playwright.sync_api import sync_playwright as playwright_factory  # type: ignore[no-redef]
    playwright = playwright_factory().start()
    browser = context = page = None
    attempted: list[str] = []
    sockets: list[str] = []
    try:
        browser = playwright.chromium.launch(headless=True)
        context = browser.new_context(
            viewport={"width": width, "height": height},
            device_scale_factor=1,
            service_workers="block",
        )

        def deny(route) -> None:
            attempted.append(route.request.url)
            route.abort()

        # A predicate rather than a glob: every scheme the page might reach for
        # is refused and recorded, so an attempted network use fails the
        # capture instead of silently painting a partial map.
        context.route(lambda url: url.split(":", 1)[0] in {"http", "https"}, deny)

        # A WebSocket is not an HTTP route. The routed socket is never
        # connected to its server counterpart, so no traffic can leave; the
        # handler only records the attempt (closing it here would deadlock the
        # sync dispatcher that is running the handler).
        def deny_socket(web_socket) -> None:
            sockets.append(web_socket.url)

        context.route_web_socket(lambda _url: True, deny_socket)
        page = context.new_page()
        page.set_default_timeout(ACTION_TIMEOUT_MS)
        page.set_default_navigation_timeout(ACTION_TIMEOUT_MS)
        result: Any = None
        shot: bytes | None = None
        failure: Exception | None = None
        try:
            page.goto(entry.as_uri(), wait_until="load")
            request = {
                "world": payload["world"],
                "partition": payload["partition"],
                "view": payload["view"],
                "map_id": payload["map_id"],
                "width": payload["width"],
                "height": payload["height"],
                "bounds": payload["bounds"],
                "hidden_layers": payload["hidden_layers"],
                "deadline": deadline_ms,
            }
            result = page.evaluate(RENDER_SCRIPT, request)
            shot = page.locator(STAGE_SELECTOR).screenshot(
                type="png", animations="disabled", caret="hide"
            )
        except Exception as error:  # noqa: BLE001 - every browser failure is a refusal
            failure = error
        # An attempted network use is the more specific refusal: the page was
        # not allowed to fetch what it wanted, so whatever it painted is not
        # the map's own assets.
        if attempted or sockets:
            raise CaptureError(
                "network_attempted",
                "the capture page tried to use the network: "
                + ", ".join(sorted(set(attempted + sockets))),
                guidance=BUILD_GUIDANCE,
            )
        if failure is not None:
            message = _browser_message(failure)
            raise CaptureError(
                "render_failed", message, guidance=_render_guidance(entry, message)
            ) from failure
        if result is None or shot is None:  # pragma: no cover - defensive
            raise CaptureError("render_failed", "the capture page produced no image")
        return result, shot
    finally:
        for close in (
            lambda: page and page.close(),
            lambda: context and context.close(),
            lambda: browser and browser.close(),
            playwright.stop,
        ):
            try:
                close()
            except Exception:  # noqa: BLE001 - teardown must reach every later step
                pass


def _browser_message(error: Exception) -> str:
    """The first useful line of a browser-side failure."""

    text = str(error).strip()
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    return lines[0] if lines else error.__class__.__name__


def _render_guidance(entry: Path, message: str) -> str | None:
    if not entry.is_file():
        return BUILD_GUIDANCE
    if "Executable doesn't exist" in message or "playwright install" in message:
        return "run `playwright install chromium` in the map-editor environment, then retry"
    return None


def _encode_image(png: bytes, image_format: str, *, width: int, height: int) -> bytes:
    """Encode the captured pixels losslessly in the selected format.

    Pillow failures (an undecodable screenshot, a format limit, a full disk)
    stay inside the command's own refusal contract instead of escaping as a
    traceback.
    """

    from PIL import Image

    try:
        with Image.open(io.BytesIO(png)) as shot:
            shot.load()
            if shot.size != (width, height):
                raise CaptureError(
                    "render_contract",
                    f"the browser produced {shot.size[0]}x{shot.size[1]} pixels, not {width}x{height}",
                )
            pixels = shot.convert("RGB")
            buffer = io.BytesIO()
            if image_format == "webp":
                pixels.save(buffer, format="WEBP", lossless=True, quality=100, method=6)
            else:
                pixels.save(buffer, format="PNG", optimize=True)
            encoded = buffer.getvalue()
    except CaptureError:
        raise
    except (OSError, ValueError) as error:
        raise CaptureError(
            "encode_failed", f"the {image_format} encoder failed: {error}"
        ) from error
    if not encoded:
        raise CaptureError("encode_failed", "the encoder produced no image bytes")
    return encoded


def _publish(encoded: bytes, destination: Path) -> None:
    """Replace ``destination`` with ``encoded`` through a same-directory stage.

    The destination is never opened for writing, so a failure anywhere before
    the replacement leaves an existing image byte-identical. The stage file is
    removed on every path.
    """

    stage = destination.parent / f".{destination.name}.{os.getpid()}.{secrets.token_hex(4)}.tmp"
    try:
        with open(stage, "xb") as handle:
            handle.write(encoded)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(stage, destination)
    except OSError as error:
        raise CaptureError(
            "output_failed", f"cannot publish {destination}: {error}"
        ) from error
    finally:
        try:
            stage.unlink()
        except FileNotFoundError:
            pass
        except OSError:
            pass


def capture(
    request: CaptureRequest,
    *,
    root: Path | None = None,
    entry: Path | None = None,
    playwright_factory: Callable[[], Any] | None = None,
    deadline_ms: int = RENDER_DEADLINE_MS,
) -> dict[str, Any]:
    """Run one capture and publish its image; return the success document.

    The success document is serialized before the destination is replaced, so
    a document that cannot be serialized never follows a published image.
    Replacement is the last operation that can fail before reporting; if
    writing the already-serialized document to stdout fails afterwards, the
    image exists and the refusal says so (``report_failed``) instead of
    pretending the image was not published. Any earlier refusal raises
    :class:`CaptureError` with no image published.
    """

    page = entry if entry is not None else ENTRY_PATH
    playwright_factory = playwright_factory or _require_runtime(page)
    workspace = (root if root is not None else Path.cwd()).resolve()
    try:
        snapshot = load_capture_snapshot(
            workspace,
            view=request.view,
            map_id=request.map_id,
            hidden_layers=request.hidden_layers,
        )
    except CaptureSnapshotError as error:
        detail = f"{error.message} ({error.reason})" if error.reason else error.message
        raise CaptureError(
            error.code,
            detail,
            guidance=error.guidance,
            diagnostics=error.diagnostics,
        ) from error
    payload = {
        "world": snapshot["world"],
        "partition": snapshot["partition"],
        "view": request.view,
        "map_id": request.map_id,
        "width": request.width,
        "height": request.height,
        "bounds": list(request.bounds) if request.bounds else None,
        "hidden_layers": list(request.hidden_layers),
    }
    try:
        rendered, shot = _render(
            page,
            payload,
            width=request.width,
            height=request.height,
            deadline_ms=deadline_ms,
            playwright_factory=playwright_factory,
        )
    except CaptureError:
        raise
    except Exception as error:  # noqa: BLE001 - launch failures carry setup guidance
        raise CaptureError(
            "browser_unavailable",
            f"the headless browser could not run: {_browser_message(error)}",
            guidance=SETUP_GUIDANCE,
        ) from error
    bounds, units, axes = _read_result(rendered)
    encoded = _encode_image(shot, request.format, width=request.width, height=request.height)
    document = {
        "image_path": str(request.output),
        "view": request.view,
        "map_id": request.map_id,
        "format": request.format,
        "width": request.width,
        "height": request.height,
        "bounds": bounds,
        "units": units,
        "axes": axes,
        "hidden_layers": list(request.hidden_layers),
        "diagnostics": snapshot["diagnostics"],
    }
    # ASCII-safe JSON: a non-UTF-8 stdout can then never fail after the
    # destination has already been replaced.
    text = json.dumps(document) + "\n"
    _publish(encoded, request.output)
    try:
        sys.stdout.write(text)
        sys.stdout.flush()
    except OSError as error:
        raise CaptureError(
            "report_failed",
            f"the image was published to {request.output}, but the success object "
            f"could not be written: {error}",
        ) from error
    return document


def _read_result(rendered: Any) -> tuple[list[float | int], str, dict[str, str]]:
    """The entry's camera result, checked for the agreed shape."""

    if not isinstance(rendered, dict):
        raise CaptureError("render_contract", "the capture page reported no camera result")
    raw_bounds = rendered.get("bounds")
    if (
        not isinstance(raw_bounds, (list, tuple))
        or len(raw_bounds) != 4
        or not all(isinstance(value, (int, float)) for value in raw_bounds)
    ):
        raise CaptureError(
            "render_contract", f"the capture page reported malformed bounds: {raw_bounds!r}"
        )
    bounds = [
        int(value) if float(value).is_integer() else float(value) for value in raw_bounds
    ]
    units = rendered.get("units")
    axes = rendered.get("axes")
    if not isinstance(units, str) or not isinstance(axes, dict):
        raise CaptureError(
            "render_contract", "the capture page reported no units or axes for the camera"
        )
    if set(axes) != {"x", "y"} or not all(isinstance(value, str) for value in axes.values()):
        raise CaptureError(
            "render_contract", f"the capture page reported malformed axes: {axes!r}"
        )
    return bounds, units, {str(key): str(value) for key, value in axes.items()}


def _report(error: CaptureError) -> None:
    """Write one short diagnosis; a failing stderr must not raise from here."""

    lines = [f"capture: {error.code}: {error.message}"]
    for diagnostic in error.diagnostics[:10]:
        where = diagnostic.get("relative_path") or "?"
        if diagnostic.get("line"):
            where = f"{where}:{diagnostic['line']}"
        lines.append(
            f"  [{diagnostic.get('category')}/{diagnostic.get('code')}] {where}"
            f" {diagnostic.get('field_path') or ''} - {diagnostic.get('message')}"
        )
    if error.guidance:
        lines.append(f"  {error.guidance}")
    try:
        print("\n".join(lines), file=sys.stderr, flush=True)
    except OSError:
        pass


def main(argv: Sequence[str] | None = None) -> int:
    """The command entry point: one image, one success object, or a refusal."""

    try:
        capture(parse_request(sys.argv[1:] if argv is None else argv))
    except CaptureError as error:
        _report(error)
        return error.exit_code
    except Exception as error:  # noqa: BLE001 - never a traceback or a stray success object
        _report(CaptureError("internal", f"{error.__class__.__name__}: {error}"))
        return 1
    return 0


__all__ = [
    "CaptureError",
    "CaptureRequest",
    "DEFAULT_FORMAT",
    "DEFAULT_HEIGHT",
    "DEFAULT_WIDTH",
    "ENTRY_PATH",
    "FORMATS",
    "LAYERS",
    "VIEWS",
    "capture",
    "main",
    "parse_request",
]
