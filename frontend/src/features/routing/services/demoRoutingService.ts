import { routeTemplates } from '../data/demoRoutes';
import type { Checkpoint, Coordinate, RiskLevel, RouteOption, TripInput, TripResult } from '../types';
import { departureToISOString } from '../utils/format';

const riskOrder: RiskLevel[] = ['low', 'moderate', 'high', 'severe', 'no-travel'];

function sampleRisk(wind: number, weight: number): RiskLevel {
  if (wind >= 55 || (wind >= 45 && weight > 30000)) return 'no-travel';
  if (wind >= 45 || (wind >= 35 && weight > 40000)) return 'severe';
  if (wind >= 35) return 'high';
  if (wind >= 25) return 'moderate';
  return 'low';
}

function pointAlong(geometry: Coordinate[], fraction: number): Coordinate {
  const lengths = geometry.slice(1).map((point, i) => Math.hypot(
    (point[0] - geometry[i][0]) * Math.cos(point[1] * Math.PI / 180), point[1] - geometry[i][1],
  ));
  let remaining = lengths.reduce((sum, length) => sum + length, 0) * fraction;
  for (let i = 0; i < lengths.length; i++) {
    if (remaining <= lengths[i]) {
      const ratio = remaining / lengths[i];
      return [geometry[i][0] + (geometry[i+1][0] - geometry[i][0]) * ratio,
        geometry[i][1] + (geometry[i+1][1] - geometry[i][1]) * ratio];
    }
    remaining -= lengths[i];
  }
  return geometry[geometry.length - 1];
}

export function buildDemoResult(trip: TripInput): TripResult {
  const reverse = /indianapolis/i.test(trip.origin);
  const start = departureToISOString(trip.departure, reverse ? 'America/Indiana/Indianapolis' : 'America/Chicago');
  const routes: RouteOption[] = routeTemplates.map((template, routeIndex) => {
    const geometry = reverse ? [...template.geometry].reverse() : template.geometry;
    const checkpointMiles = [0];
    for (let miles = trip.spacing; miles < template.distance; miles += trip.spacing) checkpointMiles.push(miles);
    checkpointMiles.push(template.distance);
    const checkpoints: Checkpoint[] = checkpointMiles.map((miles, index) => {
      const fraction = miles / template.distance;
      const coordinate = pointAlong(geometry, fraction);
      const nearLafayette = Math.hypot(coordinate[0] + 86.875, coordinate[1] - 40.5) < .22;
      const wind = routeIndex === 0 ? 18 : routeIndex === 1 && fraction > .35 && fraction < .52 ? 38
        : routeIndex === 2 && fraction > .42 && fraction < .53 ? 46
        : routeIndex === 2 && fraction > .23 && fraction < .42 ? 38 : 20;
      return {
        id: `${template.id}-${index}`, number: index, miles, coordinate,
        name: index === 0 ? trip.origin : index === checkpointMiles.length - 1 ? trip.destination
          : nearLafayette ? 'Lafayette' : `Mile ${miles}`,
        arrival: new Date(new Date(start).getTime() + fraction * template.duration * 60000).toISOString(),
        timeZone: coordinate[1] < 41.2 ? 'America/Indiana/Indianapolis' : 'America/Chicago',
        wind, rain: .03, snow: 0, risk: sampleRisk(wind, trip.loadWeight), weatherStatus: 'available',
      };
    });
    const exposure = riskOrder.map((risk) => ({ risk, miles: 0 }));
    checkpoints.slice(0,-1).forEach((point, i) => {
      exposure.find((entry) => entry.risk === point.risk)!.miles += checkpoints[i+1].miles - point.miles;
    });
    const highest = [...exposure].reverse().find((entry) => entry.miles > 0)!.risk;
    return { ...template, name: `via ${template.highway}`, geometry, checkpoints, exposure,
      risk: highest, severeMiles: exposure.find((entry) => entry.risk === 'severe')!.miles,
      highMiles: exposure.find((entry) => entry.risk === 'high')!.miles,
      noTravelMiles: exposure.find((entry) => entry.risk === 'no-travel')!.miles,
      unknownMiles: 0, complete: true, eligible: highest !== 'no-travel',
      averageRisk: exposure.reduce((sum, entry) => sum + entry.miles * riskOrder.indexOf(entry.risk), 0) / template.distance,
      segments: geometry.slice(0, -1).map((point, i) => ({
        id: `${template.id}-segment-${i}`, geometry: [point, geometry[i + 1]],
        startMiles: i / (geometry.length - 1) * template.distance,
        endMiles: (i + 1) / (geometry.length - 1) * template.distance,
        risk: checkpoints[Math.min(checkpoints.length - 1, Math.floor(i / geometry.length * checkpoints.length))].risk,
      })),
      recommended: routeIndex === 0,
      explanation: routeIndex === 0 ? 'Avoids all High and Severe exposure.' : highest === 'no-travel'
        ? 'Wind and load exceed the No Travel threshold.' : 'Higher weather exposure along this route.',
    };
  });
  return { routes, trip: { ...trip }, forecastStart: new Date(new Date(start).getTime() - 12 * 3600000).toISOString(),
    analysisId: 'demo', expiresAt: new Date(Date.now() + 86_400_000).toISOString(), recommendedRouteId: '01',
    warnings: [], forecastMetadata: { provider: 'Sample data', retrievedAt: new Date().toISOString() } };
}

export async function compareDemoRoutes(trip: TripInput): Promise<TripResult> {
  const forward = /^chicago(?:,?\s*il)?$/i.test(trip.origin.trim()) && /^indianapolis(?:,?\s*in)?$/i.test(trip.destination.trim());
  const reverse = /^indianapolis(?:,?\s*in)?$/i.test(trip.origin.trim()) && /^chicago(?:,?\s*il)?$/i.test(trip.destination.trim());
  if (!forward && !reverse) throw new Error('This UI preview supports Chicago, IL ↔ Indianapolis, IN. Other trips will be available when the routing API is connected.');
  if (!trip.departure || !Number.isFinite(trip.loadWeight) || trip.loadWeight <= 0) {
    throw new Error('Enter a departure time and a positive load weight.');
  }
  await new Promise((resolve) => setTimeout(resolve, 450));
  return buildDemoResult(trip);
}
