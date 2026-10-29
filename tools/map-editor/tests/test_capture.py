"""The capture command's own rules: arguments, staging and browser lifetime.

No authored repository data is read. Argument parsing, output staging and the
browser-lifetime ordering are exercised directly; the rendering tests open
small throwaway pages so a readiness that never arrives or a page that touches
the network is refused for the reason the runner promises. The tests that need
Pillow or Playwright skip when the optional ``capture`` dependency group is not
installed in the editor environment.
"""

from __future__ import annotations

import io
import json
import os
from pathlib import Path

import pytest

from elosern_map_editor import capture


def _arguments(**overrides) -> list[str]:
    values = {
        "view": "settlement",
        "map_id": "synthetic_town",
        "output": "map.webp",
    }
    values.update(overrides)
    arguments = ["--view", values.pop("view"), "--output", values.pop("output")]
    map_id = values.pop("map_id")
    if map_id is not None:
        arguments += ["--map", map_id]
    for key, value in values.items():
        flag = "--" + key.replace("_", "-")
        if value is None:
            continue
        if key == "hide":
            for group in value:
                arguments += [flag, *(group if isinstance(group, (list, tuple)) else [group])]
        elif key == "bounds":
            arguments += [flag, *(str(item) for item in value)]
        else:
            arguments += [flag, str(value)]
    return arguments


def _request(tmp_path, **overrides) -> capture.CaptureRequest:
    cwd = Path.cwd()
    os.chdir(tmp_path)
    try:
        return capture.parse_request(_arguments(**overrides))
    finally:
        os.chdir(cwd)


# -- argument contract --------------------------------------------------------


def test_defaults_match_the_documented_contract(tmp_path):
    request = _request(tmp_path)
    assert (request.view, request.map_id) == ("settlement", "synthetic_town")
    assert (request.width, request.height) == (1280, 960)
    assert (request.format, request.hidden_layers, request.bounds) == ("webp", (), None)
    assert request.output == (tmp_path / "map.webp").resolve()


def test_continent_takes_no_map_and_the_other_views_require_one(tmp_path):
    assert _request(tmp_path, view="continent", map_id=None).map_id is None
    with pytest.raises(capture.CaptureError) as raised:
        capture.parse_request(["--view", "continent", "--map", "synthetic_town", "--output", "a.webp"])
    assert raised.value.code == "invalid_argument"
    with pytest.raises(capture.CaptureError) as raised:
        capture.parse_request(["--view", "interior", "--output", "a.webp"])
    assert "--map" in raised.value.message


def test_hidden_layers_are_normalised_and_scoped_to_the_view(tmp_path):
    request = _request(tmp_path, hide=[["labels", "nodes"], ["labels"]])
    assert request.hidden_layers == ("labels", "nodes")
    for view, hidden in (("settlement", "rooms"), ("interior", "roads"), ("continent", "roofs")):
        with pytest.raises(capture.CaptureError) as raised:
            _request(
                tmp_path,
                view=view,
                map_id=None if view == "continent" else "synthetic_town",
                hide=[[hidden]],
            )
        assert raised.value.code == "unknown_layer", view
        assert hidden in raised.value.message


def test_show_and_unknown_flags_are_refused(tmp_path):
    for extra in (["--show", "nodes"], ["--quality", "90"], ["--service-url", "http://x"], ["--wid", "10"]):
        with pytest.raises(capture.CaptureError) as raised:
            capture.parse_request(
                ["--view", "settlement", "--map", "synthetic_town", "--output", "a.webp", *extra]
            )
        assert raised.value.code == "invalid_argument"
        assert raised.value.exit_code == 2


