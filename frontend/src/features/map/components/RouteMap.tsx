import { useEffect, useMemo, useRef, useState } from 'react';
import { LocateFixed, Minus, Plus } from 'lucide-react';
import * as maplibregl from 'maplibre-gl';
import mapWorkerUrl from 'maplibre-gl/dist/maplibre-gl-worker.mjs?worker&url';
import type { GeoJSONSource, Map as MapLibreMap } from 'maplibre-gl';
import type { Checkpoint, DataMode, RouteOption } from '../../routing/types';
import type { CorridorForecast, ForecastStatus } from '../../forecast/types';
import type { ApiError } from '../../../lib/apiClient';
import { Button } from '../../../components/ui/Button';
import { CheckpointDetails } from '../../routing/components/CheckpointDetails';
import { riskColor } from '../../routing/components/RiskBadge';
import { formatNumber } from '../../routing/utils/format';
import { ForecastControls } from '../../forecast/components/ForecastControls';
import { corridorFeatures, readMapTheme, routeBounds, routeFeatures } from '../utils/mapData';
import { MapFallback } from './MapFallback';

maplibregl.setWorkerUrl(mapWorkerUrl);

interface RouteMapProps {
  routes: RouteOption[]; selectedId: string; onSelect: (id: string) => void;
  checkpoint: Checkpoint | null; onCheckpoint: (point: Checkpoint | null) => void;
  forecastStart: string | null; hour: number; playing: boolean; onSeek: (hour: number) => void; onTogglePlay: () => void;
  corridor: CorridorForecast | null; forecastStatus: ForecastStatus; forecastError: ApiError | null;
  expired: boolean; mode: DataMode; loading: boolean; onRetryForecast: () => void; timeZone: string;
}

