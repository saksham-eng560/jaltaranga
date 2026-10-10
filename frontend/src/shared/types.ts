export type Timestamp = string;

export interface Manifest {
  scenario_id: string;
  mode: 'replay' | 'live';
  title_en?: string | null;
  title_hi?: string | null;
  start: Timestamp;
  end: Timestamp;
  step_min?: number;
  valid_at: Timestamp[];
  issued_at?: Timestamp[];
  default_at?: Timestamp | null;
  ref_station?: string;
  thresholds?: Record<string, number>;
  events?: Array<{ kind: string; ts: Timestamp; level_m?: number | null; ts_verified?: boolean }>;
  artefacts?: Record<string, 'real' | 'fixture' | 'missing'>;
  sources?: Array<Record<string, unknown>>;
  data_version?: string | null;
}

export interface GaugeReading {
  station_id: string;
  ts: Timestamp;
  level_m: number | null;
  discharge_cumecs?: number | null;
  source: 'cwc' | 'floodhub' | 'digitized' | 'synthetic' | 'glofas';
  source_ref?: string | null;
  qc_flag: 'ok' | 'imputed' | 'suspect';
  note?: string | null;
}

export interface ForecastNode {
  scenario_id: string;
  issued_at: Timestamp;
  station_id: string;
  horizon_h: number;
  valid_at: Timestamp;
  level_m: number;
  lo_m: number;
  hi_m: number;
  coverage: number;
  model: string;
}

export interface RouteOption {
  shelter_id: string;
  route_geojson: { type: string; geometry: { type: string; coordinates: number[][] }; properties?: Record<string, unknown> };
  distance_m: number;
  walk_min: number;
  via_names_en?: string[];
  via_names_hi?: string[];
  max_depth_m: number;
}

export interface AvoidEntry { name_en: string; name_hi: string; cutoff_at: Timestamp; edge_ids?: string[] }

export interface EvacuationPlan {
  scenario_id: string;
  colony_id: string;
  computed_at: Timestamp;
  t_submersion: Timestamp;
  t_submersion_earliest?: Timestamp | null;
  t_submersion_latest?: Timestamp | null;
  lead_time_h: number;
  primary: RouteOption;
  backup?: RouteOption | null;
  avoid: AvoidEntry[];
  priority: number;
  ext?: { assigned_people?: number | null; demand_people?: number | null; replanned_due_to?: string | null } | null;
}

export interface Shelter {
  shelter_id: string;
  name_en: string;
  name_hi: string;
  location: [number, number];
  free_beds: number;
  capacity?: number;
  occupied?: number;
  type?: string;
  updated_at?: Timestamp;
}

export interface RoadSegmentStatus {
  edge_id: string;
  status: 'green' | 'amber' | 'red';
  depth_m?: number | null;
  cutoff_at?: Timestamp | null;
  reason?: string;
}

export interface UnreachableEntry { colony_id: string; reason: string; population?: number }

export interface DispatchCard {
  dispatch_id: string;
  plan_ref: { scenario_id: string; colony_id: string; computed_at: Timestamp };
  alert_type: 'URGENT_EVACUATION_DISPATCH' | 'PREPARE' | 'ALL_CLEAR' | 'SHELTER_IN_PLACE';
  message_hi: string;
  message_en: string;
  sms_hi: string;
  audio_url_hi?: string | null;
  validation: { passed: boolean; checks: string[]; fallback_used: boolean; failed_checks?: string[]; fallback_fields?: string[]; source?: string };
  status: 'draft' | 'approved' | 'sent' | 'acknowledged';
  approved_by?: string | null;
  ts: Timestamp;
}

export interface FieldReport {
  report_id: string;
  ts: Timestamp;
  location: [number, number];
  kind: 'water_depth' | 'road_blocked' | 'shelter_full' | 'sos';
  depth_cm?: number | null;
  photo_key?: string | null;
  reporter_id: string;
  trust: number;
  verified: boolean;
}

export interface TrapSummary {
  scenario_id: string;
  steps: Array<{ valid_at: Timestamp; trapped_population: number; colonies: string[]; roads: string[] }>;
  max_trapped_population: number;
  max_at: Timestamp;
}

export type LayerSource = 'static' | 'fixture' | 'cached' | 'missing';

export interface ReplayStep {
  manifest: Manifest;
  at: Timestamp;
  gauges: GaugeReading[];
  forecasts: ForecastNode[];
  flood: GeoJSON.FeatureCollection | null;
  roads: RoadSegmentStatus[] | null;
  roadGeometry: GeoJSON.FeatureCollection | null;
  plans: EvacuationPlan[];
  shelters: Shelter[];
  colonies: GeoJSON.FeatureCollection | null;
  unreachable: UnreachableEntry[];
  thresholds: Array<{ colony_id: string; wet_at_level_m: number; cutoff_at_level_m: number; buffer_m: number }>;
  trapSummary: TrapSummary | null;
  sources: Record<string, LayerSource>;
  sourceMode: 'static' | 'fixture';
  sourceNote: string;
}

export interface ReportPostResponse { report: FieldReport; upload: { url: string; fields: Record<string, string> } | null }
