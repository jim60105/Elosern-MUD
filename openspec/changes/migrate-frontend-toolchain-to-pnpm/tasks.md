## 1. Toolchain & Package Configuration

- [ ] 1.1 Update root `package.json` to declare `"packageManager": "pnpm@9.15.4"`, replace npm `allowScripts` with `"pnpm": { "onlyBuiltDependencies": ["esbuild"] }`, and update the `description` to state no runtime Node.js or pnpm dependencies.
- [ ] 1.2 Enable Corepack via `corepack enable` and run `pnpm install` to generate `pnpm-lock.yaml`.
- [ ] 1.3 Remove `package-lock.json` from git and the workspace.
- [ ] 1.4 Update `.gitignore` comments to reference the pnpm toolchain and verify `node_modules/` and local pnpm artifacts are ignored.

## 2. Container Build Configuration

- [ ] 2.1 Update `Containerfile` `vue-dist` stage to enable Corepack (`RUN corepack enable`).
- [ ] 2.2 Update `Containerfile` `vue-dist` stage to copy `pnpm-lock.yaml` (instead of `package-lock.json`).
- [ ] 2.3 Update `Containerfile` `vue-dist` stage to use BuildKit cache mount `target=/root/.local/share/pnpm/store` and run `pnpm install --frozen-lockfile && pnpm run build`.

## 3. Continuous Integration Workflows

- [ ] 3.1 Update `evennia` job in `.github/workflows/quality-gate.yml` to enable Corepack and run `pnpm install --frozen-lockfile`.
- [ ] 3.2 Update `browser` job in `.github/workflows/quality-gate.yml` to build Vue dist with `pnpm install --frozen-lockfile && pnpm run build` in both workspaces.
- [ ] 3.3 Update `frontend` job in `.github/workflows/quality-gate.yml` to enable Corepack, install dependencies with `pnpm install --frozen-lockfile`, and run `pnpm run build`, `pnpm test`, `pnpm run build-storybook`, and `pnpm run showcase-coverage`.
- [ ] 3.4 Update `top-level` job in `.github/workflows/quality-gate.yml` to enable Corepack (`run: corepack enable`) so contract tests can execute `pnpm`.

## 4. Contract Tests

- [ ] 4.1 Update `tests/test_frontend_toolchain_contract.py` setup and test methods to execute `pnpm install --frozen-lockfile`, `pnpm run build`, `pnpm test`, `pnpm run showcase-coverage`, and verify workflow step names, commands, and `corepack enable` in all relevant jobs (`frontend`, `evennia`, `browser`, `top-level`).
- [ ] 4.2 Update `tests/test_container_contract.py` to assert `RUN corepack enable`, `pnpm install --frozen-lockfile`, and `pnpm run build` in the `vue-dist` stage.
- [ ] 4.3 Update `tests/test_browser_verification_contract.py` to assert the renamed workflow steps and zero runtime npm/pnpm dependencies.

## 5. Documentation & Guidelines

- [ ] 5.1 Update `AGENTS.md` section "Frontend (npm)" to "Frontend (pnpm)" and update commands and Python-vs-pnpm split descriptions.
- [ ] 5.2 Update `docs/development/frontend-developer-guide.md` to reference `pnpm` commands and workflow.
- [ ] 5.3 Update `docs/development/frontend-vue-architecture.md` to reference `pnpm`.

## 6. Verification

- [ ] 6.1 Execute frontend build and test suite (`pnpm run build`, `pnpm test`, `pnpm run build-storybook`, `pnpm run showcase-coverage`) to verify end-to-end functionality.
- [ ] 6.2 Execute focused Python contract tests: `MUD_TEST_SETTINGS=1 uv run --locked evennia test --settings test_settings.py --keepdb tests.test_frontend_toolchain_contract tests.test_container_contract tests.test_browser_verification_contract`.
- [ ] 6.3 Run static requirement traceability check: `uv run --locked python -m tools.spec_traceability check`.
- [ ] 6.4 Validate OpenSpec change integrity with `openspec validate migrate-frontend-toolchain-to-pnpm --strict`.
