import type { CorridorForecast } from '../types';
import type { TripResult } from '../../routing/types';

export function buildDemoCorridor(result: TripResult): CorridorForecast {
  const cells = [[-88.1, 40.5], [-87.8, 40.8], [-86.3, 41.4], [-86.6, 41.1]].map(([lon, lat], index) => ({
    id: `demo-${index}`, coordinate: [lon, lat] as [number, number],
    geometry: { type: 'Polygon' as const, coordinates: [[[lon - .17, lat - .17], [lon + .17, lat - .17], [lon + .17, lat + .17], [lon - .17, lat + .17], [lon - .17, lat - .17]]] },
  }));
  return {
    analysisId: 'demo', forecastStart: result.forecastStart, expiresAt: result.expiresAt, complete: true,
    grid: { cellCount: cells.length, spacingMiles: 25, coarsened: false, cells },
    frames: Array.from({ length: 49 }, (_, hour) => ({ offsetHours: hour,
      time: new Date(Date.parse(result.forecastStart) + hour * 3_600_000).toISOString(),
      riskScores: cells.map((_, i) => 1 + ((i + Math.floor(hour / 12)) % 4)), complete: true, missingCellCount: 0 })),
    riskLevels: [], forecastMetadata: { provider: 'Sample data', retrievedAt: new Date().toISOString() }, warnings: [],
  };
}
