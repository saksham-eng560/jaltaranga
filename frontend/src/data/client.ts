import type {
  DispatchCard, EvacuationPlan, ForecastNode, GaugeReading, Manifest,
  ReplayStep, ReportPostResponse, RoadSegmentStatus, Shelter, TrapSummary, UnreachableEntry,
} from '../shared/types';

const SCENARIO = import.meta.env.VITE_SCENARIO_ID || 'yamuna-2023-07';
const STATIC_BASE = (import.meta.env.VITE_STATIC_BASE || '').replace(/\/$/, '');
const API_BASE = (import.meta.env.VITE_API_BASE || '').replace(/\/$/, '');
const TIMEOUT_MS = 3_000;

export class DataError extends Error {
  constructor(message: string, readonly status?: number) { super(message); this.name = 'DataError'; }
}

export function safePathSegment(value: string): string {
  return encodeURIComponent(value);
}

export function withReplayQuery(path: string, at: string): string {
  const url = new URL(path, window.location.origin);
  url.searchParams.set('at', at);
  return url.toString();
}

async function getJson<T>(url: string, optional = false): Promise<T | null> {
  const controller = new AbortController();
  const timeout = window.setTimeout(() => controller.abort(), TIMEOUT_MS);
  try {
    const response = await fetch(url, { headers: { Accept: 'application/json' }, signal: controller.signal, cache: 'no-store' });
    if (optional && (response.status === 403 || response.status === 404)) return null;
    if (!response.ok) throw new DataError(`Request failed (${response.status})`, response.status);
    return await response.json() as T;
  } catch (error) {
    if (error instanceof DataError) throw error;
    if (error instanceof DOMException && error.name === 'AbortError') throw new DataError('Data request timed out.');
    throw new DataError(error instanceof Error ? error.message : 'Data request failed.');
  } finally {
    window.clearTimeout(timeout);
  }
}

function inferLayer(manifest: Manifest, key: string): 'static' | 'fixture' | 'missing' {
  const declared = manifest.artefacts?.[key];
  if (declared === 'missing') return 'missing';
  return declared === 'fixture' ? 'fixture' : 'static';
}

function featureCollection(value: unknown): GeoJSON.FeatureCollection | null {
  if (!value || typeof value !== 'object' || (value as { type?: string }).type !== 'FeatureCollection') return null;
  return value as GeoJSON.FeatureCollection;
}

