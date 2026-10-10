export function lineCoordinates(feature: unknown): [number, number][] {
  const candidate = feature as { geometry?: { type?: string; coordinates?: unknown } };
  if (candidate?.geometry?.type !== 'LineString' || !Array.isArray(candidate.geometry.coordinates)) return [];
  return candidate.geometry.coordinates.filter((pair): pair is [number, number] =>
    Array.isArray(pair) && pair.length >= 2 && Number.isFinite(pair[0]) && Number.isFinite(pair[1]),
  );
}

export function projectLine(coordinates: [number, number][], width: number, height: number, padding = 36): string {
  return projectLines([coordinates], width, height, padding)[0] || '';
}

export function projectLines(paths: [number, number][][], width: number, height: number, padding = 36): string[] {
  const all = paths.flat();
  if (all.length < 2) return paths.map(() => '');
  const xs = all.map(([x]) => x);
  const ys = all.map(([, y]) => y);
  const minX = Math.min(...xs), maxX = Math.max(...xs), minY = Math.min(...ys), maxY = Math.max(...ys);
  const dx = Math.max(maxX - minX, 1e-6), dy = Math.max(maxY - minY, 1e-6);
  const scale = Math.min((width - 2 * padding) / dx, (height - 2 * padding) / dy);
  const usedWidth = dx * scale, usedHeight = dy * scale;
  const offsetX = (width - usedWidth) / 2, offsetY = (height - usedHeight) / 2;
  return paths.map((coordinates) => {
    if (coordinates.length < 2) return '';
    return coordinates.map(([x, y], index) => {
      const px = offsetX + (x - minX) * scale;
      const py = height - (offsetY + (y - minY) * scale);
      return `${index === 0 ? 'M' : 'L'}${px.toFixed(2)},${py.toFixed(2)}`;
    }).join(' ');
  });
}

