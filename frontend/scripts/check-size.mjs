import { readFile } from 'node:fs/promises';
import { resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import { gzipSync } from 'node:zlib';

const root = resolve(fileURLToPath(new URL('..', import.meta.url)));
const manifestPath = resolve(root, 'dist/.vite/manifest.json');
const manifest = JSON.parse(await readFile(manifestPath, 'utf8'));
const entryKey = Object.keys(manifest).find((key) => key.endsWith('src/views/ColonyView.tsx'));
if (!entryKey) throw new Error('The ColonyView entry was not found in the Vite manifest.');
const visited = new Set();
const files = new Set();
function visit(key) {
  if (visited.has(key)) return;
  visited.add(key);
  const chunk = manifest[key];
  if (!chunk) return;
  if (chunk.file?.endsWith('.js')) files.add(resolve(root, 'dist', chunk.file));
  for (const dependency of chunk.imports || []) visit(dependency);
}
visit(entryKey);
const names = [...files];
if (names.some((file) => /maplibre|pmtiles/i.test(file))) throw new Error('The Colony route pulls MapLibre/PMTiles into its static chunk graph.');
const bytes = await Promise.all(names.map(async (file) => gzipSync(await readFile(file)).byteLength));
const total = bytes.reduce((sum, value) => sum + value, 0);
console.log(`Colony route static JS graph: ${(total / 1024).toFixed(1)} KB gzip across ${names.length} chunks (limit 100 KB).`);
if (total > 100 * 1024) throw new Error('Colony route exceeds the 100 KB gzip budget.');
