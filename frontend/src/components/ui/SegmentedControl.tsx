export function SegmentedControl<T extends string | number>({ label, value, options, onChange, className = '' }: {
  label: string; value: T; options: { value: T; label: string }[]; onChange: (value: T) => void; className?: string;
}) {
  return <div role="group" aria-label={label} className={`flex rounded-lg border border-line bg-field p-0.5 ${className}`}>
    {options.map((option) => <button key={option.value} type="button" aria-pressed={value === option.value}
      onClick={() => onChange(option.value)}
      className={`flex min-h-9 flex-1 items-center justify-center gap-2 whitespace-nowrap rounded-md px-3 text-xs font-medium transition-colors ${value === option.value ? 'bg-accent-strong text-white shadow-sm' : 'text-muted hover:bg-panel-raised hover:text-ink'}`}>
      {option.label}
    </button>)}
  </div>;
}
