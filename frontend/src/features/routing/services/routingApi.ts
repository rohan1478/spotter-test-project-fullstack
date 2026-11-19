import { apiRequest, ApiError } from '../../../lib/apiClient';
import type { ResolvedPlace, TripInput, TripResult } from '../types';

const risks = new Set(['low', 'moderate', 'high', 'severe', 'no-travel']);
const isRisk = (risk: unknown) => risk === null || (typeof risk === 'string' && risks.has(risk));
const isNumber = (value: unknown) => typeof value === 'number' && Number.isFinite(value);

export async function searchLocations(query: string, signal: AbortSignal) {
  const response = await apiRequest<{ results: ResolvedPlace[]; requiresSelection: boolean; attribution: string }>(
    `/routes/places/?q=${encodeURIComponent(query)}&limit=5`, { signal },
  );
  if (!response || !Array.isArray(response.results) || response.results.some(place => !place
      || typeof place.id !== 'string' || typeof place.label !== 'string' || typeof place.timeZone !== 'string'
      || !Array.isArray(place.coordinate) || place.coordinate.length !== 2 || !place.coordinate.every(isNumber))) {
    throw new ApiError('The location response was incomplete. Please try again.', 'invalid_response');
  }
  return response;
}

export async function compareRoutes(trip: TripInput, signal: AbortSignal): Promise<TripResult> {
  const result = await apiRequest<TripResult>('/routes/compare/', {
    method: 'POST', body: JSON.stringify({ ...trip, departureTimeZone: trip.originPlace?.timeZone }), signal,
  });
  if (!result || !Array.isArray(result.routes) || typeof result.analysisId !== 'string'
      || !Array.isArray(result.warnings) || !(result.recommendedRouteId === null || typeof result.recommendedRouteId === 'string')
      || !Number.isFinite(Date.parse(result.expiresAt)) || !Number.isFinite(Date.parse(result.forecastStart))
      || result.routes.some(route => !Array.isArray(route.geometry) || !Array.isArray(route.checkpoints)
        || !Array.isArray(route.segments) || !Array.isArray(route.exposure) || !isRisk(route.risk)
        || !isNumber(route.distance) || !isNumber(route.duration)
        || route.checkpoints.some(point => !isRisk(point.risk) || !Array.isArray(point.coordinate)
          || !Number.isFinite(Date.parse(point.arrival)) || typeof point.timeZone !== 'string'
          || [point.wind, point.rain, point.snow].some(value => value !== null && !isNumber(value))))) {
    throw new ApiError('The routing response was incomplete. Please try again.', 'invalid_response');
  }
  return result;
}
