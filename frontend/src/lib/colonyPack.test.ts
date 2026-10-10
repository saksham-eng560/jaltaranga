import { describe, expect, it } from 'vitest';
import { packIsStale } from './colonyPack';

describe('offline pack freshness', () => {
  it('marks a pack stale after two hours, not before', () => {
    const now = Date.parse('2023-07-11T12:00:00Z');
    expect(packIsStale('2023-07-11T10:00:01Z', now)).toBe(false);
    expect(packIsStale('2023-07-11T10:00:00Z', now)).toBe(false);
    expect(packIsStale('2023-07-11T09:59:59Z', now)).toBe(true);
  });
});

