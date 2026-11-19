import { AppHeader } from '../components/layout/AppHeader';
import { TripForm } from '../features/routing/components/TripForm';
import { RouteComparison } from '../features/routing/components/RouteComparison';
import { RouteMap } from '../features/map/components/RouteMap';
import { useTripPlanner } from '../features/routing/hooks/useTripPlanner';
import { useForecastPlayback } from '../features/forecast/hooks/useForecastPlayback';

const EMPTY_ROUTES: [] = [];

export function App() {
  const planner = useTripPlanner();
  const forecast = useForecastPlayback(planner.forecastStatus === 'ready' && !planner.expired,
    `${planner.mode}:${planner.result?.analysisId || ''}`, planner.mode);
  return <div className="flex min-h-dvh flex-col xl:h-dvh">
    <AppHeader mode={planner.mode} onModeChange={planner.changeMode} />
    <main className="flex min-h-0 flex-1 flex-col gap-3 p-3 sm:gap-4 sm:p-4">
      <TripForm value={planner.trip} onChange={planner.setTrip} onSubmit={planner.compare} loading={planner.loading}
        error={planner.error} mode={planner.mode} onCancel={planner.cancel} />
      <div className="grid min-h-0 flex-1 grid-cols-1 gap-3 sm:gap-4 xl:grid-cols-[minmax(0,1fr)_350px]">
        <RouteMap routes={planner.result?.routes || EMPTY_ROUTES} selectedId={planner.selectedId} onSelect={planner.selectRoute}
          checkpoint={planner.checkpoint} onCheckpoint={planner.setCheckpoint} forecastStart={planner.result?.forecastStart || null}
          hour={forecast.hour} playing={forecast.playing} onSeek={forecast.seek} onTogglePlay={forecast.toggle}
          corridor={planner.corridor} forecastStatus={planner.forecastStatus} forecastError={planner.forecastError}
          expired={planner.expired} mode={planner.mode} loading={planner.loading} onRetryForecast={planner.retryForecast}
          timeZone={planner.result?.resolvedPlaces?.origin.timeZone || planner.trip.originPlace?.timeZone || 'UTC'} />
        <RouteComparison result={planner.result} selectedId={planner.selectedId} onSelect={planner.selectRoute}
          dirty={planner.dirty} loading={planner.loading} expired={planner.expired} failed={planner.error !== null} />
      </div>
      {planner.result?.forecastMetadata?.attribution && <p className="text-[9px] text-subtle">{planner.result.forecastMetadata.attribution} · Locations powered by Geoapify · © OpenStreetMap contributors</p>}
      <p className="sr-only" role="status" aria-live="polite">{planner.loading ? 'Comparing routes' : planner.selectedId ? `Selected route ${planner.selectedId}` : 'Ready to plan a trip'}</p>
    </main>
  </div>;
}
