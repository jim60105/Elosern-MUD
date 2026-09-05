## Why

The frontend view layer of Elosern MUD currently uses `npm` with a standard flat `node_modules` structure, which suffers from duplicate disk space consumption, slower installation times in CI and container builds, and lack of strict dependency boundary enforcement (risking phantom dependencies). Furthermore, `package.json` currently contains unaligned script execution constraints (`esbuild@0.28.2` in `allowScripts` vs `^0.28.1` in `devDependencies`).

As evaluated in architectural comparisons, `pnpm` is the ideal package manager for this Vue 3 SPA + Node 24 + Vite + Vitest + Storybook stack:
1. It uses content-addressable storage and hard links to drastically reduce installation time and disk footprint.
2. Its symlinked, non-flat `node_modules` strictly prevents undeclared phantom dependencies.
3. Node 24 includes Corepack to activate and pin pnpm deterministically without global npm installations.
4. Container multi-stage builds can leverage BuildKit cache mounts (`/root/.local/share/pnpm/store`) for instantaneous cached builds while producing clean, runtime-independent static assets.

Because the project is in early unreleased development with zero production users, migrating cleanly to `pnpm` now establishes a modern, fast, and strict frontend toolchain with no backward-compatibility burden.

## What Changes

- **BREAKING (Frontend Toolchain & CI)**: Adopt `pnpm` (managed via Node 24 Corepack and pinned via `"packageManager"` in `package.json`) as the sole package manager for the frontend view layer.
- **Lockfile Cutover**: Delete `package-lock.json` and commit `pnpm-lock.yaml` generated via `pnpm install`.
- **Lifecycle Script Allowlist**: Replace npm-specific `allowScripts` in `package.json` with pnpm's native allowlist configuration `"pnpm": { "onlyBuiltDependencies": ["esbuild"] }`, permitting only `esbuild` to run its native binary postinstall script.
- **Container Build Optimization**: Update `Containerfile` (`vue-dist` stage) to enable Corepack, copy `pnpm-lock.yaml`, leverage a BuildKit cache mount targeting the pnpm store (`/root/.local/share/pnpm/store`), and execute `pnpm install --frozen-lockfile && pnpm run build`.
- **CI Quality Gate**: Update `.github/workflows/quality-gate.yml` across `evennia`, `browser`, `frontend`, and `top-level` jobs to activate Corepack (`corepack enable`), install locked dependencies using `pnpm install --frozen-lockfile`, and run scripts via `pnpm` (`pnpm run build`, `pnpm test`, `pnpm run build-storybook`, `pnpm run showcase-coverage`).
- **Contract Tests**: Update `tests/test_frontend_toolchain_contract.py`, `tests/test_container_contract.py`, and `tests/test_browser_verification_contract.py` to execute and verify `pnpm` commands, step names, Corepack activation prerequisites across all jobs, and configuration assertions.
- **Developer Documentation & Configuration Metadata**: Update `AGENTS.md`, `docs/development/frontend-developer-guide.md`, `docs/development/frontend-vue-architecture.md`, `package.json` description, and `.gitignore` comments to reflect the pnpm toolchain commands and the Python-vs-pnpm boundary while preserving the zero-runtime-Node-dependency invariant.

## Capabilities

### New Capabilities
None.

### Modified Capabilities
- `webclient-browser-verification`: Update quality gate requirements and locked dependency scenarios to require the Corepack-managed locked pnpm toolchain (`pnpm install --frozen-lockfile`, `pnpm-lock.yaml`, `pnpm run build`, `pnpm test`) while maintaining zero runtime npm/pnpm dependencies.
- `webclient-component-showcase`: Update verification scenarios to specify `pnpm run build-storybook` and `pnpm run showcase-coverage`.

## Impact

- **Frontend Configuration**: `package.json` (version pinning, description, and `onlyBuiltDependencies`), `pnpm-lock.yaml` (replacing `package-lock.json`), and `.gitignore` comments.
- **Containerization**: `Containerfile` (`vue-dist` stage Corepack activation, BuildKit cache mount, and build commands).
- **CI / Workflows**: `.github/workflows/quality-gate.yml` (`evennia`, `browser`, `frontend`, and `top-level` jobs).
- **Test Suite**: `tests/test_frontend_toolchain_contract.py`, `tests/test_container_contract.py`, `tests/test_browser_verification_contract.py`.
- **Documentation**: `AGENTS.md`, `docs/development/frontend-developer-guide.md`, `docs/development/frontend-vue-architecture.md`.
- **Runtime Invariants**: Unchanged. The Vue build remains view-layer-only dev/CI tooling; the Evennia server serves the compiled offline assets with no Node.js or pnpm runtime dependency.
