import { describe, expect, it } from 'vitest';
import { formatCountdown, formatIST, readReplayTime, snapToValidAt, writeReplayTime } from './replay';
import type { Manifest } from '../shared/types';

const steps = ['2023-07-11T03:00:00+05:30', '2023-07-11T06:00:00+05:30', '2023-07-11T09:00:00+05:30'];

describe('replay timestamp handling', () => {
  it('snaps to a manifest step and resolves ties to the earlier step', () => {
    expect(snapToValidAt('2023-07-11T04:00:00+05:30', steps)).toBe(steps[0]);
    expect(snapToValidAt('2023-07-11T05:00:00+05:30', steps)).toBe(steps[1]);
    expect(snapToValidAt(null, steps)).toBe(steps[0]);
  });

  it('keeps the +05:30 offset encoded in a URL query', () => {
    window.history.replaceState({}, '', '/command?view=command');
    writeReplayTime(steps[2]);
    expect(new URL(window.location.href).searchParams.get('at')).toBe(steps[2]);
    expect(window.location.search).toContain('%2B05%3A30');
  });

  it('uses the replay manifest and formats Indian Standard Time', () => {
    const manifest: Manifest = { scenario_id: 'x', mode: 'replay', start: steps[0], end: steps[2], valid_at: steps, default_at: steps[2] };
    expect(manifest.valid_at).toContain(snapToValidAt(manifest.default_at, manifest.valid_at));
    expect(readReplayTime(manifest, '')).toBe(steps[2]);
    expect(formatIST('2023-07-11T09:00:00+05:30', { hour: '2-digit', minute: '2-digit', hour12: false })).toContain('09:00');
  });
});

describe('time-to-water display', () => {
  it('shows a rounded countdown without altering plan timestamps', () => {
    expect(formatCountdown(steps[2], '2023-07-11T11:36:00+05:30')).toEqual({ kind: 'future', text: '2 h 40 min' });
  });

  it('distinguishes elapsed and unknown estimates', () => {
    expect(formatCountdown(steps[2], steps[1]).kind).toBe('elapsed');
    expect(formatCountdown(steps[2], null).kind).toBe('unknown');
  });

  it('does not generate negative or sub-ten-minute forecasts', () => {
    expect(formatCountdown(steps[2], '2023-07-11T09:01:00+05:30').text).toBe('10 min');
    expect(formatCountdown(steps[2], '2023-07-11T08:00:00+05:30').kind).toBe('elapsed');
  });
});

