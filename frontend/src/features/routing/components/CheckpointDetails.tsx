import { Clock3, CloudRain, MapPin, Snowflake, Wind, X } from 'lucide-react';
import type { Checkpoint, DataMode } from '../types';
import { formatTime, formatReading, formatNumber } from '../utils/format';
import { RiskBadge } from './RiskBadge';

export function CheckpointDetails({ checkpoint, onClose, mode, expired }: { checkpoint: Checkpoint; onClose: () => void; mode: DataMode; expired: boolean }) {
  return <section aria-label="Checkpoint weather" className="panel w-full bg-panel/95 p-3.5 backdrop-blur-sm sm:w-80">
    <div className="flex items-center gap-2"><MapPin size={14} className="text-accent" /><h3 className="min-w-0 flex-1 truncate text-xs font-semibold">Checkpoint {checkpoint.number} · {checkpoint.name}</h3>
      <button aria-label="Close checkpoint details" onClick={onClose} className="rounded p-1 text-subtle hover:bg-field hover:text-ink"><X size={14} /></button>
    </div>
    <div className="mt-2.5 flex items-center justify-between"><span className="flex items-center gap-1.5 text-xs text-muted"><Clock3 size={13} />ETA <strong className="font-medium text-ink">{formatTime(checkpoint.arrival, checkpoint.timeZone)}</strong></span><RiskBadge risk={checkpoint.risk} /></div>
    <div className="mt-3 grid grid-cols-3 divide-x divide-line border-t border-line pt-3">
      {[{ Icon: Wind, label: 'Wind', value: formatReading(checkpoint.wind, 'mph') }, { Icon: CloudRain, label: 'Rain', value: formatReading(checkpoint.rain, 'in/hr') }, { Icon: Snowflake, label: 'Snow', value: formatReading(checkpoint.snow, 'in/hr') }].map(({ Icon, label, value }) => <div key={label} className="pl-2 first:pl-0">
        <div className="flex items-center gap-1.5 text-[10px] text-muted"><Icon size={14} />{label}</div><p className="mt-1 text-[11px] font-semibold">{value}</p>
      </div>)}
    </div>
    <p className="mt-3 text-[10px] text-subtle">{expired ? 'Expired forecast' : mode === 'demo' ? 'Sample forecast at truck arrival' : 'Forecast at truck arrival'} · Mile {formatNumber(checkpoint.miles)}</p>
    {checkpoint.weatherStatus === 'missing' && <p className="mt-2 text-[10px] text-moderate">Required weather is unavailable at this checkpoint.</p>}
    {!!checkpoint.riskReasons?.length && <details className="mt-2 text-[10px] leading-relaxed text-muted"><summary className="cursor-pointer text-accent">Risk details</summary><ul className="mt-1 space-y-1">{checkpoint.riskReasons.map(reason => <li key={reason}>{reason}</li>)}</ul></details>}
  </section>;
}
