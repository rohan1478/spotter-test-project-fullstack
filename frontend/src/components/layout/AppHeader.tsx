import { Route } from 'lucide-react';
import type { DataMode } from '../../features/routing/types';

export function AppHeader({ mode, onModeChange }: { mode: DataMode; onModeChange: (mode: DataMode) => void }) {
  return <header className="flex min-h-18 items-center justify-between gap-4 border-b border-line px-4 py-3 sm:px-6">
    <div className="flex items-center gap-3">
      <Route className="size-8 shrink-0 text-accent sm:size-10" strokeWidth={1.7} aria-hidden="true" />
      <div><h1 className="text-base font-bold tracking-tight sm:text-xl">Weather-aware routing</h1>
        <p className="mt-0.5 text-xs text-muted sm:text-sm">Safer journeys, informed by weather</p></div>
    </div>
    <div className="flex shrink-0 items-center gap-3">
      <span className="hidden text-[11px] text-muted md:block">{mode === 'live' ? 'Live mode' : 'Demo · Sample data'}</span>
      <div role="group" aria-label="Data source" className="flex rounded-lg border border-line bg-field p-0.5">
        {(['live', 'demo'] as const).map(value => <button key={value} type="button" aria-pressed={mode === value} onClick={() => onModeChange(value)} className={`rounded-md px-2.5 py-1.5 text-[11px] font-medium ${mode === value ? 'bg-accent-strong text-ink' : 'text-muted hover:text-ink'}`}>{value === 'live' ? 'Live' : 'Demo'}</button>)}
      </div>
    </div>
  </header>;
}
