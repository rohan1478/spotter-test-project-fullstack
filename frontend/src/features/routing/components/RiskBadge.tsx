import type { RiskLevel } from '../types';

export const riskLabels: Record<RiskLevel, string> = {
  low: 'Low', moderate: 'Moderate', high: 'High', severe: 'Severe', 'no-travel': 'No Travel',
};
export const riskColors: Record<RiskLevel, string> = {
  low: 'var(--color-low)', moderate: 'var(--color-moderate)', high: 'var(--color-high)',
  severe: 'var(--color-severe)', 'no-travel': 'var(--color-no-travel)',
};

export const riskColor = (risk: RiskLevel | null) => risk === null ? 'var(--color-subtle)' : riskColors[risk];

export function RiskBadge({ risk }: { risk: RiskLevel | null }) {
  return <span className="inline-flex shrink-0 items-center gap-1.5 rounded-md border px-2 py-1 text-[10px] font-semibold leading-none"
    style={{ color: riskColor(risk), borderColor: `color-mix(in srgb, ${riskColor(risk)} 35%, transparent)`, background: `color-mix(in srgb, ${riskColor(risk)} 10%, transparent)` }}>
    <span className="size-1 rounded-full" style={{ backgroundColor: riskColor(risk) }} />
    {risk === null ? 'Unavailable' : riskLabels[risk]}{risk === 'no-travel' || risk === null ? '' : ' risk'}
  </span>;
}
