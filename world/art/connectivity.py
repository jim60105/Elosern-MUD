"""Diagnostic sd-webui reachability probe with a configuration-keyed TTL cache.

`probe()` answers "is the configured server reachable RIGHT NOW?" the way the
reference plugin does — one fast, bounded ``GET /sdapi/v1/samplers`` through
the public client seam — with three hard invariants:

* **Never raises.** One absolute outer boundary (design D1b) wraps the WHOLE
  operation, lock acquisition included: every failure (transport, HTTP shape,
  decode, settings snapshot, host derivation, client resolution, and even the
  inner recovery path itself) becomes an ``ok=False`` ``ProbeResult`` with a
  named code. A misconfigured deployment is a verdict, never an exception
  path.
* **Never mutates.** Constructing the client issues zero HTTP (the
  ``samples_format`` pre-pin lives in ``generate()``, not the constructor),
  and the probe itself only performs the samplers GET.
* **Never gates.** No production module under ``world/art/`` except this one
  may import it (an AST boundary test enforces the spellings); the queue and
  worker attempt server calls regardless of any verdict. Connectivity is
  diagnostic, not a permission.

The verdict cache is a single process-local slot guarded by one lock. Its key
is a sha256 fingerprint over the effective connectivity settings — the
USERINFO-STRIPPED base URL, credential *presence* booleans, and probe timeout
— so no credential value (including URL userinfo, which the transport never
uses for auth) ever becomes cache material, while any meaningful URL or
credential edit still misses the cache. The TTL
(``ART_SD_PROBE_CACHE_SECONDS``) is re-evaluated per call against the entry's
age, never part of the fingerprint: shortening it invalidates immediately.
"""

from __future__ import annotations

import hashlib
import threading
import time
import urllib.parse
from dataclasses import dataclass, replace

from django.conf import settings

from world.art.sd_worker import SDError, resolve_sd_client

# Emitted when the probe target cannot be derived at all (malformed URL or a
# client seam that cannot even be constructed). Never URL text.
UNKNOWN_HOST = "?"

# Degenerate timestamp for the absolute fallback verdict — a value only the
# never-raises boundary itself can produce.
_FALLBACK_CHECKED_AT = 0.0

# Module-level clock seam; tests patch this instead of injecting a clock
# parameter (the spec pins the probe() signature).
_now = time.monotonic


@dataclass(frozen=True)
class ProbeResult:
    """One reachability verdict. Carries no credential material, no URL."""

    ok: bool
    code: str | None
    host: str
    checked_at: float
    age_seconds: float
    from_cache: bool


# Single cache slot: (fingerprint_hex, ProbeResult, monotonic_ts) | None.
# One server is configured per deployment, so no LRU is needed.
_cache_slot: tuple[str, ProbeResult, float] | None = None
_cache_lock = threading.Lock()


def _settings_snapshot() -> tuple[str, bool, bool, int, int]:
    """Read every connectivity setting exactly once, per probe call.

    The fingerprint, host, probe timeout, and TTL are all derived from this
    one snapshot, so a settings reload racing a probe can never pair the
    fingerprint of one configuration with a request made against another.
    """
    return (
        str(settings.ART_SD_BASE_URL),
        bool(settings.ART_SD_USERNAME),
        bool(settings.ART_SD_PASSWORD),
        int(settings.ART_SD_PROBE_TIMEOUT_MS),
        int(settings.ART_SD_PROBE_CACHE_SECONDS),
    )


def _fingerprint(snapshot: tuple[str, bool, bool, int, int]) -> str:
    """sha256 over the USERINFO-STRIPPED URL + credential PRESENCE + timeout.

    The URL is normalised to ``scheme://host[:port]/path[?query]`` with any
    ``user:password@`` userinfo removed before hashing: the transport derives
    Basic auth ONLY from ART_SD_USERNAME/PASSWORD, so URL userinfo never
    affects a request — and it must never enter cache material either, since
    a plain sha256 of embedded credentials is offline-guessable from a cache
    dump. Credential identity is still covered by the presence booleans.
    """
    base_url, has_user, has_pass, timeout_ms, _ttl = snapshot
    parsed = urllib.parse.urlsplit(base_url)
    netloc = parsed.netloc.rsplit("@", 1)[-1]
    stripped = urllib.parse.urlunsplit(
        (parsed.scheme, netloc, parsed.path, parsed.query, "")
    )
    material = "\0".join((stripped, str(has_user), str(has_pass), str(timeout_ms)))
    return hashlib.sha256(material.encode("utf-8")).hexdigest()