def test_bounds_must_be_finite_and_strictly_increasing(tmp_path):
    for bounds in ((0, 0, 10, 10), (-5.5, 1.25, 5.5, 20)):
        assert _request(tmp_path, bounds=bounds).bounds == tuple(float(item) for item in bounds)
    for bounds in ((0, 0, 0, 10), (0, 0, 10, -1), (float("nan"), 0, 10, 10), (0, float("inf"), 10, 10)):
        with pytest.raises(capture.CaptureError) as raised:
            capture.parse_request(
                ["--view", "settlement", "--map", "synthetic_town", "--output", "a.webp"]
                + ["--bounds", *(str(item) for item in bounds)]
            )
        assert raised.value.code == "invalid_argument"


def test_pixel_dimensions_must_be_positive_integers(tmp_path):
    for width, height in ((1920, 1080), (1, 1)):
        request = _request(tmp_path, width=width, height=height)
        assert (request.width, request.height) == (width, height)
    for width, height in ((0, 960), (-1, 960), (1280, 0)):
        with pytest.raises(capture.CaptureError) as raised:
            _request(tmp_path, width=width, height=height)
        assert raised.value.code == "invalid_argument"
    with pytest.raises(capture.CaptureError):
        capture.parse_request(
            ["--view", "settlement", "--map", "synthetic_town", "--output", "a.webp", "--width", "12.5"]
        )


def test_format_selects_the_matching_suffix(tmp_path):
    assert _request(tmp_path, format="png", output="map.png").format == "png"
    assert _request(tmp_path, format="png", output="MAP.PNG").output.suffix == ".PNG"
    for image_format, output in (("webp", "map.png"), ("png", "map.webp"), ("jpeg", "map.jpeg")):
        with pytest.raises(capture.CaptureError) as raised:
            _request(tmp_path, format=image_format, output=output)
        assert raised.value.code in {"invalid_argument", "invalid_output"}
    with pytest.raises(capture.CaptureError) as raised:
        _request(tmp_path, output="map")
    assert raised.value.code == "invalid_output"


def test_output_parent_must_exist_and_not_be_a_directory(tmp_path):
    with pytest.raises(capture.CaptureError) as raised:
        _request(tmp_path, output=str(tmp_path / "missing" / "map.webp"))
    assert raised.value.code == "invalid_output"
    (tmp_path / "folder.webp").mkdir()
    with pytest.raises(capture.CaptureError) as raised:
        _request(tmp_path, output="folder.webp")
    assert raised.value.code == "invalid_output"


# -- output staging -----------------------------------------------------------


def _existing_image(path: Path) -> bytes:
    payload = b"an earlier image that must survive every failure"
    path.write_bytes(payload)
    return payload


def test_publication_replaces_and_leaves_no_stage_file(tmp_path):
    destination = tmp_path / "map.webp"
    _existing_image(destination)

    capture._publish(b"complete encoded image", destination)

    assert destination.read_bytes() == b"complete encoded image"
    assert [path.name for path in tmp_path.iterdir()] == ["map.webp"]


def test_a_replace_failure_keeps_the_previous_image(tmp_path, monkeypatch):
    destination = tmp_path / "map.webp"
    previous = _existing_image(destination)

    def refuse(_stage, _destination):
        raise OSError("the destination is on a read-only mount")

    monkeypatch.setattr(capture.os, "replace", refuse)
    with pytest.raises(capture.CaptureError) as raised:
        capture._publish(b"a new complete image", destination)

    assert raised.value.code == "output_failed"
    assert destination.read_bytes() == previous
    assert [path.name for path in tmp_path.iterdir()] == ["map.webp"]


def test_a_write_failure_keeps_the_previous_image(tmp_path, monkeypatch):
    destination = tmp_path / "map.webp"
    previous = _existing_image(destination)

    def refuse(_file_descriptor):
        raise OSError("no space left on device")

    monkeypatch.setattr(capture.os, "fsync", refuse)
    with pytest.raises(capture.CaptureError) as raised:
        capture._publish(b"a new complete image", destination)

    assert raised.value.code == "output_failed"
    assert destination.read_bytes() == previous
    assert [path.name for path in tmp_path.iterdir()] == ["map.webp"]


