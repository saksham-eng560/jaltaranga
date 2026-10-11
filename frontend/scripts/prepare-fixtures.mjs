import { mkdir, copyFile, readFile, writeFile } from 'node:fs/promises';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const root = resolve(dirname(fileURLToPath(import.meta.url)), '../..');
const out = resolve(root, 'frontend/public/fixtures');
await mkdir(out, { recursive: true });

const fixtureNames = [
  'hero.json', 'evacuation_plans.json', 'road_segment_status.json', 'shelters.json',
  'forecast_nodes.json', 'depth_index.json', 'plans_unreachable.json', 'trap_summary.json',
  'dispatch_card.json', 'dispatch_card_fallback.json', 'dispatch_card_shelter_in_place.json',
  'dispatch_cache_sample.json', 'report_post_response.json', 'colony_thresholds.json',
];
for (const name of fixtureNames) {
  await copyFile(resolve(root, 'shared/fixtures', name), resolve(out, name));
}

try {
  await copyFile(
    resolve(root, 'frontend/node_modules/maplibre-gl/dist/maplibre-gl-worker.mjs'),
    resolve(root, 'frontend/public/maplibre-gl-worker.mjs')
  );
} catch {
  // Ignore if worker source path varies
}

const anchors = (await readFile(resolve(root, 'ml/data/fallback/drb_anchors.csv'), 'utf8'))
  .trim().split(/\r?\n/).slice(1).map((line) => {
    const [ts, rawLevel, sourceRef] = line.split(',');
    return {
      station_id: 'DELHI_RLY_BRIDGE', ts, level_m: Number(rawLevel), discharge_cumecs: null,
      source: sourceRef.startsWith('cwc') ? 'cwc' : 'digitized', qc_flag: 'ok', source_ref: sourceRef,
    };
  });
await writeFile(resolve(out, 'gauges.json'), JSON.stringify(anchors, null, 2));

const [hero, plans] = await Promise.all([
  readFile(resolve(out, 'hero.json'), 'utf8').then(JSON.parse),
  readFile(resolve(out, 'evacuation_plans.json'), 'utf8').then(JSON.parse),
]);
const validAt = Object.keys(plans).sort((a, b) => Date.parse(a) - Date.parse(b));
const thresholds = { warning: 204.5, danger: 205.33, evacuation: 206.0, hfl: 208.66 };
const crossings = Object.entries(thresholds).flatMap(([kind, level]) => {
  const prior = anchors.find((row) => row.level_m >= level);
  return prior ? [{ kind, ts: prior.ts, level_m: prior.level_m, ts_verified: kind !== 'hfl' }] : [];
});
const manifest = {
  scenario_id: 'yamuna-2023-07', mode: 'replay', title_en: 'Yamuna flood · July 2023',
  title_hi: 'यमुना बाढ़ · जुलाई 2023', start: validAt[0], end: validAt.at(-1), step_min: 180,
  valid_at: validAt, issued_at: [], default_at: hero.hero.t, ref_station: 'DELHI_RLY_BRIDGE',
  thresholds, events: crossings,
  artefacts: { gauges: 'fixture', forecasts: 'fixture', depth: 'missing', roads: 'fixture', plans: 'fixture', infra: 'missing' },
  sources: [
    { id: 'drb-anchors', label: 'Source-labeled CWC and press anchors', provenance: 'ml/data/fallback/drb_anchors.csv' },
    { id: 'routing-fixtures', label: 'Synthetic development world', provenance: 'shared/fixtures/README.md' },
  ],
  built_at: null, git_sha: null, data_version: 'local-fixtures',
};
await writeFile(resolve(out, 'manifest.json'), JSON.stringify(manifest, null, 2));
console.log(`Prepared ${fixtureNames.length + 2} local fixture assets from tracked project data.`);
