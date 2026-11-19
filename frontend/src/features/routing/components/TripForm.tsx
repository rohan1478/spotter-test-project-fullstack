import { ArrowLeftRight, LoaderCircle, Search } from 'lucide-react';
import type { FormEvent } from 'react';
import { Button } from '../../../components/ui/Button';
import { Field } from '../../../components/ui/Field';
import { SegmentedControl } from '../../../components/ui/SegmentedControl';
import type { DataMode, TripInput } from '../types';
import { LocationInput } from './LocationInput';
import { localDateTime } from '../utils/format';

export function TripForm({ value, onChange, onSubmit, loading, error, mode, onCancel }: {
  value: TripInput; onChange: (trip: TripInput) => void; onSubmit: () => void; loading: boolean; error: string | null;
  mode: DataMode; onCancel: () => void;
}) {
  function submit(event: FormEvent) { event.preventDefault(); onSubmit(); }
  const set = <K extends keyof TripInput>(key: K, input: TripInput[K]) => onChange({ ...value, [key]: input });
  return <section aria-label="Trip planner" className="panel shrink-0 px-4 py-3.5">
    <form onSubmit={submit}>
      <div className="grid grid-cols-2 items-end gap-3 md:grid-cols-[1fr_auto_1fr] xl:grid-cols-[1fr_auto_1fr_1.35fr_.8fr_1.2fr_auto]">
        <LocationInput id="origin" label="Origin" value={value.origin} selected={value.originPlace} live={mode === 'live'}
          onChange={origin => onChange({ ...value, origin, originPlace: undefined, departureTimeZone: undefined })}
          onSelect={place => onChange({ ...value, origin: place.label, originPlace: place, departureTimeZone: place.timeZone,
            departure: value.departure || localDateTime(new Date(Date.now() + 3_600_000), place.timeZone) })} />
        <div className="hidden md:block"><Button variant="secondary" aria-label="Swap origin and destination" className="h-11 w-10 px-0" onClick={() => onChange({ ...value, origin: value.destination, destination: value.origin, originPlace: value.destinationPlace, destinationPlace: value.originPlace, departureTimeZone: value.destinationPlace?.timeZone })}><ArrowLeftRight size={17} /></Button></div>
        <LocationInput id="destination" label="Destination" value={value.destination} selected={value.destinationPlace} live={mode === 'live'}
          onChange={destination => onChange({ ...value, destination, destinationPlace: undefined })}
          onSelect={place => onChange({ ...value, destination: place.label, destinationPlace: place })} />
        <Field id="departure" label={<>Departure <span className="font-normal text-subtle">· origin time</span></>}>
          <input id="departure" type="datetime-local" className="field-input text-xs" value={value.departure} required onChange={(event) => set('departure', event.target.value)} />
        </Field>
        <Field id="load-weight" label="Load weight" className="relative">
          <input id="load-weight" type="number" min="0" step="any" required className="field-input pr-8" value={value.loadWeight || ''} onChange={(event) => set('loadWeight', Number(event.target.value))} />
          <span className="pointer-events-none absolute right-3 bottom-3 text-xs text-muted">lb</span>
        </Field>
        <div className="min-w-0"><span className="mb-2 block text-xs font-semibold">Checkpoints</span>
          <SegmentedControl label="Checkpoint spacing" value={value.spacing} options={[{ value: 10, label: '10 mi' }, { value: 25, label: '25 mi' }, { value: 50, label: '50 mi' }]} onChange={(spacing) => set('spacing', spacing)} className="h-11" />
        </div>
        <Button type="submit" disabled={loading} className="col-span-2 md:col-span-1 xl:px-4">
          {loading ? <LoaderCircle size={16} className="animate-spin" /> : <Search size={16} />} {loading ? 'Comparing…' : 'Compare routes'}
        </Button>
      </div>
      <div className="mt-2 flex flex-wrap items-center justify-between gap-2 text-[10px] text-subtle">
        <span>{mode === 'demo' ? 'Demo trip · illustrative routes and forecasts' : value.originPlace ? `Departure time zone: ${value.originPlace.timeZone} · Select both locations from search results` : 'Select locations from search results to set the departure time zone.'}</span>
        {loading && <button type="button" onClick={onCancel} className="text-accent underline">Cancel comparison</button>}
      </div>
      {error && <p role="alert" className="mt-3 rounded-md border border-severe/30 bg-severe/10 px-3 py-2 text-xs leading-relaxed text-severe">{error}</p>}
    </form>
  </section>;
}
