#!/usr/bin/env node
/**
 * First-load JS budget check (#239).
 *
 * Reads .next/app-build-manifest.json after `next build` and computes the
 * gzipped size of each route's first-load scripts. Fails (exit 1) if any
 * route exceeds its budget, so bundle regressions fail loudly in CI.
 *
 * Budgets are gzipped bytes. DEFAULT_BUDGET covers any route not listed in
 * ROUTE_BUDGETS. Baselines were measured after the #233/#235 pruning; keep
 * headroom modest so regressions are caught early. If a legitimate feature
 * needs more, raise the budget in the same PR and say why.
 */

import { readFileSync, statSync } from "node:fs";
import { join } from "node:path";
import { gzipSync } from "node:zlib";

const NEXT_DIR = join(process.cwd(), ".next");

// Default budget for any app route's first-load JS (gzipped).
// Largest route measured 134 kB after the #233/#235 pruning; 150 kB leaves
// ~12% headroom before the check fires.
const DEFAULT_BUDGET = 150 * 1024;

// Per-route overrides (gzipped bytes); empty today - every route fits the default
const ROUTE_BUDGETS = {};

function fail(msg) {
  console.error(`❌ ${msg}`);
  process.exitCode = 1;
}

let manifest;
try {
  manifest = JSON.parse(readFileSync(join(NEXT_DIR, "app-build-manifest.json"), "utf8"));
} catch (err) {
  console.error(`Cannot read .next/app-build-manifest.json - run \`next build\` first (${err.message})`);
  process.exit(2);
}

const gzipCache = new Map();
function gzippedSize(file) {
  if (!gzipCache.has(file)) {
    const path = join(NEXT_DIR, file);
    try {
      statSync(path);
      gzipCache.set(file, gzipSync(readFileSync(path)).length);
    } catch {
      // Non-file entries (rare) count as zero rather than crashing the check
      gzipCache.set(file, 0);
    }
  }
  return gzipCache.get(file);
}

const rows = [];
for (const [route, files] of Object.entries(manifest.pages)) {
  const jsFiles = files.filter((f) => f.endsWith(".js"));
  const size = jsFiles.reduce((sum, f) => sum + gzippedSize(f), 0);
  const budget = ROUTE_BUDGETS[route] ?? DEFAULT_BUDGET;
  rows.push({ route, size, budget, over: size > budget });
}

rows.sort((a, b) => b.size - a.size);

const kb = (n) => `${(n / 1024).toFixed(1)} kB`;
const width = Math.max(...rows.map((r) => r.route.length));
console.log(`\nFirst-load JS (gzipped) vs budget:\n`);
for (const { route, size, budget, over } of rows) {
  const mark = over ? "❌ OVER" : "✓";
  console.log(`  ${route.padEnd(width)}  ${kb(size).padStart(9)} / ${kb(budget).padStart(9)}  ${mark}`);
}
console.log();

const overs = rows.filter((r) => r.over);
if (overs.length > 0) {
  fail(
    `${overs.length} route(s) over budget. If the growth is intentional, raise the budget in scripts/check-bundle-budget.mjs in the same PR and explain why.`
  );
} else {
  console.log(`✓ All ${rows.length} routes within budget.`);
}
