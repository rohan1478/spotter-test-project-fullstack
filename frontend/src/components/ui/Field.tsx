import type { ReactNode } from 'react';

export function Field({ id, label, children, className = '' }: {
  id: string; label: ReactNode; children: ReactNode; className?: string;
}) {
  return <div className={`min-w-0 ${className}`}>
    <label htmlFor={id} className="mb-2 block text-xs font-semibold text-ink">{label}</label>
    {children}
  </div>;
}
