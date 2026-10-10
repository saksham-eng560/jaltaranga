export interface ForecastNode {
  scenario_id: string;
  issued_at: string;
  station_id: string;
  horizon_h: number;
  valid_at: string;
  level_m: number;
  lo_m: number;
  hi_m: number;
  coverage: number;
  model: string;
}

export interface ColonyThreshold {
  colony_id: string;
  wet_at_level_m: number | null;
  cutoff_at_level_m: number | null;
  buffer_m: number;
}

export interface EvacuationPlan {
  plan_id: string;
  colony_id: string;
  colony_name: string;
  colony_name_hi?: string;
  population: number;
  priority: number;
  lead_time_h: number;
  shelter_name: string;
  route_summary: string;
  route_summary_hi: string;
  avoid_roads: string[];
}

export interface WhatIfResponse {
  level_m: number;
  wet_colonies: { colony_id: string; wet_at_level_m: number }[];
  cut_colonies: { colony_id: string }[];
  cut_edge_ids: string[];
  flood_geojson_url?: string;
}

export interface DispatchCard {
  dispatch_id: string;
  colony_id: string;
  status: 'draft' | 'approved' | 'sent';
  message_hi: string;
  message_en: string;
  audio_url_hi?: string;
  validation: {
    passed: boolean;
    checks: Record<string, boolean>;
  };
}
