# Design: art-service-connectivity-surface

## Context

After A and B, the art pipeline has: an `SDWebUIClient` whose `_http_json`
accepts a per-call `timeout_seconds` and maps every transport failure to a
named `SDError` code; option-enumeration GETs (`/sdapi/v1/samplers` is
already one of them); optional Basic auth from the never-env auth pair; and
an output-format policy the operator configures by env. The reference plugin
wraps the same server call surface with a connectivity layer
(`connection-flag.ts` + `connection-probe.ts`): a fast `GET
/sdapi/v1/samplers` probe on the same transport, a TTL cache keyed by a
config fingerprint so edits to URL/credentials invalidate stale verdicts, a
cached-flag UI badge, and an uncached "Test connection" action. Its probe
never throws — a failure is a `false` flag, never an exception path.

Constraints: `world/ai/`-style read-only discipline does not apply here
(`world/art/` is a named mutation owner, but a probe mutates nothing at all);
the deterministic core must keep working with the probe absent or failing —
**the probe is diagnostic, never a gate**; settings env names are capped by
the inventory contract at "exactly 26" after this change; new staff commands
must land with docs + tests per AGENTS.md.

## Goals / Non-Goals

**Goals:**

- One bounded, cached, never-raising reachability verdict that reflects the
  *effective* configuration (a URL/credential edit must not be masked by a
  cached verdict about the old target).
- `@art health`: single-screen operator dashboard — reachability (+age),
  scheduler on/off + interval/limit, queue counts by status, effective output
  policy.
- Two bounded, typed env knobs, consistent with the existing helper family.

**Non-Goals:**

- Host allowlists / SSRF policy / DNS pinning (the reference's
  `allowedHostPatterns` + `resolveAndPinHostnames`): our `ART_SD_BASE_URL` is
  operator-authored in a settings/secret file, never user-supplied — adopting
  a defense against a threat class we don't have adds two env knobs and a DNS
  code path for zero protection, and pinning interacts badly with the CDN/TLS
  behavior we deliberately left to urllib (see the settings-env design's TLS
  decision). Rejected with reason.
- An `enabled` master switch (the reference's `enabled` setting gates the
  *plugin's* queue; our equivalent is `ART_SCHEDULER_ENABLED` + `@art run`
  already controlling drain — a second kill-switch would fork the truth).
- Background probes / timers: the cache is lazy (probe on read, refresh when
  stale), not a thread. The scheduler tick already touches the server only
  when draining. No new threads, no new Evennia Scripts.
- Persisting probe history (the reference stores nothing either; the verdict
  is a process-local snapshot).

## Decisions

### D1 — `probe(*, force=False)` shape, lazy TTL cache keyed by a settings fingerprint

`world/art/connectivity.py`:

```python
@dataclass(frozen=True)
class ProbeResult:
    ok: bool
    code: str | None      # None when ok; else the named SDError code
    host: str             # urlsplit().hostname + ':' + validated port ONLY —
                          # NEVER netloc (urlsplit('http://u:p@h:7860')
                          # .netloc == 'u:p@h:7860' leaks userinfo) and never
                          # the full URL
    checked_at: float     # time.monotonic() snapshot
    age_seconds: float    # wall-clock seconds since the probe ran
    from_cache: bool
```

The probe seam is a PUBLIC client method, never the private `_http_json`:
change C adds `SDWebUIClient.probe_samplers(*, timeout_seconds: float) ->
None` (GETs `/sdapi/v1/samplers`, validates a JSON list, returns None, raises
the same named `SDError`s), and `connectivity.probe()` calls ONLY that method
of the configured `ART_SD_CLIENT` class — so the module composes with any
client implementing the documented seam. `world/art/fake_sd_client.py` and
`web/tests/browser/fake_sd_client.py` gain a matching scriptable
`probe_samplers` (success or named failure), which is how the cache tests and
the non-gating test run socket-free.

