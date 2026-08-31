# Tasks: art-service-connectivity-surface

## 1. Settings

- [ ] 1.1 Add `ART_SD_PROBE_TIMEOUT_MS` (`_env_int` positive with inclusive
  `maximum=60_000` and lower bound 1000 — extend the helper's rule phrasing
  for two-sided ranges as designed in D4) and `ART_SD_PROBE_CACHE_SECONDS`
  (`_env_int`, inclusive 5–3600, default 300) in `server/conf/settings.py`.
- [ ] 1.2 Grow `ENV_BACKED`/`DEFAULT_REPR`/`VALID_OVERRIDES` in
  `server/conf/tests/test_env_overrides.py` to exactly 26 entries (both
  bounds inclusive: 1000/60000 and 5/3600 valid; 999/60001 and 4/3601
  invalid); update the AST inventory expectations and the pop list in
  `server/conf/test_settings.py` (→ 26).

## 2. Probe seam + module

- [ ] 2.0 Add the PUBLIC seam `SDWebUIClient.probe_samplers(*,
  timeout_seconds: float) -> None` in `world/art/sd_worker.py` (one GET
  `/sdapi/v1/samplers`, JSON-list validation, named `SDError`s); mirror a
  scriptable success/named-failure implementation into
  `world/art/fake_sd_client.py` and `web/tests/browser/fake_sd_client.py`.
  `connectivity.py` calls ONLY this method — never `_http_json`.
- [ ] 2.1 Create `world/art/connectivity.py`: frozen `ProbeResult` dataclass;
  `probe(*, force=False)` calling
  `probe_samplers(timeout_seconds=ART_SD_PROBE_TIMEOUT_MS/1000)`, never
  raising (every `SDError`/`OSError` → `ok=False` + named code). `host` =
  `urlsplit().hostname` + validated port ONLY — never raw `netloc` (userinfo
  would leak), never the full URL.
- [ ] 2.2 Process-local single-slot cache guarded by `threading.Lock`, entry =
  `(fingerprint, ProbeResult, wall_ts)`; fingerprint = sha256 over
  `base_url | bool(username) | bool(password) | timeout_ms` (presence only —
  never secret values); reuse iff not forced, younger than
  `ART_SD_PROBE_CACHE_SECONDS` (the TTL itself, re-evaluated per call — not a
  fingerprint component), fingerprint equal; stale/mismatched → fresh probe +
  replace slot.
- [ ] 2.3 `world/art/tests/test_connectivity.py` (unittest.TestCase, fake
  client + injected clock): ok verdict; named code on a scriptable
  `SDError`; within-TTL reuse with zero calls + `from_cache=True`; forced
  probe issues exactly one call despite a young entry; base-URL /
  credential-presence / timeout fingerprint changes each miss the cache; TTL
  expiry re-probes; a base URL of `http://user:password@example.test:7860/`
  yields host `example.test:7860` with no `user`/`password`/`@`/netloc in any
  result, cache entry, or log; result never contains the password. No
  manifest change (label `world.art` covers the package; verify via the
  ownership-contract test).

## 3. `@art health`

- [ ] 3.1 Add `CmdArtHealth` on the `_ArtCommand` Developer base: one forced
  probe (`force=True`), then four fixed-order sections — reachability (+named
  code, "checked just now"), scheduler (`enabled|disabled interval=Xs limit=N`
  from effective settings), queue counts (`pending/in_progress/failed/done`
  exact ints from the record store, read-only), output policy
  (`format q=NN metadata=on|off`).
- [ ] 3.2 Register the command in the art command set; add docs rows +
  `command-reference` section/anchor in `docs/game/commands.md` and
  `docs/game/command-reference.md`; keep `tests/test_command_docs.py` green.
- [ ] 3.3 Command tests (EvenniaCommandTest-style, fake client): both
  reachability renders; all four sections present and exact; store untouched
  after run; denial for non-Developer with zero probe calls; no
  credential/userinfo/absolute-path leakage.

## 4. Non-gating guarantee

- [ ] 4.1 Package-wide import-boundary test: AST-parse EVERY production
  `world/art/**/*.py` file and fail if any module other than
  `connectivity.py` itself imports `world.art.connectivity` (covers worker,
  service, scheduler, queue, store, formats, sd_worker, and future modules —
  a single-module assertion is insufficient).
- [ ] 4.2 Integration test: seed a cached `ok=False` verdict, recover the fake
  server, claim a job, and assert it settles `done` with no reference to the
  stale verdict.

## 5. Docs + inventory

- [ ] 5.1 `.env.example`: `#ART_SD_PROBE_TIMEOUT_MS=5000`,
  `#ART_SD_PROBE_CACHE_SECONDS=300` with range comments.
- [ ] 5.2 Guide `docs/development/settings-and-environment.md`: 26-row
  inventory + troubleshooting row ("health probe is diagnostic only — an
  unreachable verdict never blocks the queue; generation attempts are
  unaffected").
- [ ] 5.3 `docs/gm/prompts.md` ART_SD table gains the two probe rows.

## 6. Verification

- [ ] 6.1 Focused: `MUD_TEST_SETTINGS=1 uv run --locked evennia test
  --settings test_settings.py --keepdb world.art server.conf commands` green.
- [ ] 6.2 `compileall -q world server commands`; `git diff --check`;
  `openspec validate art-service-connectivity-surface --strict`.

## 7. Archive-time traceability sync (after implementation is verified)

- [ ] 7.1 Annotate tests with `@covers_requirement` literal IDs (both
  new-capability requirements, the ADDED `@art health` requirement, the
  MODIFIED settings requirements), sync this change's deltas into
  `openspec/specs/`, and land code + tests + spec sync + archive as one
  commit chain (the `env-overridable-settings` archive precedent); confirm
  IDs against `uv run --locked python -m tools.spec_traceability list` — the
  check gate only accepts them once the specs are synced.
