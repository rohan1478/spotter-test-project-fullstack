import { Check, ChevronRight, Clock3, Route } from 'lucide-react';
import type { RouteOption } from '../types';
import { formatDuration, formatNumber } from '../utils/format';
import { RiskBadge, riskColor, riskLabels } from './RiskBadge';

export function RouteCard({ route, selected, onSelect }: { route: RouteOption; selected: boolean; onSelect: () => void }) {
  return <button aria-label={`Select route ${route.id} via ${route.highway}`} aria-pressed={selected} onClick={onSelect}
    className={`w-full rounded-lg border p-3.5 text-left transition-colors ${selected ? 'border-accent bg-accent-strong/10 ring-1 ring-accent/10' : 'border-line bg-panel-raised/50 hover:border-subtle hover:bg-panel-raised'}`}>
    <div className="flex items-center gap-2.5">
      <span className={`rounded px-2 py-0.5 text-xs font-bold ${selected ? 'bg-accent-strong/45 text-accent' : 'bg-line text-muted'}`}>{route.id}</span>
      <h3 className="text-sm font-semibold">{route.name}</h3>
      {route.recommended ? <span className="ml-auto flex items-center gap-1 rounded bg-accent-strong/30 px-1.5 py-1 text-[9px] font-semibold text-accent"><Check size={10} /> Recommended</span>
        : <ChevronRight size={15} className="ml-auto text-subtle" />}
    </div>
    <div className="mt-3 flex items-center gap-2 text-sm">
      <Clock3 size={15} className="text-muted" /><span className="font-bold">{formatDuration(route.duration)}</span>
      <span className="mx-1 h-3.5 w-px bg-line" /><Route size={14} className="text-muted" /><span className="text-muted">{formatNumber(route.distance)} mi</span>
      <span className="ml-auto"><RiskBadge risk={route.risk} /></span>
    </div>
    <div className="mt-3 flex flex-wrap gap-x-3 gap-y-1 text-[11px] text-muted"><span>Severe <strong className="font-medium text-ink">{formatNumber(route.severeMiles)} mi</strong></span><span>High <strong className="font-medium text-ink">{formatNumber(route.highMiles)} mi</strong></span>
      {route.noTravelMiles > 0 && <span className="text-no-travel">No Travel {formatNumber(route.noTravelMiles)} mi</span>}
      {route.unknownMiles > 0 && <span>Unknown {formatNumber(route.unknownMiles)} mi</span>}
    </div>
    <div className="mt-2.5 flex h-1.5 overflow-hidden rounded-full bg-line" aria-label={route.exposure.filter((entry) => entry.miles > 0).map((entry) => `${formatNumber(entry.miles)} ${entry.risk === null ? 'unknown' : riskLabels[entry.risk]} miles`).join(', ')}>
      {route.exposure.filter((entry) => entry.miles > 0).map((entry) => <span key={entry.risk ?? 'unknown'} style={{ width: `${route.distance > 0 ? entry.miles / route.distance * 100 : 0}%`, backgroundColor: riskColor(entry.risk) }} />)}
    </div>
    {(selected || route.risk === 'no-travel') && <p className="mt-2.5 text-[11px] leading-relaxed text-muted">{route.explanation}</p>}
    {!!route.avoid?.length && <p className="mt-2 text-[10px] text-subtle">Avoids {route.avoid.map(value => value === 'toll' ? 'toll roads' : value === 'motorway' ? 'motorways' : value).join(', ')}</p>}
  </button>;
}