def _target_host(base_url: str) -> str:
    """``hostname[:port]`` derived from the base URL — never userinfo.

    ``urlsplit().netloc`` on ``http://user:password@host:7860`` carries the
    credentials, so it is never used; the port is appended only when it
    parses. Raises on a malformed URL; the boundary converts that to the
    ``UNKNOWN_HOST`` placeholder.
    """
    parsed = urllib.parse.urlsplit(base_url)
    hostname = parsed.hostname
    if not hostname:
        raise ValueError("base URL has no host")
    port = parsed.port  # raises ValueError on an invalid port
    return f"{hostname}:{port}" if port is not None else hostname


def _run_seam(
    snapshot: tuple[str, bool, bool, int, int], host: str
) -> tuple[ProbeResult, str]:
    """One seam call for the snapshotted configuration.

    ``ImportError`` (an unresolvable dotted path / class / constructor seam)
    is a deployment misconfiguration: ``sd_internal_error``. It must NOT be
    swallowed by the ``OSError`` arm below — ``ModuleNotFoundError`` is an
    ``OSError``, and a bad seam is not a connectivity failure.
    """
    _base_url, _has_user, _has_pass, timeout_ms, _ttl = snapshot
    checked_at = _now()
    fingerprint = _fingerprint(snapshot)

    def _failed(code: str, failed_host: str) -> tuple[ProbeResult, str]:
        return (
            ProbeResult(
                ok=False,
                code=code,
                host=failed_host,
                checked_at=checked_at,
                age_seconds=0.0,
                from_cache=False,
            ),
            fingerprint,
        )

    try:
        client = resolve_sd_client()
    except ImportError:
        return _failed("sd_internal_error", UNKNOWN_HOST)
    try:
        client.probe_samplers(timeout_seconds=timeout_ms / 1000)
    except SDError as error:
        return _failed(error.code, host)
    except OSError:
        return _failed("sd_connection_error", host)
    return (
        ProbeResult(
            ok=True,
            code=None,
            host=host,
            checked_at=checked_at,
            age_seconds=0.0,
            from_cache=False,
        ),
        fingerprint,
    )


def probe(*, force: bool = False) -> ProbeResult:
    """One bounded reachability verdict, cached by effective configuration.

    The absolute never-raises boundary (design D1b): it wraps EVERYTHING,
    including lock acquisition and ``_probe_locked``'s own recovery path. If
    anything anywhere raises — even while handling an earlier failure — a
    minimal ``sd_internal_error`` / ``UNKNOWN_HOST`` verdict is returned
    without touching the cache. probe() NEVER raises.
    """
    try:
        return _probe_locked(force=force)
    except Exception:  # noqa: BLE001 - the absolute never-raises boundary
        return ProbeResult(
            ok=False,
            code="sd_internal_error",
            host=UNKNOWN_HOST,
            checked_at=_FALLBACK_CHECKED_AT,
            age_seconds=0.0,
            from_cache=False,
        )


def _probe_locked(*, force: bool) -> ProbeResult:
    """Cache check + probe + slot write under one lock (design D1c).

    A concurrent unforced caller blocks on an in-flight probe and then
    receives its result as ``from_cache=True`` instead of issuing a duplicate
    request, and the slot is replaced only when the completing probe is no
    older than the stored entry, so a slow stale probe can never overwrite a
    newer verdict.

    The inner boundary converts a failed settings snapshot, fingerprint, or
    host derivation into an uncacheable ``sd_internal_error`` verdict: no
    fingerprint exists for a configuration that never resolved, so the slot
    must not be poisoned with a digest of a half-read snapshot.
    """
    global _cache_slot
    with _cache_lock:
        entry_fingerprint: str | None
        try:
            snapshot = _settings_snapshot()
            ttl_seconds = snapshot[4]
            now = _now()
            fingerprint = _fingerprint(snapshot)
            if not force and _cache_slot is not None:
                stored_fp, stored_result, stored_ts = _cache_slot
                age = now - stored_ts
                if 0 <= age < ttl_seconds and stored_fp == fingerprint:
                    return replace(stored_result, age_seconds=age, from_cache=True)
            host = _target_host(snapshot[0])
            result, entry_fingerprint = _run_seam(snapshot, host)
        except Exception:  # noqa: BLE001 - verdict, not exception; may still
            # escalate to the absolute boundary if _now() itself is broken.
            result = ProbeResult(
                ok=False,
                code="sd_internal_error",
                host=UNKNOWN_HOST,
                checked_at=_now(),
                age_seconds=0.0,
                from_cache=False,
            )
            entry_fingerprint = None
        if (
            entry_fingerprint is not None
            and (_cache_slot is None or _cache_slot[2] <= result.checked_at)
        ):
            _cache_slot = (entry_fingerprint, result, result.checked_at)
        return result


def _reset_for_testing() -> None:
    """Clear the cache slot (test isolation only)."""
    global _cache_slot
    with _cache_lock:
        _cache_slot = None