async function loadStaticStep(at: string): Promise<ReplayStep> {
  const base = STATIC_BASE;
  const manifestUrl = `${base}/scenarios/${safePathSegment(SCENARIO)}/manifest.json`;
  const manifest = await getJson<Manifest>(manifestUrl) as Manifest;
  if (!manifest.valid_at.includes(at)) throw new DataError('Selected timestamp is not in the static manifest.');
  const prefix = `/scenarios/${safePathSegment(SCENARIO)}`;
  const g = (artifact: string, path: string) => inferLayer(manifest, artifact) === 'missing'
    ? Promise.resolve(null)
    : getJson<unknown>(`${base}${path}`, true).then((value) => {
      if (value === null) throw new DataError(`Required ${artifact} artifact is absent for this replay step.`);
      return value;
    });
  const planTime = safePathSegment(at);
  const forecastIssue = [...(manifest.issued_at || [])].filter((value) => Date.parse(value) <= Date.parse(at)).sort().at(-1);

  const [gaugesRaw, forecastsRaw, roadsRaw, plansRaw, unreachableRaw, sheltersRaw, coloniesRaw,
    roadGeometryRaw, floodIndexRaw, trapRaw] = await Promise.all([
    g('gauges', `${prefix}/gauges.json`),
    forecastIssue ? g('forecasts', `${prefix}/forecasts/${safePathSegment(forecastIssue)}.json`) : Promise.resolve([]),
    g('roads', `${prefix}/roads/${planTime}.json`),
    g('plans', `${prefix}/plans/${planTime}.json`),
    getJson<unknown>(`${base}${prefix}/plans/${planTime}.unreachable.json`, true),
    getJson<unknown>(`${base}/static/shelters.geojson`, true),
    getJson<unknown>(`${base}/static/colonies.geojson`, true),
    getJson<unknown>(`${base}/static/osm/roads.geojson`, true),
    g('depth', `${prefix}/depth/index.json`),
    getJson<TrapSummary>(`${base}${prefix}/routing/trap_summary.json`, true),
  ]);

  const gauges = Array.isArray(gaugesRaw) ? gaugesRaw as GaugeReading[] : [];
  const forecasts = Array.isArray(forecastsRaw) ? forecastsRaw as ForecastNode[] : [];
  const plans = Array.isArray(plansRaw) ? plansRaw as EvacuationPlan[] : [];
  const roads = Array.isArray(roadsRaw) ? roadsRaw as RoadSegmentStatus[] : null;
  const sheltersFc = featureCollection(sheltersRaw);
  const shelters = (sheltersFc?.features || []).map((feature) => feature.properties as Shelter).filter((item) => item?.shelter_id);
  const thresholds = await getJson<Array<{ colony_id: string; wet_at_level_m: number; cutoff_at_level_m: number; buffer_m: number }>>(
    `${base}/models/inundation/v1/colony_thresholds.json`, true,
  );
  const floodIndex = Array.isArray(floodIndexRaw) ? floodIndexRaw as Array<{ valid_at: string; geojson: string }> : [];
  const floodEntry = floodIndex.find((item) => item.valid_at === at);
  let flood: GeoJSON.FeatureCollection | null = null;
  if (floodEntry?.geojson) {
    const path = floodEntry.geojson.startsWith('/') ? floodEntry.geojson : `/${floodEntry.geojson}`;
    flood = featureCollection(await getJson<unknown>(`${base}${path}`, true));
  }
  const artifactLayers: Record<string, ReplayStep['sources'][string]> = {
    gauges: inferLayer(manifest, 'gauges'), plans: inferLayer(manifest, 'plans'), roads: inferLayer(manifest, 'roads'),
    shelters: shelters.length ? 'static' : 'missing', colonies: featureCollection(coloniesRaw) ? 'static' : 'missing',
    flood: flood ? inferLayer(manifest, 'depth') : 'missing', thresholds: thresholds ? 'static' : 'missing',
    unreachable: unreachableRaw ? inferLayer(manifest, 'plans') : 'missing',
  };
  const coreSources = ['gauges', 'plans', 'roads', 'flood'].map((key) => artifactLayers[key]);
  const sourceMode: ReplayStep['sourceMode'] = coreSources.includes('fixture') || coreSources.includes('missing') ? 'fixture' : 'static';
  return {
    manifest, at,
    gauges: gauges.filter((row) => Date.parse(row.ts) <= Date.parse(at)), forecasts,
    flood, roads, roadGeometry: featureCollection(roadGeometryRaw), plans, shelters,
    colonies: featureCollection(coloniesRaw),
    unreachable: Array.isArray(unreachableRaw) ? unreachableRaw as UnreachableEntry[] : [],
    thresholds: thresholds || [], trapSummary: trapRaw || null, sources: artifactLayers,
    sourceMode, sourceNote: sourceMode === 'fixture' ? 'Some selected scenario layers are declared fixtures in the manifest; check the per-layer source ledger.' : 'CloudFront static artefacts · source status follows the scenario manifest.',
  };
}

async function loadFixtureStep(at: string): Promise<ReplayStep> {
  const read = async <T,>(name: string) => getJson<T>(`/fixtures/${name}.json`).then((value) => {
    if (value === null) throw new DataError(`Fixture ${name} is unavailable.`);
    return value;
  });
  const [manifest, gauges, planIndex, roadFixture, shelters, forecastFixture, depthIndex,
    unreachableFixture, thresholds, trapSummary] = await Promise.all([
    read<Manifest>('manifest'), read<GaugeReading[]>('gauges'), read<Record<string, EvacuationPlan[]>>('evacuation_plans'),
    read<RoadSegmentStatus[]>('road_segment_status'), read<Shelter[]>('shelters'), read<ForecastNode[]>('forecast_nodes'),
    read<Array<{ valid_at: string; level_m_ref: number }>>('depth_index'), read<UnreachableEntry[]>('plans_unreachable'),
    read<Array<{ colony_id: string; wet_at_level_m: number; cutoff_at_level_m: number; buffer_m: number }>>('colony_thresholds'),
    read<TrapSummary>('trap_summary'),
  ]);
  const plans = planIndex[at] || [];
  const isHeroStep = at === manifest.default_at;
  const forecasts = forecastFixture.filter((node) => Date.parse(node.issued_at) <= Date.parse(at));
  const trap = trapSummary.steps.some((item) => item.valid_at === at) ? trapSummary : null;
  const sources: ReplayStep['sources'] = {
    gauges: 'fixture', plans: plans.length ? 'fixture' : 'missing', roads: isHeroStep ? 'fixture' : 'missing',
    shelters: 'fixture', colonies: 'missing', flood: depthIndex.some((item) => item.valid_at === at) ? 'fixture' : 'missing',
    thresholds: 'fixture', unreachable: isHeroStep ? 'fixture' : 'missing',
  };
  return {
    manifest, at,
    gauges: gauges.filter((row) => Date.parse(row.ts) <= Date.parse(at)), forecasts,
    flood: null, roads: isHeroStep ? roadFixture : null, roadGeometry: null, plans, shelters,
    colonies: null, unreachable: isHeroStep ? unreachableFixture : [], thresholds, trapSummary: trap,
    sources, sourceMode: 'fixture',
    sourceNote: 'Fixture replay · routing, road and shelter examples are synthetic development data.',
  };
}

