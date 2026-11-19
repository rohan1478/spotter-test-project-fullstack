import { CalendarDays, LoaderCircle, Pause, Play } from 'lucide-react';
import { riskColors, riskLabels } from '../../routing/components/RiskBadge';
import { formatForecast } from '../../routing/utils/format';
import type { DataMode } from '../../routing/types';
import type { CorridorForecast, ForecastStatus } from '../types';
import type { ApiError } from '../../../lib/apiClient';

export function ForecastControls({ start, hour, onHourChange, playing, onTogglePlay, data, status, error, expired, mode, onRetry, timeZone }: {
  start: string | null; hour: number; onHourChange: (hour: number) => void; playing: boolean; onTogglePlay: () => void;
  data: CorridorForecast | null; status: ForecastStatus; error: ApiError | null; expired: boolean; mode: DataMode; onRetry: () => void; timeZone: string;
}) {
  const disabled = status !== 'ready' || !data || expired;
  const missing = data?.frames[hour]?.missingCellCount || 0;
  return <section aria-label="Corridor forecast" className="panel relative z-10 shrink-0 bg-panel/95 px-4 py-3 backdrop-blur-sm">
    <div className="flex flex-wrap items-center gap-x-4 gap-y-1"><h2 className="text-sm font-semibold">Corridor forecast</h2>
      <span className="hidden h-4 w-px bg-line sm:block" /><span className="flex items-center gap-1.5 text-[11px] text-muted"><CalendarDays size={13} />{start ? formatForecast(start, hour, timeZone) : 'Compare a trip to view forecasts'}</span>
      <span className="ml-auto hidden rounded bg-field px-1.5 py-0.5 text-[9px] font-medium tracking-wide text-subtle sm:block">{mode === 'demo' ? 'SAMPLE FORECAST' : 'CORRIDOR RISK'}</span>
    </div>
    {status === 'loading' && <p role="status" className="mt-2 flex items-center gap-2 text-xs text-accent"><LoaderCircle size={13} className="animate-spin" />Loading corridor forecast…</p>}
    {(expired || error) && <div className="mt-2 flex flex-wrap items-center gap-2 text-xs"><p role="alert" className="text-moderate">{expired ? 'Analysis expired. Compare again for a fresh forecast.' : error?.message}</p><button type="button" onClick={onRetry} className="text-accent underline">{expired ? 'Compare again' : 'Retry forecast'}</button></div>}
    <div className="mt-3 flex flex-col gap-4 2xl:flex-row 2xl:items-center">
      <div className="flex min-w-0 flex-1 items-start gap-3">
        <button disabled={disabled} aria-label={playing ? 'Pause forecast' : 'Play forecast'} aria-pressed={playing} onClick={onTogglePlay} className="flex size-8 shrink-0 items-center justify-center rounded-md border border-accent/50 bg-accent/5 text-accent hover:bg-accent/15">{playing ? <Pause size={14} fill="currentColor" /> : <Play size={14} fill="currentColor" />}</button>
        <div className="flex-1 pt-1"><input type="range" aria-label="Forecast hour" aria-valuetext={`${hour} hours from forecast start`} min="0" max="48" step="1" value={hour} disabled={disabled} onChange={event => onHourChange(Number(event.target.value))} className="forecast-range block w-full disabled:opacity-40" style={{ background: `linear-gradient(to right, var(--color-accent) ${hour / 48 * 100}%, var(--color-line) ${hour / 48 * 100}%)` }} />
          <div className="mt-2 flex justify-between text-[10px] text-muted">{[0, 12, 24, 36, 48].map(tick => <button key={tick} disabled={disabled} aria-label={`Show forecast at ${tick} hours`} onClick={() => onHourChange(tick)} className="rounded hover:text-accent">{tick === 0 ? 'Start' : `+${tick}h`}</button>)}</div>
        </div>
      </div>
      <div className="shrink-0 2xl:border-l 2xl:border-line 2xl:pl-4">
        <div className="flex flex-wrap gap-x-3 gap-y-1.5">{Object.entries(riskLabels).map(([risk, label]) => <span key={risk} className="flex items-center gap-1.5 text-[10px] text-ink"><span className="h-2 w-4 rounded-sm" style={{ backgroundColor: riskColors[risk as keyof typeof riskColors] }} />{label}</span>)}<span className="text-[10px] text-subtle">Unknown = unavailable</span></div>
        <p className="mt-2 text-[10px] leading-relaxed text-subtle">Slider updates the heatmap; route risk uses arrival forecasts.</p>
      </div>
    </div>
    {missing > 0 && !expired && <p className="mt-2 text-[10px] text-moderate">{missing} of {data?.grid.cellCount} cells have unavailable weather for this hour.</p>}
    {data?.warnings.map(warning => <p key={warning.code} className="mt-1 text-[10px] text-muted">{warning.message}</p>)}
    {data?.forecastMetadata.attribution && <p className="mt-2 text-[9px] text-subtle">{data.forecastMetadata.attribution}</p>}
  </section>;
}
