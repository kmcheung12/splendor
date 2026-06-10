// Bundle size gate for the training explainer article.
//
// Budget rationale:
// - JS budget: Three.js is ~700 KB raw (~200 KB gzip), onnxruntime-web shim
//   adds ~400 KB raw (~110 KB gzip). Total gzip JS is ~315 KB, well under the
//   600 KB gzip target. Raw JS budget is set to 1.5 MB.
// - Excluded from JS + total budgets (they are data assets, not app code):
//     .wasm  — onnxruntime-web WASM (~26 MB, lazy-loaded, browser-cached)
//     .data  — ONNX model weights (~2 MB, lazy-loaded)
//     .onnx  — ONNX model graph
//     runs/  — JSON data (snapshots ~3 MB each, replays ~0.5 MB each)
//              These scale with training data, not with the app codebase.
//     stats.html — visualizer output, not deployed
// - Total app code (JS + CSS + HTML): kept under 2 MB raw.
import { readdirSync, statSync } from 'fs';
import { join, sep } from 'path';

const MAX_JS_BYTES = 1.5 * 1024 * 1024;   // 1.5 MB raw JS
const MAX_APP_BYTES = 2 * 1024 * 1024;    // 2 MB total app code
const DIST = 'dist-article';

const isDataAsset = (relPath) => {
  const f = relPath.split(sep).pop();
  if (f.endsWith('.wasm') || f.endsWith('.data') || f.endsWith('.onnx')) return true;
  if (f === 'stats.html') return true;
  // JSON files inside the runs/ data directory
  if (relPath.includes(`${sep}runs${sep}`) && f.endsWith('.json')) return true;
  if (relPath.includes(`${sep}snapshots${sep}`) && f.endsWith('.json')) return true;
  return false;
};

let appTotal = 0;
let js = 0;
let dataTotal = 0;
const walk = (dir, base = dir) => {
  for (const f of readdirSync(dir)) {
    const p = join(dir, f);
    const rel = p.slice(base.length);
    const s = statSync(p);
    if (s.isDirectory()) walk(p, base);
    else if (isDataAsset(rel)) {
      dataTotal += s.size;
    } else {
      appTotal += s.size;
      if (f.endsWith('.js')) js += s.size;
    }
  }
};
walk(DIST);

console.log(`App code total:  ${(appTotal / 1024).toFixed(1)} KB  (JS + CSS + HTML)`);
console.log(`JS:              ${(js / 1024).toFixed(1)} KB`);
console.log(`Data assets:     ${(dataTotal / 1024).toFixed(1)} KB  (WASM + ONNX + run data, excluded)`);

if (appTotal > MAX_APP_BYTES) {
  console.error(`App code exceeds budget of ${(MAX_APP_BYTES / 1024 / 1024).toFixed(0)} MB`);
  process.exit(1);
}
if (js > MAX_JS_BYTES) {
  console.error(`JS exceeds budget of ${(MAX_JS_BYTES / 1024 / 1024).toFixed(1)} MB raw`);
  process.exit(1);
}

console.log('Bundle size OK.');