# -- browser lifetime ---------------------------------------------------------


class _FakePage:
    def __init__(self, events: list[str], outcome) -> None:
        self.events = events
        self._outcome = outcome

    def set_default_timeout(self, _value):
        self.events.append("timeout:action")

    def set_default_navigation_timeout(self, _value):
        self.events.append("timeout:navigation")

    def on(self, event, _handler):
        self.events.append(f"on:{event}")

    def goto(self, _url, wait_until=None):
        self.events.append(f"goto:{wait_until}")

    def evaluate(self, _script, request):
        self.events.append(f"evaluate:{request['view']}")
        if isinstance(self._outcome, Exception):
            raise self._outcome
        return self._outcome

    def locator(self, selector):
        self.events.append(f"locator:{selector}")
        events = self.events

        class _Shot:
            def screenshot(self, **_options):
                events.append("screenshot")
                return b"\x89PNG\r\n\x1a\n"

        return _Shot()

    def close(self):
        self.events.append("close:page")


class _FakeContext:
    def __init__(self, events: list[str], page: _FakePage) -> None:
        self.events = events
        self._page = page

    def route(self, pattern, _handler):
        self.events.append(f"route:{pattern if isinstance(pattern, str) else 'predicate'}")

    def route_web_socket(self, pattern, _handler):
        self.events.append(
            f"route_websocket:{pattern if isinstance(pattern, str) else 'predicate'}"
        )

    def new_page(self):
        self.events.append("new_page")
        return self._page

    def close(self):
        self.events.append("close:context")


class _FakeBrowser:
    def __init__(self, events: list[str], context: _FakeContext) -> None:
        self.events = events
        self._context = context
        self.options: dict | None = None

    def new_context(self, **options):
        self.options = options
        return self._context

    def close(self):
        self.events.append("close:browser")


class _FakePlaywright:
    def __init__(self, events: list[str], browser: _FakeBrowser) -> None:
        self.events = events
        self._browser = browser

    @property
    def chromium(self):
        browser = self._browser
        events = self.events

        class _Launcher:
            def launch(self, *, headless):
                events.append(f"launch:{headless}")
                return browser

        return _Launcher()

    def stop(self):
        self.events.append("stop")


class _FakeFactory:
    def __init__(self, outcome) -> None:
        self.events: list[str] = []
        self.page = _FakePage(self.events, outcome)
        self.context = _FakeContext(self.events, self.page)
        self.browser = _FakeBrowser(self.events, self.context)
        self.playwright = _FakePlaywright(self.events, self.browser)

    def __call__(self):
        return self

    def start(self):
        self.events.append("start")
        return self.playwright


def _render(tmp_path, factory) -> tuple[dict, bytes]:
    entry = tmp_path / "index.html"
    entry.write_text("<!doctype html><div data-capture-stage></div>", encoding="utf-8")
    return capture._render(
        entry,
        {
            "world": {},
            "partition": None,
            "view": "settlement",
            "map_id": "synthetic_town",
            "width": 40,
            "height": 30,
            "bounds": None,
            "hidden_layers": [],
        },
        width=40,
        height=30,
        playwright_factory=factory,
    )


def test_a_successful_render_closes_page_context_browser_and_playwright(tmp_path):
    factory = _FakeFactory({"bounds": [0, 0, 1, 1], "units": "m", "axes": {"x": "east", "y": "north"}})

    result, shot = _render(tmp_path, factory)

    assert result["units"] == "m"
    assert shot.startswith(b"\x89PNG")
    assert factory.browser.options == {
        "viewport": {"width": 40, "height": 30},
        "device_scale_factor": 1,
        "service_workers": "block",
    }
    events = factory.page.events
    assert any(event.startswith("route:") for event in events)
    assert events.index("goto:load") < events.index("evaluate:settlement") < events.index("screenshot")
    assert events[-4:] == ["close:page", "close:context", "close:browser", "stop"]


