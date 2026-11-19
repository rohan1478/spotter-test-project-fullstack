import type { MultiPolygon, Polygon } from 'geojson';
import type { Coordinate, RiskLevel } from '../routing/types';

export interface CorridorForecast {
  analysisId: string;
  forecastStart: string;
  expiresAt: string;
  complete: boolean;
  grid: {
    cellCount: number;
    spacingMiles: number;
    coarsened: boolean;
    cells: { id: string; coordinate: Coordinate; geometry: Polygon | MultiPolygon }[];
  };
  frames: { offsetHours: number; time: string; riskScores: (number | null)[]; complete: boolean; missingCellCount: number }[];
  riskLevels: { score: number; risk: RiskLevel; label: string }[];
  forecastMetadata: { provider: string; retrievedAt: string; attribution?: string };
  warnings: { code: string; message: string }[];
}

export type ForecastStatus = 'idle' | 'loading' | 'ready' | 'error';
