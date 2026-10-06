#!/usr/bin/env node
// GM dependency boundary (gm-portal-s1-foundation, design D5): the GM SPA in
// web/admin-app may import from the game tree ONLY
// web/webclient-app/styles/tokens.css and web/webclient-app/styles/fonts*.css.
// Dependency-free: node built-ins only.
//
// The scan reads every JS/Vue/CSS source under the GM root, extracts each
// dependency reference (static import/export-from, side-effect import,
// literal dynamic import, require, new URL(<literal>, import.meta.url),
// import.meta.glob, CSS @import and url(), Vue <script>/<style> bodies and
// their src= attributes), strips ?query/#hash suffixes, resolves relative,
// root-absolute ("/" = repo root, the Vite root), and configured alias
// specifiers to a normalized real path, and only then applies the exact
// allowlist. A reference that cannot be resolved statically (non-literal
// dynamic import, any import.meta.glob) fails closed.
import { existsSync, readFileSync, readdirSync, realpathSync, statSync } from "node:fs";
import { dirname, isAbsolute, join, relative, resolve, sep } from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";

const SOURCE_EXTENSIONS = new Set([".js", ".mjs", ".cjs", ".ts", ".vue", ".css"]);
// Game-tree roots (repo-relative). web/static/webclient holds the game's
// preserved protocol/transport logic, so it is game tree too.
export const GAME_ROOTS = Object.freeze(["web/webclient-app", "web/static/webclient"]);
// Allowed game-tree files, relative to web/webclient-app (anchored).
export const ALLOWED_GAME_FILES = Object.freeze([/^styles\/tokens\.css$/, /^styles\/fonts[A-Za-z0-9_-]*\.css$/]);

function extensionOf(file) {
  const index = file.lastIndexOf(".");
  return index === -1 ? "" : file.slice(index);
}

function listSources(dir) {
  const out = [];
  for (const entry of readdirSync(dir)) {
    if (entry === "node_modules" || entry.startsWith(".")) continue;
    const path = join(dir, entry);
    const stat = statSync(path);
    if (stat.isDirectory()) out.push(...listSources(path));
    else if (SOURCE_EXTENSIONS.has(extensionOf(entry))) out.push(path);
  }
  return out.sort();
}