def test_a_failed_render_still_closes_every_resource(tmp_path):
    factory = _FakeFactory(RuntimeError("Error: capture: the map was not ready within 20 ms"))

    with pytest.raises(capture.CaptureError) as raised:
        _render(tmp_path, factory)

    assert raised.value.code == "render_failed"
    assert "not ready within 20 ms" in raised.value.message
    events = factory.page.events
    assert events[-4:] == ["close:page", "close:context", "close:browser", "stop"]
    assert "screenshot" not in events


def test_a_launch_failure_carries_the_setup_action(tmp_path, monkeypatch):
    class _Broken:
        def start(self):
            raise RuntimeError("Executable doesn't exist at ~/.cache/ms-playwright/chromium")

    entry = tmp_path / "index.html"
    entry.write_text("<!doctype html>", encoding="utf-8")
    monkeypatch.setattr(capture, "_require_runtime", lambda _entry: _Broken)
    request = capture.CaptureRequest(
        view="settlement",
        map_id="synthetic_town",
        bounds=None,
        width=40,
        height=30,
        hidden_layers=(),
        format="webp",
        output=tmp_path / "map.webp",
    )
    monkeypatch.setattr(
        capture,
        "load_capture_snapshot",
        lambda *_args, **_kwargs: {"world": {}, "partition": None, "diagnostics": []},
    )

    with pytest.raises(capture.CaptureError) as raised:
        capture.capture(request, root=tmp_path, entry=entry)

    assert raised.value.code == "browser_unavailable"
    assert "playwright install chromium" in (raised.value.guidance or "")


def test_a_missing_capture_page_is_refused_with_the_build_action(tmp_path):
    with pytest.raises(capture.CaptureError) as raised:
        capture._require_runtime(tmp_path / "no-index.html")
    assert raised.value.code == "build_missing"
    assert "build:capture" in (raised.value.guidance or "")


# -- real browser probes (optional capture dependency group) ------------------


@pytest.fixture(scope="module")
def chromium():
    sync_api = pytest.importorskip("playwright.sync_api", reason="the capture dependency group is optional")
    try:
        with sync_api.sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True)
            browser.close()
    except Exception as error:  # noqa: BLE001 - an uninstalled browser is a skip, not a failure
        pytest.skip(f"Chromium is not installed for the editor environment: {error}")
    return sync_api


def _page(tmp_path, body: str, name: str = "index.html") -> Path:
    entry = tmp_path / name
    entry.write_text(
        "<!doctype html><meta charset='utf-8'><div data-capture-stage "
        "style='width:40px;height:30px'></div><script>" + body + "</script>",
        encoding="utf-8",
    )
    return entry


def _payload() -> dict:
    return {
        "world": {},
        "partition": None,
        "view": "settlement",
        "map_id": "synthetic_town",
        "width": 40,
        "height": 30,
        "bounds": None,
        "hidden_layers": [],
    }


def test_a_real_page_reports_readiness_under_the_deadline(tmp_path, chromium):
    entry = _page(
        tmp_path,
        "window.renderMapCapture = () => new Promise((resolve) => setTimeout("
        "() => resolve({bounds: [0, 0, 4, 3], units: 'm', axes: {x: 'east', y: 'north'}}), 50));",
    )

    result, shot = capture._render(entry, _payload(), width=40, height=30, deadline_ms=5000)

    assert result["bounds"] == [0, 0, 4, 3]
    # The screenshot is exactly the stage rectangle at scale factor one.
    pillow = pytest.importorskip("PIL.Image")
    with pillow.open(io.BytesIO(shot)) as image:
        assert image.size == (40, 30)


def test_a_real_page_that_never_becomes_ready_is_refused_by_the_deadline(tmp_path, chromium):
    entry = _page(tmp_path, "window.renderMapCapture = () => new Promise(() => {});")

    with pytest.raises(capture.CaptureError) as raised:
        capture._render(entry, _payload(), width=40, height=30, deadline_ms=200)

    assert raised.value.code == "render_failed"
    assert "not ready within 200 ms" in raised.value.message


