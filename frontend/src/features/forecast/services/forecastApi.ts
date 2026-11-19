import { apiRequest, ApiError } from '../../../lib/apiClient';
import type { CorridorForecast } from '../types';

export async function fetchCorridor(analysisId: string, signal: AbortSignal): Promise<CorridorForecast> {
  const data = await apiRequest<CorridorForecast>(`/analyses/${encodeURIComponent(analysisId)}/corridor-forecast/`, { signal });
  if (!data?.grid || data.analysisId !== analysisId || !Array.isArray(data.grid.cells) || !Array.isArray(data.frames) || data.frames.length !== 49
      || !Number.isFinite(Date.parse(data.forecastStart))
      || !Number.isFinite(Date.parse(data.expiresAt)) || data.grid.cellCount !== data.grid.cells.length
    || data.frames.some((frame, index) => !frame || !Number.isFinite(Date.parse(frame.time)) || frame.offsetHours !== index || !Array.isArray(frame.riskScores)
        || frame.riskScores.length !== data.grid.cells.length
        || frame.riskScores.some(score => score !== null && (!Number.isInteger(score) || score < 0 || score > 4)))) {
    throw new ApiError('The corridor forecast was incomplete. Please try again.', 'invalid_response');
  }
  return data;
}