export function RouteMap(props: RouteMapProps) {
  const { routes, selectedId, onSelect, checkpoint, onCheckpoint, hour, corridor, expired, mode } = props;
  const container = useRef<HTMLDivElement>(null);
  const mapRef = useRef<MapLibreMap | null>(null);
  const [ready, setReady] = useState(false);
  const [mapUnavailable, setMapUnavailable] = useState(false);
  const callbacks = useRef({ onSelect, onCheckpoint, routes });
  callbacks.current = { onSelect, onCheckpoint, routes };
  const selected = routes.find(route => route.id === selectedId);
  const lineData = useMemo(() => routeFeatures(routes, selectedId), [routes, selectedId]);
  const cells = useMemo(() => corridorFeatures(expired ? null : corridor, hour), [corridor, hour, expired]);

  useEffect(() => {
    if (!container.current) return;
    let timer: ReturnType<typeof setTimeout> | undefined;
    let resize: ResizeObserver | undefined;
    try {
      const map = new maplibregl.Map({ container: container.current,
        style: 'https://tiles.openfreemap.org/styles/dark', center: [-87.15, 40.9], zoom: 6,
        minZoom: 1, maxZoom: 13, attributionControl: false, renderWorldCopies: false });
      mapRef.current = map;
      map.addControl(new maplibregl.AttributionControl({ compact: true }), 'bottom-left');
      timer = setTimeout(() => { if (!map.isStyleLoaded()) setMapUnavailable(true); }, 12000);
      map.on('error', () => setMapUnavailable(true));
      map.on('load', () => {
        clearTimeout(timer);
        const theme = readMapTheme();
        for (const layer of map.getStyle().layers) {
          if (layer.type === 'background') map.setPaintProperty(layer.id, 'background-color', theme.land);
          if (layer.type === 'fill' && /water/.test(layer.id)) map.setPaintProperty(layer.id, 'fill-color', theme.water);
          if (layer.type === 'line' && /road|highway|transport/.test(layer.id)) map.setPaintProperty(layer.id, 'line-color', theme.road);
          if (layer.type === 'symbol' && layer.layout?.['text-field']) {
            map.setPaintProperty(layer.id, 'text-color', theme.label);
            map.setPaintProperty(layer.id, 'text-halo-color', theme.land);
          }
        }
        map.addSource('corridor-weather', { type: 'geojson', data: { type: 'FeatureCollection', features: [] } });
        map.addLayer({ id: 'corridor-weather', type: 'fill', source: 'corridor-weather', paint: {
          'fill-color': ['get', 'color'], 'fill-opacity': ['get', 'opacity'],
        } });
        map.addSource('trip-routes', { type: 'geojson', data: { type: 'FeatureCollection', features: [] } });
        map.addLayer({ id: 'route-outline', type: 'line', source: 'trip-routes', layout: { 'line-join': 'round', 'line-cap': 'round' },
          paint: { 'line-color': theme.panel, 'line-width': ['+', ['get', 'width'], 3], 'line-opacity': .9 } });
        map.addLayer({ id: 'route-line', type: 'line', source: 'trip-routes', layout: { 'line-join': 'round', 'line-cap': 'round' },
          paint: { 'line-color': ['get', 'color'], 'line-width': ['get', 'width'], 'line-opacity': ['get', 'opacity'] } });
        map.addLayer({ id: 'route-hit-area', type: 'line', source: 'trip-routes', paint: { 'line-width': 18, 'line-opacity': 0 } });
        map.on('click', 'route-hit-area', event => {
          const id = event.features?.[0]?.properties?.id;
          if (id) callbacks.current.onSelect(String(id));
        });
        map.on('mouseenter', 'route-hit-area', () => { map.getCanvas().style.cursor = 'pointer'; });
        map.on('mouseleave', 'route-hit-area', () => { map.getCanvas().style.cursor = ''; });
        map.resize();
        map.once('idle', () => map.fitBounds(routeBounds(callbacks.current.routes), { padding: 60, maxZoom: 10, duration: 0 }));
        setReady(true);
      });
      resize = new ResizeObserver(() => map.resize());
      resize.observe(container.current);
    } catch { setMapUnavailable(true); }
    return () => { clearTimeout(timer); resize?.disconnect(); mapRef.current?.remove(); mapRef.current = null; };
  }, []);

  useEffect(() => {
    if (!ready || !mapRef.current) return;
    (mapRef.current.getSource('trip-routes') as GeoJSONSource).setData(lineData);
  }, [ready, lineData]);

  useEffect(() => {
    if (!ready || !mapRef.current) return;
    mapRef.current.fitBounds(routeBounds(routes), { padding: 60, maxZoom: 10, duration: 0 });
  }, [ready, routes]);

  useEffect(() => {
    if (!ready || !mapRef.current) return;
    (mapRef.current.getSource('corridor-weather') as GeoJSONSource).setData(cells);
  }, [ready, cells]);

  useEffect(() => {
    const map = mapRef.current;
    if (!ready || !map || !selected) return;
    const markers = selected.checkpoints.map((point, index) => {
      const endpoint = index === 0 || index === selected.checkpoints.length - 1;
      const element = document.createElement('button');
      element.type = 'button';
      element.setAttribute('aria-label', `Checkpoint ${point.number} at mile ${formatNumber(point.miles)}`);
      element.setAttribute('aria-pressed', String(point.id === checkpoint?.id));
      if (endpoint) {
        element.className = 'endpoint-marker'; element.dataset.destination = String(index !== 0);
        const dot = document.createElement('i'); const label = document.createElement('span'); label.textContent = point.name;
        element.append(dot, label);
      } else {
        element.className = 'checkpoint-marker'; element.textContent = String(point.number);
        element.style.borderColor = point.risk === 'low' ? 'var(--color-accent)' : riskColor(point.risk);
      }
      element.addEventListener('click', event => { event.stopPropagation(); callbacks.current.onCheckpoint(point); });
      return new maplibregl.Marker({ element, anchor: endpoint ? 'left' : 'center' }).setLngLat(point.coordinate).addTo(map);
    });
    return () => markers.forEach(marker => marker.remove());
  }, [ready, selected, checkpoint?.id]);

  return <section aria-label="Route map and forecast" className="panel relative flex min-h-[660px] min-w-0 flex-col overflow-hidden xl:min-h-0">
    <div className="relative min-h-[470px] flex-1 bg-map-land xl:min-h-0">
      {!ready && <MapFallback routes={routes} selectedId={selectedId} corridor={!expired ? corridor : null} hour={hour} onCheckpoint={onCheckpoint} onSelect={onSelect} />}
      <div ref={container} className={`absolute inset-0 ${ready ? 'opacity-100' : 'pointer-events-none opacity-0'}`} aria-label="Interactive route map" />
      {!routes.length && <div className="pointer-events-none absolute inset-0 z-10 flex items-center justify-center p-8"><div className="max-w-xs rounded-xl border border-line bg-panel/90 p-6 text-center shadow-panel"><LocateFixed size={28} className="mx-auto text-accent" /><h2 className="mt-3 text-base font-semibold">{props.loading ? 'Finding your route options…' : 'Your route starts here'}</h2><p className="mt-2 text-xs leading-relaxed text-muted">{props.loading ? 'Checking road alternatives and weather at each arrival.' : 'Compare a trip to see routes, checkpoints, and the forecast ahead.'}</p></div></div>}
      <div className="absolute top-4 right-4 z-10 flex flex-col gap-1.5">
        <Button variant="icon" aria-label="Zoom in" disabled={!ready} onClick={() => mapRef.current?.zoomIn()}><Plus size={18} /></Button>
        <Button variant="icon" aria-label="Zoom out" disabled={!ready} onClick={() => mapRef.current?.zoomOut()}><Minus size={18} /></Button>
        <Button variant="icon" aria-label="Fit all routes" disabled={!ready} onClick={() => mapRef.current?.fitBounds(routeBounds(routes), { padding: 60, maxZoom: 10, duration: 0 })} className="mt-1"><LocateFixed size={17} /></Button>
      </div>
      {checkpoint && <div className="absolute right-3 bottom-10 left-3 z-10 sm:top-[37%] sm:right-5 sm:bottom-auto sm:left-auto"><CheckpointDetails checkpoint={checkpoint} onClose={() => onCheckpoint(null)} mode={mode} expired={expired} /></div>}
      <div className="pointer-events-none absolute right-3 bottom-3 rounded-md border border-line/70 bg-panel/90 px-2 py-1 text-[9px] text-muted">{mode === 'demo' ? 'Demo · Sample data' : expired ? 'Forecast expired' : mapUnavailable ? 'Basemap unavailable' : 'Live mode'}</div>
    </div>
    <div className="z-10 border-t border-line p-3"><ForecastControls start={props.forecastStart} hour={hour} onHourChange={props.onSeek} playing={props.playing} onTogglePlay={props.onTogglePlay}
      data={corridor} status={props.forecastStatus} error={props.forecastError} expired={expired} mode={mode} onRetry={props.onRetryForecast} timeZone={props.timeZone} /></div>
  </section>;
}