// Strip comments so commented-out imports neither count nor hide real ones.
function stripJsComments(code) {
  return code.replace(/\/\*[\s\S]*?\*\//g, " ").replace(/(^|[^:\\])\/\/[^\n]*/g, "$1");
}

function stripCssComments(code) {
  return code.replace(/\/\*[\s\S]*?\*\//g, " ");
}

const QUOTED = String.raw`(["'\`])([^"'\`]*)\1`;

export function extractJsReferences(source) {
  const code = stripJsComments(source);
  const refs = [];
  const add = (specifier, kind) => refs.push({ specifier, kind });
  const patterns = [
    [new RegExp(String.raw`\bimport\s+(?:[\w$*{}\s,]+?\s+from\s+)?${QUOTED}`, "g"), "import"],
    [new RegExp(String.raw`\bexport\s+(?:\*(?:\s+as\s+[\w$]+)?|\{[^}]*\})\s*from\s*${QUOTED}`, "g"), "re-export"],
    [new RegExp(String.raw`\brequire\s*\(\s*${QUOTED}\s*\)`, "g"), "require"],
    [new RegExp(String.raw`\bnew\s+URL\s*\(\s*${QUOTED}\s*,\s*import\.meta\.url`, "g"), "new-url"],
  ];
  for (const [regex, kind] of patterns) {
    for (const match of code.matchAll(regex)) add(match[2], kind);
  }
  // Dynamic import(): a literal specifier resolves; anything else fails closed.
  for (const match of code.matchAll(/\bimport\s*\(\s*(\/\*[\s\S]*?\*\/\s*)?([^)]*)\)/g)) {
    const arg = match[2].trim();
    const literal = arg.match(/^(["'`])([^"'`$]*)\1$/);
    if (literal) add(literal[2], "dynamic-import");
    else add(null, `non-literal dynamic import(${arg})`);
  }
  for (const match of code.matchAll(/\bimport\.meta\.glob(?:Eager)?\s*\(/g)) {
    add(null, `import.meta.glob at offset ${match.index}`);
  }
  return refs;
}

export function extractCssReferences(source) {
  const code = stripCssComments(source);
  const refs = [];
  for (const match of code.matchAll(/@import\s+(?:url\(\s*)?(["']?)([^"')\s;]+)\1/g)) {
    refs.push({ specifier: match[2], kind: "css-import" });
  }
  for (const match of code.matchAll(/url\(\s*(["']?)([^"')]+)\1\s*\)/g)) {
    refs.push({ specifier: match[2].trim(), kind: "css-url" });
  }
  return refs;
}

export function extractVueReferences(source) {
  const refs = [];
  for (const match of source.matchAll(/<(script|style)\b([^>]*)>([\s\S]*?)<\/\1>/g)) {
    const [, tag, attrs, body] = match;
    const src = attrs.match(/\bsrc\s*=\s*(["'])([^"']+)\1/);
    if (src) refs.push({ specifier: src[2], kind: `${tag}-src` });
    refs.push(...(tag === "script" ? extractJsReferences(body) : extractCssReferences(body)));
  }
  return refs;
}

export function extractReferences(file, source) {
  const ext = extensionOf(file);
  if (ext === ".vue") return extractVueReferences(source);
  if (ext === ".css") return extractCssReferences(source);
  return extractJsReferences(source);
}

function isExternal(specifier) {
  return /^(?:[a-z][a-z0-9+.-]*:|#)/i.test(specifier);
}

function normalize(path) {
  try {
    return existsSync(path) ? realpathSync(path) : resolve(path);
  } catch {
    return resolve(path);
  }
}

// Resolve a specifier to an absolute path, or null for a bare package name.
export function resolveSpecifier(specifier, importer, { repoRoot, aliases }) {
  const clean = specifier.replace(/[?#].*$/, "");
  if (clean.startsWith("./") || clean.startsWith("../") || clean === "." || clean === "..") {
    return normalize(resolve(dirname(importer), clean));
  }
  if (clean.startsWith("/")) return normalize(join(repoRoot, clean));
  for (const [alias, target] of Object.entries(aliases)) {
    if (clean === alias || clean.startsWith(`${alias}/`)) {
      return normalize(join(repoRoot, target, clean.slice(alias.length)));
    }
  }
  if (isAbsolute(clean)) return normalize(clean);
  return null; // bare package (vue, vue-router, ...)
}

function within(path, root) {
  const rel = relative(root, path);
  return rel === "" || (!rel.startsWith("..") && !isAbsolute(rel));
}

export function checkResolved(resolved, { repoRoot }) {
  const gameApp = normalize(join(repoRoot, "web/webclient-app"));
  for (const root of GAME_ROOTS) {
    const absRoot = normalize(join(repoRoot, root));
    if (!within(resolved, absRoot)) continue;
    if (absRoot === gameApp) {
      const rel = relative(gameApp, resolved).split(sep).join("/");
      if (ALLOWED_GAME_FILES.some((pattern) => pattern.test(rel))) return true;
    }
    return false;
  }
  return true;
}

export function scanBoundary({ appRoot, repoRoot, aliases }) {
  const violations = [];
  const realRepo = normalize(repoRoot);
  for (const file of listSources(appRoot)) {
    const source = readFileSync(file, "utf-8");
    const from = relative(realRepo, normalize(file)).split(sep).join("/");
    for (const { specifier, kind } of extractReferences(file, source)) {
      if (specifier === null) {
        violations.push({ source: from, specifier: kind, resolved: null, reason: "unresolvable reference" });
        continue;
      }
      if (!specifier || isExternal(specifier)) continue;
      const resolved = resolveSpecifier(specifier, file, { repoRoot: realRepo, aliases });
      if (resolved === null) continue;
      if (!checkResolved(resolved, { repoRoot: realRepo })) {
        violations.push({
          source: from,
          specifier,
          resolved: relative(realRepo, resolved).split(sep).join("/"),
          reason: `forbidden game-tree dependency (${kind})`,
        });
      }
    }
  }
  return violations;
}

export function formatViolations(violations) {
  return violations
    .map((v) => `  ${v.source} -> ${v.specifier}${v.resolved ? ` (${v.resolved})` : ""}: ${v.reason}`)
    .join("\n");
}

const isMain = process.argv[1] && pathToFileURL(process.argv[1]).href === import.meta.url;
if (isMain) {
  const repoRoot = fileURLToPath(new URL("..", import.meta.url));
  const { GM_ALIASES } = await import(pathToFileURL(join(repoRoot, "web/admin-app/gm-aliases.mjs")).href);
  const violations = scanBoundary({ appRoot: join(repoRoot, "web/admin-app"), repoRoot, aliases: GM_ALIASES });
  if (violations.length) {
    console.error(`GM import boundary: ${violations.length} violation(s)\n${formatViolations(violations)}`);
    process.exit(1);
  }
  console.log("GM import boundary: web/admin-app imports only the allowlisted game tokens and fonts");
}
