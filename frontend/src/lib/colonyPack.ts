import { get, set } from 'idb-keyval';
import type { DispatchCard, EvacuationPlan, Shelter, Timestamp } from '../shared/types';

const STORE = 'jaltaranga-colony-packs-v1';

export interface ColonyPack {
  colonyId: string;
  scenarioId: string;
  at: Timestamp;
  savedAt: Timestamp;
  plan: EvacuationPlan;
  shelter: Shelter | null;
  dispatch: DispatchCard | null;
  audioBlob: Blob | null;
  source: 'static' | 'fixture';
}

export async function saveColonyPack(pack: ColonyPack): Promise<void> {
  await set(`${STORE}:${pack.colonyId}`, pack);
}

export async function getColonyPack(colonyId: string): Promise<ColonyPack | undefined> {
  return get<ColonyPack>(`${STORE}:${colonyId}`);
}

export async function fetchAudioBlob(card: DispatchCard | null): Promise<Blob | null> {
  if (!card?.validation.passed || !card.audio_url_hi) return null;
  try {
    const response = await fetch(card.audio_url_hi, { mode: 'cors' });
    return response.ok ? await response.blob() : null;
  } catch { return null; }
}

export function packIsStale(savedAt: Timestamp, now = Date.now()): boolean {
  return now - Date.parse(savedAt) > 2 * 60 * 60 * 1000;
}
