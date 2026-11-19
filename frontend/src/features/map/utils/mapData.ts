import type { FeatureCollection, LineString, MultiPolygon, Polygon } from 'geojson';
import type { Coordinate, RouteOption } from '../../routing/types';
import type { CorridorForecast } from '../../forecast/types';

export function readMapTheme() {
  const style = getComputedStyle(document.documentElement);
  const color = (name: string) => style.getPropertyValue(`--color-${name}`).trim();
  return { accent: color('accent'), alternate: color('route-alternate'), third: color('route-third'),
    low: color('low'), moderate: color('moderate'), high: color('high'), severe: color('severe'),
    blocked: color('no-travel'), panel: color('panel'), muted: color('muted'), unknown: color('subtle'),
    land: color('map-land'), water: color('map-water'), road: color('map-road'), label: color('map-label') };
}

export function routeFeatures(routes: RouteOption[], selected: string): FeatureCollection<LineString> {
  const theme = readMapTheme();
  return { type: 'FeatureCollection', features: [...routes]
    .sort((a, b) => Number(a.id === selected) - Number(b.id === selected))
    .flatMap((route, index) => route.segments.map(segment => {
      const color = segment.risk === null ? theme.unknown : segment.risk === 'no-travel' ? theme.blocked
        : segment.risk === 'severe' ? theme.severe : segment.risk === 'high' ? theme.high
        : segment.risk === 'moderate' ? theme.moderate : route.id === selected ? theme.accent
        : index % 2 === 0 ? theme.alternate : theme.third;
      return { type: 'Feature' as const, geometry: { type: 'LineString' as const, coordinates: segment.geometry },
        properties: { id: route.id, color, width: route.id === selected ? 4 : 2.5, opacity: route.id === selected ? 1 : .75 } };
    })) };
}

export function corridorFeatures(data: CorridorForecast | null, hour: number): FeatureCollection<Polygon | MultiPolygon> {
  if (!data) return { type: 'FeatureCollection', features: [] };
  const theme = readMapTheme();
  const colors = [theme.low, theme.moderate, theme.high, theme.severe, theme.blocked];
  return { type: 'FeatureCollection', features: data.grid.cells.map((cell, index) => {
    const score = data.frames[hour]?.riskScores[index] ?? null;
    return { type: 'Feature' as const, id: cell.id, geometry: cell.geometry,
      properties: { color: score === null ? theme.unknown : colors[score], opacity: score === null ? .08 : .14 + score * .065, score } };
  }) };
}

export function routeBounds(routes: RouteOption[]): [[number, number], [number, number]] {
  const points = routes.flatMap(route => route.geometry);
  if (!points.length) return [[-89.1, 39.4], [-85.4, 42.2]];
  const reference = points[0][0];
  let west = Infinity, east = -Infinity, south = Infinity, north = -Infinity;
  for (const [rawLon, lat] of points) {
    const lon = reference + ((rawLon - reference + 180) % 360 + 360) % 360 - 180;
    west = Math.min(west, lon); east = Math.max(east, lon);
    south = Math.min(south, lat); north = Math.max(north, lat);
  }
  return [[west - .05, south - .05], [east + .05, north + .05]];
}

export function schematicProjection(routes: RouteOption[]) {
  const [[west, south], [east, north]] = routeBounds(routes);
  const reference = (west + east) / 2;
  return ([rawLon, lat]: Coordinate) => {
    const lon = reference + ((rawLon - reference + 180) % 360 + 360) % 360 - 180;
    return [80 + (lon - west) / Math.max(east - west, .1) * 840,
      60 + (north - lat) / Math.max(north - south, .1) * 600];
  };
}