def test_a_real_page_with_no_entry_script_is_refused(tmp_path, chromium):
    entry = _page(tmp_path, "")

    with pytest.raises(capture.CaptureError) as raised:
        capture._render(entry, _payload(), width=40, height=30, deadline_ms=2000)

    assert raised.value.code == "render_failed"
    assert "renderMapCapture is missing" in raised.value.message


def test_a_real_page_that_opens_a_websocket_is_refused(tmp_path, chromium):
    entry = _page(
        tmp_path,
        "window.renderMapCapture = async () => {"
        " const socket = new WebSocket('ws://127.0.0.1:1/socket');"
        " await new Promise((resolve) => setTimeout(resolve, 50));"
        " socket.close();"
        " return {bounds: [0, 0, 4, 3], units: 'm', axes: {x: 'east', y: 'north'}}; };",
    )

    with pytest.raises(capture.CaptureError) as raised:
        capture._render(entry, _payload(), width=40, height=30, deadline_ms=5000)

    assert raised.value.code == "network_attempted"
    assert "ws://127.0.0.1:1/socket" in raised.value.message


def test_a_real_page_that_touches_the_network_is_refused(tmp_path, chromium):
    entry = _page(
        tmp_path,
        "window.renderMapCapture = async () => {"
        " await fetch('http://127.0.0.1:1/asset.png').catch(() => null);"
        " return {bounds: [0, 0, 4, 3], units: 'm', axes: {x: 'east', y: 'north'}}; };",
    )

    with pytest.raises(capture.CaptureError) as raised:
        capture._render(entry, _payload(), width=40, height=30, deadline_ms=5000)

    assert raised.value.code == "network_attempted"
    assert "asset.png" in raised.value.message


def test_a_real_page_cannot_size_a_screenshot_differently(tmp_path, chromium):
    pytest.importorskip("PIL.Image")
    entry = _page(
        tmp_path,
        "window.renderMapCapture = () => Promise.resolve("
        "{bounds: [0, 0, 4, 3], units: 'm', axes: {x: 'east', y: 'north'}});",
    )
    _, shot = capture._render(entry, _payload(), width=40, height=30, deadline_ms=5000)

    with pytest.raises(capture.CaptureError) as raised:
        capture._encode_image(shot, "webp", width=41, height=30)

    assert raised.value.code == "render_contract"


def test_both_formats_encode_the_same_lossless_pixels(tmp_path, chromium):
    pillow = pytest.importorskip("PIL.Image")
    features = pytest.importorskip("PIL.features")
    entry = _page(
        tmp_path,
        "window.renderMapCapture = () => Promise.resolve("
        "{bounds: [0, 0, 4, 3], units: 'm', axes: {x: 'east', y: 'north'}});",
    )
    _, shot = capture._render(entry, _payload(), width=40, height=30, deadline_ms=5000)
    if not features.check("webp"):
        pytest.skip("this Pillow has no WebP support")

    webp = capture._encode_image(shot, "webp", width=40, height=30)
    png = capture._encode_image(shot, "png", width=40, height=30)

    with pillow.open(io.BytesIO(webp)) as first, pillow.open(io.BytesIO(png)) as second:
        assert first.size == second.size == (40, 30)
        assert first.format == "WEBP" and second.format == "PNG"
        assert first.convert("RGB").tobytes() == second.convert("RGB").tobytes()
    assert webp != png


