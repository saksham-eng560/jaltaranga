import { describe, expect, it } from 'vitest';
import { lineCoordinates, projectLine, projectLines } from './geo';

describe('route geometry rendering', () => {
  it('accepts only valid LineString coordinate pairs', () => {
    expect(lineCoordinates({ geometry: { type: 'LineString', coordinates: [[77.2, 28.6], ['bad', 28.7], [77.3, 28.7]] } })).toEqual([[77.2, 28.6], [77.3, 28.7]]);
    expect(lineCoordinates({ geometry: { type: 'Point', coordinates: [77.2, 28.6] } })).toEqual([]);
  });

  it('projects route coordinates to a stable viewbox path', () => {
    expect(projectLine([[77.2, 28.6], [77.3, 28.7]], 600, 340)).toMatch(/^M/);
    expect(projectLine([[77.2, 28.6]], 600, 340)).toBe('');
  });

  it('projects primary and backup routes in the same geographic bounds', () => {
    const [primary, backup] = projectLines([[[77.2, 28.6], [77.25, 28.65]], [[77.2, 28.6], [77.3, 28.7]]], 600, 340);
    expect(primary?.split(' ')[0]).toBe(backup?.split(' ')[0]);
    expect(primary?.split(' ').at(-1)).not.toBe(backup?.split(' ').at(-1));
  });
});

