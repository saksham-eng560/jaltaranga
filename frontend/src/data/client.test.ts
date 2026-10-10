import { describe, expect, it } from 'vitest';
import { safePathSegment, withReplayQuery } from './client';

describe('static URL encoding', () => {
  it('encodes timestamp segments including plus and colons', () => {
    expect(safePathSegment('2023-07-11T09:00:00+05:30')).toBe('2023-07-11T09%3A00%3A00%2B05%3A30');
  });

  it('encodes the timezone offset in query strings without changing the decoded value', () => {
    const at = '2023-07-11T09:00:00+05:30';
    const url = new URL(withReplayQuery('/api/plans', at));
    expect(url.searchParams.get('at')).toBe(at);
    expect(url.search).toContain('%2B05%3A30');
  });
});

