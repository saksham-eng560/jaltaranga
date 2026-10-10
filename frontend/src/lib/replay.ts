import type { Manifest } from '../shared/types';

export function snapToValidAt(requested: string | null | undefined, validAt: string[]): string {
  if (!validAt.length) throw new Error('Replay manifest has no valid timestamps.');
  const wanted = requested ? Date.parse(requested) : Number.NaN;
  if (!Number.isFinite(wanted)) return validAt[0];
  return validAt.reduce((closest, candidate) =>
    Math.abs(Date.parse(candidate) - wanted) < Math.abs(Date.parse(closest) - wanted) ? candidate : closest,
  );
}

export function readReplayTime(manifest: Manifest, search = window.location.search): string {
  const value = new URLSearchParams(search).get('at');
  return snapToValidAt(value || manifest.default_at, manifest.valid_at);
}

export function writeReplayTime(at: string, replace = true): void {
  const url = new URL(window.location.href);
  url.searchParams.set('at', at);
  window.history[replace ? 'replaceState' : 'pushState']({}, '', url);
}

export function formatIST(value: string | null | undefined, options?: Intl.DateTimeFormatOptions): string {
  if (!value || !Number.isFinite(Date.parse(value))) return 'Time unavailable';
  return new Intl.DateTimeFormat('en-IN', {
    timeZone: 'Asia/Kolkata', day: '2-digit', month: 'short', hour: '2-digit', minute: '2-digit',
    hour12: false, ...options,
  }).format(new Date(value));
}

export function formatCountdown(from: string, to: string | null | undefined): { kind: 'future' | 'elapsed' | 'unknown'; text: string } {
  const start = Date.parse(from);
  const end = to ? Date.parse(to) : Number.NaN;
  if (!Number.isFinite(start) || !Number.isFinite(end)) return { kind: 'unknown', text: 'Time to water unavailable' };
  const deltaMinutes = Math.round((end - start) / 60_000);
  if (deltaMinutes <= 0) return { kind: 'elapsed', text: 'The planned water-arrival time has passed' };
  const rounded = Math.max(10, Math.round(deltaMinutes / 10) * 10);
  const hours = Math.floor(rounded / 60);
  const minutes = rounded % 60;
  const text = hours > 0 ? `${hours} h${minutes ? ` ${minutes} min` : ''}` : `${minutes} min`;
  return { kind: 'future', text };
}

