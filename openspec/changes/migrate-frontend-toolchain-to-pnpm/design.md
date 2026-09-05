## Context

The Elosern MUD project features a Vue 3 SPA frontend (located in `web/webclient-app/`) bundled by Vite into offline static assets served from the Evennia web origin (`web/static/webclient/app/dist/`). The frontend toolchain is strictly dev/CI-time only: the Evennia runtime container and production server execute purely in Python 3.13 with zero Node.js, npm, or pnpm runtime dependencies.

Currently, the frontend uses `npm` (`npm ci`) with `package-lock.json`. While functional, npm uses a flat `node_modules` structure prone to phantom dependencies and repeated package downloads. Furthermore, `package.json` contains unaligned script execution settings (`allowScripts` specifying `esbuild@0.28.2` while `devDependencies` specifies `^0.28.1`).

The project baseline runtime environment is Node 24 (`node >= 24`). Node 24 comes with `corepack` pre-bundled, enabling zero-install, deterministic management of `pnpm`.

## Goals / Non-Goals

**Goals:**
- Atomically migrate the frontend package manager from `npm` to `pnpm`.
- Pin the pnpm version via the `"packageManager"` field in `package.json` (e.g. `pnpm@9.15.4`) and enable it via Node 24's built-in Corepack.
- Replace `package-lock.json` with a deterministic, committed `pnpm-lock.yaml`.
- Replace npm's `allowScripts` with pnpm's native `"pnpm": { "onlyBuiltDependencies": ["esbuild"] }` allowlist configuration.
- Optimize multi-stage container builds in `Containerfile` (`vue-dist` stage) using Corepack and BuildKit cache mounting targeting the pnpm store (`/root/.local/share/pnpm/store`).
- Update CI quality-gate workflows (`.github/workflows/quality-gate.yml`) across `evennia`, `browser`, `frontend`, and `top-level` jobs to activate Corepack and run locked pnpm commands.
- Update Python contract tests (`tests/test_frontend_toolchain_contract.py`, `tests/test_container_contract.py`, and `tests/test_browser_verification_contract.py`) to verify pnpm commands, structure, and Corepack activation prerequisites.
- Update developer documentation and configuration comments (`AGENTS.md`, `docs/development/frontend-developer-guide.md`, `docs/development/frontend-vue-architecture.md`, `package.json` description, and `.gitignore` comments).

**Non-Goals:**
- No changes to Vue application source code or components (`web/webclient-app/**`).
- No changes to the DOM-independent pure JavaScript logic (`web/static/webclient/js/**`), which remains dependency-free and tested via native `node --test`.
- No addition of new dev tools or typecheck pipelines (e.g. `vue-tsc`) in this change; keep the migration strictly focused on the package manager cutover.
- No changes to Evennia server runtime, backend dependencies, or production container layers.

## Decisions

### D1: Package Manager Choice and Version Pinning
- **Decision**: Adopt `pnpm` pinned via `"packageManager": "pnpm@9.15.4"` in `package.json`.
- **Rationale**: Node 24 bundles Corepack 0.35+, which natively resolves and activates pnpm 9. pnpm 9 provides mature, stable support for Vite 7, Vitest 3, and Storybook 10, avoiding potential peer dependency breaking changes found in early pnpm 10 releases.
- **Alternatives Considered**:
  - *pnpm 10*: Newer, but introduces stricter defaults on peer dependencies that may introduce friction with Storybook plugins without tangible benefit.
  - *Bun / Deno*: Rejected per architectural analysis in `tmp/Bun 與 Deno 與 pnpm 與 npm 比較.md` due to runtime conflicts with Node's native `node --test` runner, CJS/ESM dual-stack constraints, and complex Storybook tooling compatibility.
  - *Keep npm*: Retains slower installations, redundant disk usage, and flat node_modules vulnerability.

### D2: Lifecycle Script Security (`onlyBuiltDependencies`)
- **Decision**: Remove `allowScripts` from `package.json` and configure:
  ```json
  "pnpm": {
    "onlyBuiltDependencies": [
      "esbuild"
    ]
  }
  ```
- **Rationale**: npm's `allowScripts` is an npm-specific property. In pnpm, lifecycle scripts (`install`, `postinstall`) are constrained by declaring an explicit allowlist under `pnpm.onlyBuiltDependencies`. `esbuild` requires running its postinstall script to install its native binary platform package; all other dependencies are prevented from executing arbitrary scripts during installation.
- **Alternatives Considered**:
  - *Disabling lifecycle scripts entirely*: Fails because `esbuild` requires its postinstall setup.
  - *Allowing all scripts (`--no-frozen-lockfile` or unconstrained)*: Degrades security posture against malicious packages.

