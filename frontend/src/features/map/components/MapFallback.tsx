import { useMemo } from 'react';
import type { Coordinate, RouteOption, Checkpoint } from '../../routing/types';
import type { CorridorForecast } from '../../forecast/types';
import { corridorFeatures, routeFeatures, schematicProjection } from '../utils/mapData';
import { formatNumber } from '../../routing/utils/format';

export function MapFallback({ routes, selectedId, corridor, hour, onCheckpoint, onSelect }: {
  routes: RouteOption[]; selectedId: string; corridor: CorridorForecast | null; hour: number;
  onCheckpoint: (point: Checkpoint) => void; onSelect: (id: string) => void;
}) {
  const project = useMemo(() => schematicProjection(routes), [routes]);
  const lines = useMemo(() => routeFeatures(routes, selectedId), [routes, selectedId]);
  const cells = useMemo(() => corridorFeatures(corridor, hour), [corridor, hour]);
  const selected = routes.find(route => route.id === selectedId);
  const path = (rings: number[][][]) => rings.map(ring => ring.map((coordinate, index) => `${index ? 'L' : 'M'}${project(coordinate as Coordinate).join(' ')}`).join(' ') + 'Z').join(' ');
  return <svg viewBox="0 0 1000 720" preserveAspectRatio="none" className="absolute inset-0 h-full w-full" role="img" aria-label="Route schematic">
    <defs><pattern id="map-grid" width="40" height="40" patternUnits="userSpaceOnUse"><path d="M40 0H0V40" stroke="var(--color-map-road)" strokeWidth=".45" fill="none" /></pattern></defs>
    <rect width="1000" height="720" fill="var(--color-map-land)" /><rect width="1000" height="720" fill="url(#map-grid)" />
    {cells.features.map(feature => <path key={feature.id} fill={feature.properties?.color} opacity={feature.properties?.opacity} fillRule="evenodd"
      d={feature.geometry.type === 'Polygon' ? path(feature.geometry.coordinates) : feature.geometry.coordinates.map(path).join(' ')} />)}
    {lines.features.map((feature, index) => <polyline key={index} points={feature.geometry.coordinates.map(point => project(point as Coordinate).join(',')).join(' ')}
      fill="none" stroke={feature.properties?.color} strokeWidth={feature.properties?.width} strokeLinejoin="round" className="cursor-pointer"
      onClick={() => onSelect(feature.properties!.id)} />)}
    {selected?.checkpoints.map(point => {
      const [x, y] = project(point.coordinate);
      return <g key={point.id} transform={`translate(${x},${y})`} role="button" tabIndex={0}
        aria-label={`Checkpoint ${point.number} at mile ${formatNumber(point.miles)}`}
        onClick={() => onCheckpoint(point)} onKeyDown={event => { if (event.key === 'Enter' || event.key === ' ') { event.preventDefault(); onCheckpoint(point); } }} className="cursor-pointer">
        <circle r="10" fill="var(--color-panel)" stroke="var(--color-accent)" strokeWidth="2" />
        <text textAnchor="middle" dy="4" fontSize="11" fill="var(--color-ink)">{point.number}</text>
      </g>;
    })}
    <text x="18" y="700" fontSize="11" fill="var(--color-map-label)">Route schematic · Geographic basemap unavailable</text>
  </svg>;
}
