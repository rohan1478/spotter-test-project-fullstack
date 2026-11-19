import type { ButtonHTMLAttributes } from 'react';

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'primary' | 'icon' | 'secondary';
}

export function Button({ variant = 'primary', className = '', type = 'button', ...props }: ButtonProps) {
  const styles = {
    primary: 'inline-flex h-11 items-center justify-center gap-2 rounded-lg border border-accent-strong bg-accent-strong px-5 text-sm font-semibold text-ink transition-colors hover:bg-accent-hover',
    icon: 'map-button',
    secondary: 'inline-flex h-10 items-center justify-center gap-2 rounded-lg border border-line bg-field px-3 text-sm text-muted transition-colors hover:bg-panel-raised hover:text-ink',
  };
  return <button type={type} className={`${styles[variant]} ${className}`} {...props} />;
}