def test_an_encoder_failure_preserves_the_previous_image_and_prints_nothing(
    tmp_path, monkeypatch, capsys, chromium
):
    pytest.importorskip("PIL.Image")
    entry = _page(
        tmp_path,
        "window.renderMapCapture = () => Promise.resolve("
        "{bounds: [0, 0, 4, 3], units: 'm', axes: {x: 'east', y: 'north'}});",
    )
    monkeypatch.setattr(
        capture,
        "load_capture_snapshot",
        lambda *_args, **_kwargs: {"world": {}, "partition": None, "diagnostics": []},
    )
    destination = tmp_path / "map.webp"
    previous = _existing_image(destination)
    request = capture.CaptureRequest(
        view="settlement",
        map_id="synthetic_town",
        bounds=None,
        width=40,
        height=30,
        hidden_layers=(),
        format="webp",
        output=destination,
    )

    def explode(*_args, **_kwargs):
        raise OSError("the encoder refused this image")

    monkeypatch.setattr("PIL.Image.Image.save", explode)
    with pytest.raises(capture.CaptureError) as raised:
        capture.capture(request, root=tmp_path, entry=entry)

    assert raised.value.code == "encode_failed"
    assert "encoder refused" in raised.value.message
    assert capsys.readouterr().out == ""
    assert destination.read_bytes() == previous
    assert [path.name for path in tmp_path.iterdir() if path.suffix == ".tmp"] == []


def test_a_failed_success_report_names_the_published_image(
    tmp_path, monkeypatch, chromium
):
    pillow = pytest.importorskip("PIL.Image")
    entry = _page(
        tmp_path,
        "window.renderMapCapture = () => Promise.resolve("
        "{bounds: [0, 0, 4, 3], units: 'm', axes: {x: 'east', y: 'north'}});",
    )
    monkeypatch.setattr(
        capture,
        "load_capture_snapshot",
        lambda *_args, **_kwargs: {"world": {}, "partition": None, "diagnostics": []},
    )
    destination = tmp_path / "map.webp"
    request = capture.CaptureRequest(
        view="settlement",
        map_id="synthetic_town",
        bounds=None,
        width=40,
        height=30,
        hidden_layers=(),
        format="webp",
        output=destination,
    )

    class _BrokenPipe:
        def write(self, _text):
            raise BrokenPipeError("the reading process is gone")

        def flush(self):
            raise BrokenPipeError("the reading process is gone")

    monkeypatch.setattr("sys.stdout", _BrokenPipe())
    with pytest.raises(capture.CaptureError) as raised:
        capture.capture(request, root=tmp_path, entry=entry)

    assert raised.value.code == "report_failed"
    assert "was published to" in raised.value.message
    # The image is not rolled back or hidden: it is a complete, decodable file.
    with pillow.open(destination) as image:
        assert image.size == (40, 30)


def test_a_capture_prints_only_after_a_complete_publication(tmp_path, monkeypatch, capsys, chromium):
    pillow = pytest.importorskip("PIL.Image")
    entry = _page(
        tmp_path,
        "window.renderMapCapture = () => Promise.resolve("
        "{bounds: [0, 0, 4, 3], units: 'm', axes: {x: 'east', y: 'north'}});",
    )
    monkeypatch.setattr(
        capture,
        "load_capture_snapshot",
        lambda *_args, **_kwargs: {"world": {}, "partition": None, "diagnostics": []},
    )
    destination = tmp_path / "map.webp"
    previous = _existing_image(destination)
    original_replace = os.replace
    request = capture.CaptureRequest(
        view="settlement",
        map_id="synthetic_town",
        bounds=None,
        width=40,
        height=30,
        hidden_layers=(),
        format="webp",
        output=destination,
    )

    def refuse(_stage, _destination):
        raise OSError("the destination cannot be replaced")

    monkeypatch.setattr(capture.os, "replace", refuse)
    with pytest.raises(capture.CaptureError):
        capture.capture(request, root=tmp_path, entry=entry)
    assert capsys.readouterr().out == ""
    assert destination.read_bytes() == previous

    monkeypatch.setattr(capture.os, "replace", original_replace)
    document = capture.capture(request, root=tmp_path, entry=entry)

    assert json.loads(capsys.readouterr().out) == document
    with pillow.open(destination) as image:
        assert image.size == (40, 30)