export async function loadManifest(): Promise<Manifest> {
  if (STATIC_BASE) {
    try {
      const manifest = await getJson<Manifest>(`${STATIC_BASE}/scenarios/${safePathSegment(SCENARIO)}/manifest.json`);
      if (manifest) return manifest;
    } catch { /* A static manifest failure selects the complete fixture source. */ }
  }
  const manifest = await getJson<Manifest>('/fixtures/manifest.json');
  if (!manifest) throw new DataError('No replay manifest is available.');
  return manifest;
}

export async function loadReplayStep(at: string): Promise<ReplayStep> {
  if (STATIC_BASE) {
    try { return await loadStaticStep(at); }
    catch { /* A step is resolved as a whole. Never combine static and fixture layers. */ }
  }
  return loadFixtureStep(at);
}

export async function loadDispatchCache(at: string, colonyId: string): Promise<DispatchCard | null> {
  if (STATIC_BASE) {
    const url = `${STATIC_BASE}/scenarios/${safePathSegment(SCENARIO)}/dispatch_cache/${safePathSegment(at)}/${safePathSegment(colonyId)}.json`;
    const card = await getJson<DispatchCard>(url, true);
    if (card?.plan_ref?.computed_at === at && card.plan_ref.colony_id === colonyId) return card;
  }
  const sample = await getJson<{ key?: string; card?: DispatchCard }>('/fixtures/dispatch_cache_sample.json', true);
  return sample?.card?.plan_ref?.computed_at === at && sample.card.plan_ref.colony_id === colonyId ? sample.card : null;
}

function apiUrl(path: string, at?: string): string {
  if (!API_BASE) throw new DataError('The Jaltaranga write API is not configured.');
  const url = new URL(`${API_BASE}${path}`);
  if (at) url.searchParams.set('at', at);
  return url.toString();
}

async function apiRequest<T>(path: string, init: RequestInit, at?: string): Promise<T> {
  const response = await fetch(apiUrl(path, at), {
    ...init, headers: { Accept: 'application/json', 'Content-Type': 'application/json', ...init.headers },
  });
  const value = await response.json().catch(() => null) as T | { error?: { message?: string } } | null;
  if (!response.ok) throw new DataError((value as { error?: { message?: string } } | null)?.error?.message || `API request failed (${response.status}).`, response.status);
  if (!value) throw new DataError('The API returned an empty response.');
  return value as T;
}

export async function draftDispatch(at: string, colonyId: string, fresh = false): Promise<DispatchCard> {
  const path = `/scenarios/${safePathSegment(SCENARIO)}/colonies/${safePathSegment(colonyId)}/dispatch${fresh ? '?fresh=1' : ''}`;
  const card = await apiRequest<DispatchCard>(path, { method: 'POST', body: '{}' }, at);
  if (card.plan_ref?.colony_id !== colonyId || card.plan_ref?.computed_at !== at) throw new DataError('Dispatch response does not match the selected colony and replay step.');
  return card;
}

export async function approveDispatch(dispatchId: string): Promise<DispatchCard> {
  return apiRequest<DispatchCard>(`/dispatches/${safePathSegment(dispatchId)}/approve`, { method: 'POST', body: JSON.stringify({ approved_by: 'officer-demo' }) });
}

export async function listDispatches(): Promise<DispatchCard[]> {
  return apiRequest<DispatchCard[]>('/dispatches?scenario_id=yamuna-2023-07', { method: 'GET' });
}

export async function submitReport(payload: Record<string, unknown>, photo: Blob | null): Promise<{ response: ReportPostResponse; photoUploaded: boolean }> {
  const response = await apiRequest<ReportPostResponse>('/reports', {
    method: 'POST', body: JSON.stringify({ ...payload, has_photo: Boolean(photo) }),
  }, typeof payload.replay_at === 'string' ? payload.replay_at : undefined);
  if (!response.upload || !photo) return { response, photoUploaded: !photo };
  const form = new FormData();
  Object.entries(response.upload.fields).forEach(([key, value]) => form.append(key, value));
  form.append('file', photo, 'field-report.jpg');
  const upload = await fetch(response.upload.url, { method: 'POST', body: form });
  if (!upload.ok) return { response, photoUploaded: false };
  return { response, photoUploaded: true };
}

export function hasApiConfiguration(): boolean { return Boolean(API_BASE); }
export function getStaticBase(): string { return STATIC_BASE; }

