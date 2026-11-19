import { CloudSun } from 'lucide-react';
import type { TripResult } from '../types';
import { RouteCard } from './RouteCard';

export function RouteComparison({ result, selectedId, onSelect, dirty, loading, expired, failed }: {
  result: TripResult | null; selectedId: string; onSelect: (id: string) => void;
  dirty: boolean; loading: boolean; expired: boolean; failed: boolean;
}) {
  const routes = result?.routes || [];
  return <aside aria-labelledby="comparison-heading" className="panel flex min-h-0 flex-col p-4 xl:overflow-y-auto">
    <div className="mb-4 flex items-start justify-between gap-2">
      <div><h2 id="comparison-heading" className="text-lg font-bold tracking-tight">Route comparison</h2><p className="mt-1 text-xs text-muted">{result ? `${routes.length} ${routes.length === 1 ? 'option' : 'options'} · Ranked by weather risk` : 'Choose your journey to compare routes'}</p></div>
    </div>
    {dirty && <p role="status" className="mb-3 rounded-md border border-moderate/25 bg-moderate/5 px-2.5 py-2 text-[11px] text-moderate">Trip changed. Compare routes to update these results.</p>}
    {expired && <p role="status" className="mb-3 text-xs text-moderate">Forecast expired. Compare routes again to refresh.</p>}
    {failed && result && <p className="mb-3 text-xs text-moderate">The latest comparison failed. Previous results are shown below.</p>}
    {loading && <p role="status" className="mb-3 text-xs text-accent">Comparing routes and arrival forecasts…</p>}
    {!result && !loading && <div className="rounded-lg border border-dashed border-line px-4 py-8 text-center"><h3 className="text-sm font-semibold">Plan your first trip</h3><p className="mt-2 text-xs leading-relaxed text-muted">Select locations, choose a departure time, and compare the weather along your journey.</p></div>}
    {result && !routes.length && <p className="rounded-lg border border-line p-5 text-sm text-muted">No routes available. Try different locations or departure details.</p>}
    {result && routes.length > 0 && result.recommendedRouteId === null && <div className="mb-3 rounded-lg border border-moderate/30 bg-moderate/5 p-3"><h3 className="text-xs font-semibold text-moderate">No recommended route</h3><p className="mt-1 text-[11px] leading-relaxed text-muted">{result.recommendationReason || 'Available routes are blocked or have incomplete weather.'}</p></div>}
    <div className="grid gap-3 sm:grid-cols-3 xl:grid-cols-1">{routes.map((route) => <RouteCard key={route.id} route={route} selected={selectedId === route.id} onSelect={() => onSelect(route.id)} />)}</div>
    {result?.warnings.filter(warning => !warning.routeId && warning.code !== 'no_recommendation').map(warning => <p key={warning.code} className="mt-3 text-[11px] leading-relaxed text-muted">{warning.message}</p>)}
    <div className="mt-5 flex gap-2.5 rounded-lg border border-line bg-field/50 p-3">
      <CloudSun size={21} className="shrink-0 text-muted" /><p className="text-[11px] leading-relaxed text-muted">Weather is evaluated at each checkpoint’s arrival time.</p>
    </div>
  </aside>;
}
