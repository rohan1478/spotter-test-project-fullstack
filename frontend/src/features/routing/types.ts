export type RiskLevel = 'low' | 'moderate' | 'high' | 'severe' | 'no-travel';
export type Coordinate = [number, number];
export type CheckpointSpacing = 10 | 25 | 50;
export type DataMode = 'live' | 'demo';

export interface ResolvedPlace {
  id: string;
  label: string;
  coordinate: Coordinate;
  timeZone: string;
}

export interface TripInput {
  origin: string;
  destination: string;
  departure: string;
  loadWeight: number;
  spacing: CheckpointSpacing;
  originPlace?: ResolvedPlace;
  destinationPlace?: ResolvedPlace;
  departureTimeZone?: string;
}

export interface Checkpoint {
  id: string;
  number: number;
  name: string;
  coordinate: Coordinate;
  miles: number;
  arrival: string;
  timeZone: string;
  wind: number | null;
  rain: number | null;
  snow: number | null;
  risk: RiskLevel | null;
  weatherStatus: 'available' | 'missing';
  forecastTime?: string | null;
  riskReasons?: string[];
}

export interface RouteSegment {
  id: string;
  geometry: Coordinate[];
  startMiles: number;
  endMiles: number;
  risk: RiskLevel | null;
}

export interface RouteOption {
  id: string;
  name: string;
  highway: string;
  distance: number;
  duration: number;
  risk: RiskLevel | null;
  severeMiles: number;
  highMiles: number;
  noTravelMiles: number;
  unknownMiles: number;
  averageRisk: number | null;
  complete: boolean;
  eligible: boolean;
  recommended: boolean;
  explanation: string;
  geometry: Coordinate[];
  checkpoints: Checkpoint[];
  exposure: { risk: RiskLevel | null; miles: number }[];
  segments: RouteSegment[];
  avoid?: string[];
}

export interface TripResult {
  analysisId: string;
  expiresAt: string;
  routes: RouteOption[];
  trip: TripInput;
  forecastStart: string;
  recommendedRouteId: string | null;
  recommendationReason?: string;
  warnings: { code: string; message: string; routeId?: string }[];
  resolvedPlaces?: { origin: ResolvedPlace; destination: ResolvedPlace };
  forecastMetadata?: { provider: string; retrievedAt: string; attribution?: string };
}