### D3: Containerfile BuildKit Cache Mount & Corepack Acquisition
- **Decision**: In `Containerfile` (`vue-dist` stage):
  ```dockerfile
  FROM docker.io/library/node:24-slim AS vue-dist
  ARG TARGETARCH
  ARG TARGETVARIANT
  WORKDIR /build
  RUN corepack enable
  COPY --chown=root:0 package.json pnpm-lock.yaml vite.config.js ./
  RUN --mount=type=cache,id=pnpm-$TARGETARCH$TARGETVARIANT,sharing=locked,target=/root/.local/share/pnpm/store \
      pnpm install --frozen-lockfile
  COPY --chown=root:0 web/ /build/web/
  RUN pnpm run build
  ```
- **Rationale**: pnpm utilizes a global content-addressable store. By caching `/root/.local/share/pnpm/store` with BuildKit cache mounts scoped by target architecture, subsequent container builds avoid redownloading packages while keeping the resulting static output cleanly separated in `app-layout`.
- **Operational Requirement**: Note that `corepack enable` configures shims, and the initial execution of `pnpm` fetches the pinned version into Corepack's cache. Container builds require outbound network access during the build stage for initial tool and package resolution.
- **Alternatives Considered**:
  - *Caching `/root/.npm`*: Invalid path for pnpm; fails to cache store.
  - *No cache mount*: Forces full network fetch of all packages on every container rebuild.

### D4: CI Workflow Strategy via Built-in Corepack & Cache Policy
- **Decision**: Enable Corepack via `run: corepack enable` after `actions/setup-node@v7` across **all** CI jobs that invoke Node/pnpm (`frontend`, `evennia`, `browser`, and `top-level`).
  - Keep `package-manager-cache: false` in `actions/setup-node@v7`.
  ```yaml
  - name: Install Node.js
    uses: actions/setup-node@v7
    with:
      node-version: "24"
      package-manager-cache: false
  - name: Enable Corepack and install locked pnpm toolchain
    run: |
      corepack enable
      pnpm install --frozen-lockfile
  ```
- **Rationale**:
  - `top-level` job executes `tests/test_frontend_toolchain_contract.py`, which runs `pnpm install --frozen-lockfile`, `pnpm run build`, `pnpm test`, and `pnpm run showcase-coverage`. Without `corepack enable` in `top-level`, `pnpm` is not on `PATH` and the regression suite fails.
  - `actions/setup-node@v7` pnpm caching requires pnpm to be resolved before the action runs or requires specific store paths. Because Corepack is enabled as a post-setup step, keeping `package-manager-cache: false` avoids cache resolution errors. Furthermore, with `pnpm install --frozen-lockfile` and hard links, pnpm installs in CI are already lightweight and fast. If persistent CI caching is added in the future, it should use a dedicated `actions/cache` step targeting the output of `pnpm store path`.
- **Alternatives Considered**:
  - *`pnpm/action-setup@v4`*: Adds an external third-party GitHub Action dependency to maintain when Corepack is already standard in Node 24.
  - *`package-manager-cache: true` in setup-node*: Fragile with Corepack; may fail or silently do nothing without pre-existing pnpm on PATH during setup-node execution.

### D5: Single Atomic Change & Contract Verification
- **Decision**: Perform the migration across toolchain, CI, container, contract tests, specs, and docs in a single change.
- **Rationale**: CI and test suites enforce locked dependency synchronization (`npm ci` vs `pnpm install --frozen-lockfile`). Splitting the change across multiple changes would leave intermediate branches broken.
- **Contract Enforcement**: Python contract tests will assert:
  - Every workflow job invoking pnpm (`frontend`, `evennia`, `browser`, `top-level`) includes a step running `corepack enable`.
  - The `Containerfile` `vue-dist` stage includes `RUN corepack enable` and `pnpm install --frozen-lockfile`.
  - The repo root maintains zero runtime npm or pnpm dependencies in `package.json`.

## Risks / Trade-offs

- **[Risk] Phantom dependencies / Strict Symlink Resolution**: pnpm's non-flat `node_modules` might cause modules that implicitly relied on transitive hoisting to fail resolution during build or tests.
  - *Mitigation*: The project's dependencies are clean (Vue 3, Vite, Vitest, Storybook 10, JSDOM, Pinia). Storybook 10 and Vite 7 fully support pnpm's symlinked layout. All gates (`pnpm run build`, `pnpm test`, `pnpm run build-storybook`, `pnpm run showcase-coverage`) will be executed to verify complete resolution. If needed, pnpm hoisting configuration (`shamefully-hoist=false` or specific `.npmrc` settings) can be applied.
- **[Risk] CI Execution Speed & Cache Parity**: Transitioning package managers might affect CI caching if not properly configured.
  - *Mitigation*: pnpm installation is significantly faster than npm even without cache. With `pnpm install --frozen-lockfile` and hard links, disk and CPU overhead in CI is minimized.
- **[Risk] Contract Test Regression**: Python contract tests in `tests/test_frontend_toolchain_contract.py` and `tests/test_container_contract.py` contain string checks for `npm ci` and `npm run build`.
  - *Mitigation*: The contract tests are explicitly included in the change scope and will be updated to assert pnpm commands, step names, and Corepack activation prerequisites.