`probe(force=False)` returns the cache entry when `not force`, the entry is
younger than `ART_SD_PROBE_CACHE_SECONDS`, and its stored fingerprint equals
the fingerprint of the current effective connectivity settings; otherwise it
runs one `probe_samplers(timeout_seconds=ART_SD_PROBE_TIMEOUT_MS / 1000)`
call, catches every `SDError`/`OSError`/timeout, and caches the result. It
NEVER raises: an unreachable or misconfigured server is
`ProbeResult(ok=False, code=...)`.
The fingerprint is `sha256(base_url | has_user | has_pass | timeout_ms)` —
inclusion *presence*-booleans keeps secret material out of any loggable
value; a change to any component (or settings reload) misses the cache.
`ART_SD_PROBE_CACHE_SECONDS` is deliberately NOT in the fingerprint — it is
the TTL itself, re-evaluated against the entry's age on every call, so
shortening it invalidates immediately and lengthening it only ever admits
entries the new (longer) TTL still covers. `force=True` (always used by
`@art health`, see D3) probes fresh and never consumes the entry.
Cache is a single module-level slot (one server configured; no LRU needed),
guarded by a `threading.Lock` because `@art health` runs under Evennia's
async server while the scheduler worker thread is the only other possible
reader (a lock miss just re-probes — never corrupts).

Rationale vs. reference: identical semantics (fast samplers probe, TTL,
fingerprint invalidation, force bypass, never-throw), minus the plugin's
`chrome.storage` persistence — process-local is the honest lifetime (the
verdict describes *now*; a restart probing fresh is correct).

### D2 — The probe is diagnostic-only, enforced by structure

No production module under `world/art/` except `connectivity.py` itself SHALL
import `world.art.connectivity` — that is worker.py, service.py, scheduler.py,
queue.py, store.py, formats.py, sd_worker.py, and every future module. The
only importer is `commands/art.py`. Enforcement is an import-boundary test
that AST-parses EVERY production `world/art/**/*.py` file and fails on any
`connectivity` import outside `connectivity.py` itself (a one-module
assertion on `worker` alone would let a gate through `service`/`scheduler`/
`queue` pass), PLUS an integration test that seeds a cached `ok=False`
verdict, recovers the fake server, and asserts a claimed job still settles
`done`. The queue contract (`art-queue-worker`) stays unchanged. A health
"unreachable" verdict while `@art run` succeeds is a legitimate state
(server flapping) and the UI text says so via the verdict age.

### D3 — `@art health` output contract

Developer-gated (same `_ArtCommand` base as every other `@art` subcommand).
Sections, in fixed order, each one line-ish:

1. `server: reachable (checked just now)` or
   `server: unreachable — sd_connection_error (checked just now)`.
   `@art health` ALWAYS forces a fresh probe (`force=True`) — the reference's
   "Test connection" semantic, the right default for the only surface we have
   (the reference's badge uses the cached path; we have no badge). The cached
   path exists for tests and any future badge-like surface; the spec pins that
   a forced check does not reuse an entry younger than the TTL, and that an
   unforced read within the TTL of a matching fingerprint returns
   `from_cache=True` without a request.

2. `scheduler: enabled interval=45s limit=8` (effective settings).
3. `queue: pending=3 in_progress=1 failed=2 done=41` (counted from the
   existing record store; read-only).
4. `output: webp q=80 metadata=on` (effective format policy from B).

No credentials, no URL userinfo, no absolute paths, no prompt text — same
leakage contract as `@art status`. Counts are exact integers (bounded by the
record store); verdict age is the only float (1 decimal).

### D4 — Two bounded int knobs reuse B's inclusive-maximum helper

`ART_SD_PROBE_TIMEOUT_MS` (`_env_int` positive, `maximum=60_000`, default
`5_000`, min 1000: values below 1000 are `ImproperlyConfigured` — the probe's
whole point is surviving a slow-but-alive server) and
`ART_SD_PROBE_CACHE_SECONDS` (`_env_int`, lower bound 5 inclusive,
`maximum=3_600`, default `300`). Both join the exact-26 inventory (`.env.
example`, guide, `ENV_BACKED`/`DEFAULT_REPR`/`VALID_OVERRIDES`, pop list).
The probe TIMEOUT is part of the cache fingerprint, so a timeout edit cannot
be masked by a cached entry; the cache SECONDS is the TTL itself
re-evaluated per call (see D1), not a fingerprint component.

## Risks / Trade-offs

- [Cache hides a state flip for up to TTL seconds] → `@art health` always
  forces; the cached verdict's age is always printed; 300 s default is short.
- [A reachable-but-wrong-server verdict ("200 OK but not sd-webui")] → the
  samplers probe only validates HTTP+JSON-list shape, same as the reference;
  deeper validation is the enumeration commands' (`@art options`) job.
- [Fingerprint includes only credential *presence*] → a password *rotation*
  to a still-valid password keeps a cached verdict up to TTL; the forced probe
  on health catches it immediately, and the flag itself is about reachability,
  not auth success — a 401 maps to `sd_http_error` on the next real call.
- [New command = new doc-surface obligations] → tasks bind docs +
  `test_command_docs.py` in the same change.
