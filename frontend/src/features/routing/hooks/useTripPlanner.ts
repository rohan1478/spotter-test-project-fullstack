import { useCallback, useEffect, useRef, useState } from 'react';
import { ApiError, errorMessage } from '../../../lib/apiClient';
import { fetchCorridor } from '../../forecast/services/forecastApi';
import type { CorridorForecast, ForecastStatus } from '../../forecast/types';
import { defaultTrip } from '../data/demoRoutes';
import { buildDemoResult, compareDemoRoutes } from '../services/demoRoutingService';
import { buildDemoCorridor } from '../../forecast/services/demoForecast';
import { compareRoutes } from '../services/routingApi';
import type { Checkpoint, DataMode, TripInput, TripResult } from '../types';

const liveTrip = (): TripInput => ({ ...defaultTrip, departure: '' });

interface PlannerSnapshot {
  trip: TripInput;
  submitted: TripInput | null;
  result: TripResult | null;
  selectedId: string;
  checkpoint: Checkpoint | null;
  error: string | null;
  corridor: CorridorForecast | null;
  forecastStatus: ForecastStatus;
  forecastError: ApiError | null;
  expired: boolean;
}

export function useTripPlanner() {
  const [mode, setMode] = useState<DataMode>('live');
  const [trip, setTrip] = useState<TripInput>(liveTrip);
  const [submitted, setSubmitted] = useState<TripInput | null>(null);
  const [result, setResult] = useState<TripResult | null>(null);
  const [selectedId, setSelectedId] = useState('');
  const [checkpoint, setCheckpoint] = useState<Checkpoint | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [corridor, setCorridor] = useState<CorridorForecast | null>(null);
  const [forecastStatus, setForecastStatus] = useState<ForecastStatus>('idle');
  const [forecastError, setForecastError] = useState<ApiError | null>(null);
  const [expired, setExpired] = useState(false);
  const comparisonRequest = useRef<AbortController | null>(null);
  const corridorRequest = useRef<AbortController | null>(null);
  const generation = useRef(0);
  const snapshots = useRef<Partial<Record<DataMode, PlannerSnapshot>>>({});

  useEffect(() => () => { comparisonRequest.current?.abort(); corridorRequest.current?.abort(); }, []);
  useEffect(() => {
    if (!result || mode === 'demo') return;
    const deadline = Math.min(Date.parse(result.expiresAt), corridor ? Date.parse(corridor.expiresAt) : Infinity);
    const remaining = deadline - Date.now();
    if (remaining <= 0) { setExpired(true); return; }
    const timer = window.setTimeout(() => setExpired(true), Math.min(remaining, 2_147_483_647));
    return () => window.clearTimeout(timer);
  }, [result, corridor, mode]);

  const selectRoute = useCallback((id: string, data?: TripResult) => {
    const route = (data || result)?.routes.find(option => option.id === id);
    if (!route) { setSelectedId(''); setCheckpoint(null); return; }
    setSelectedId(id);
    setCheckpoint(route.checkpoints.find(point => point.risk !== null && point.risk !== 'low')
      || route.checkpoints[Math.floor(route.checkpoints.length / 2)] || null);
  }, [result]);

  async function loadCorridor(data: TripResult, requestGeneration = generation.current) {
    corridorRequest.current?.abort();
    const controller = new AbortController();
    corridorRequest.current = controller;
    setForecastStatus('loading'); setForecastError(null); setCorridor(null);
    try {
      let next: CorridorForecast | undefined;
      for (let attempt = 0; attempt < 3; attempt++) {
        try { next = await fetchCorridor(data.analysisId, controller.signal); break; }
        catch (caught) {
          if (!(caught instanceof ApiError) || caught.code !== 'corridor_in_progress' || attempt === 2) throw caught;
          await new Promise<void>((resolve, reject) => {
            const cancel = () => { window.clearTimeout(timer); reject(new DOMException('Cancelled', 'AbortError')); };
            const timer = window.setTimeout(() => { controller.signal.removeEventListener('abort', cancel); resolve(); }, 1500);
            controller.signal.addEventListener('abort', cancel, { once: true });
            if (controller.signal.aborted) cancel();
          });
        }
      }
      if (!controller.signal.aborted && requestGeneration === generation.current && next) {
        setCorridor(next); setForecastStatus('ready');
      }
    } catch (caught) {
      if (controller.signal.aborted || requestGeneration !== generation.current) return;
      const failure = caught instanceof ApiError ? caught : new ApiError(errorMessage(caught), 'forecast_error');
      setForecastError(failure); setForecastStatus('error');
      if (failure.code === 'analysis_expired' || failure.code === 'forecast_expired') setExpired(true);
    }
  }

  function changeMode(next: DataMode) {
    if (next === mode) return;
    snapshots.current[mode] = { trip, submitted, result, selectedId, checkpoint, error,
      corridor, forecastStatus, forecastError, expired };
    generation.current++;
    comparisonRequest.current?.abort(); corridorRequest.current?.abort();
    let restored = snapshots.current[next];
    if (!restored && next === 'demo') {
      const demo = buildDemoResult(defaultTrip);
      const selected = demo.routes.find(route => route.id === demo.recommendedRouteId) || demo.routes[0];
      restored = { trip: { ...defaultTrip }, submitted: { ...defaultTrip }, result: demo,
        selectedId: selected?.id || '',
        checkpoint: selected?.checkpoints.find(point => point.risk !== null && point.risk !== 'low')
          || selected?.checkpoints[Math.floor(selected.checkpoints.length / 2)] || null,
        error: null, corridor: buildDemoCorridor(demo), forecastStatus: 'ready', forecastError: null, expired: false };
    }
    restored ||= { trip: liveTrip(), submitted: null, result: null, selectedId: '', checkpoint: null,
      error: null, corridor: null, forecastStatus: 'idle', forecastError: null, expired: false };
    const deadline = restored.result ? Math.min(Date.parse(restored.result.expiresAt),
      restored.corridor ? Date.parse(restored.corridor.expiresAt) : Infinity) : Infinity;
    const isExpired = next === 'live' && (restored.expired || deadline <= Date.now());
    setMode(next); setLoading(false); setTrip(restored.trip); setSubmitted(restored.submitted);
    setResult(restored.result); setSelectedId(restored.selectedId); setCheckpoint(restored.checkpoint);
    setError(restored.error); setCorridor(restored.corridor); setExpired(isExpired);
    setForecastError(restored.forecastError);
    setForecastStatus(restored.forecastStatus === 'loading' ? 'idle' : restored.forecastStatus);
    if (next === 'live' && !isExpired && restored.result?.routes.length && !restored.corridor
        && (restored.forecastStatus === 'loading' || restored.forecastStatus === 'idle')) {
      void loadCorridor(restored.result);
    }
  }

  async function compare() {
    if (mode === 'live' && (!trip.originPlace || !trip.destinationPlace)) {
      setError('Choose both origin and destination from the location search results.'); return;
    }
    if (!trip.departure || !Number.isFinite(trip.loadWeight) || trip.loadWeight <= 0) {
      setError('Enter a departure time and a positive load weight.'); return;
    }
    comparisonRequest.current?.abort(); corridorRequest.current?.abort();
    const controller = new AbortController(); comparisonRequest.current = controller;
    const version = ++generation.current;
    const snapshot = structuredClone(trip);
    setLoading(true); setError(null); setCorridor(null); setForecastStatus('idle'); setForecastError(null);
    try {
      const next = mode === 'demo' ? await compareDemoRoutes(snapshot) : await compareRoutes(snapshot, controller.signal);
      if (controller.signal.aborted || version !== generation.current) return;
      setResult(next); setSubmitted(snapshot); setExpired(false);
      selectRoute(next.recommendedRouteId || next.routes[0]?.id || '', next);
      if (mode === 'demo') { setCorridor(buildDemoCorridor(next)); setForecastStatus('ready'); }
      else if (next.routes.length) void loadCorridor(next, version);
    } catch (caught) {
      if (!controller.signal.aborted && version === generation.current) setError(errorMessage(caught));
    } finally { if (version === generation.current) setLoading(false); }
  }

  function cancel() {
    generation.current++; comparisonRequest.current?.abort(); corridorRequest.current?.abort();
    setLoading(false); setError('Comparison cancelled.'); setForecastStatus('idle');
  }

  return { mode, changeMode, trip, setTrip, result, selectedId, selectRoute, checkpoint, setCheckpoint,
    loading, error, compare, cancel, corridor, forecastStatus, forecastError, expired,
    retryForecast: () => { if (result && !expired) void loadCorridor(result); else void compare(); },
    dirty: submitted !== null && JSON.stringify(trip) !== JSON.stringify(submitted) };
}
