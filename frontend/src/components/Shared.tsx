import type { PropsWithChildren, ReactNode } from 'react';

export function Icon({ name, size = 18 }: { name: string; size?: number }) {
  const common = { width: size, height: size, viewBox: '0 0 24 24', fill: 'none', stroke: 'currentColor', strokeWidth: 1.8, strokeLinecap: 'round' as const, strokeLinejoin: 'round' as const, 'aria-hidden': true as const };
  const paths: Record<string, ReactNode> = {
    command: <><rect x="3" y="4" width="18" height="16" rx="2"/><path d="M8 8h8M8 12h4M8 16h7"/></>,
    home: <><path d="m3 10 9-7 9 7"/><path d="M5 9v11h14V9M9 20v-6h6v6"/></>,
    compare: <><path d="M12 4v16M4 7h5M15 7h5M4 17h5M15 17h5"/><circle cx="7" cy="7" r="2"/><circle cx="17" cy="17" r="2"/></>,
    report: <><path d="M12 3 4 6v6c0 5 3.4 8 8 9 4.6-1 8-4 8-9V6l-8-3Z"/><path d="M12 8v5M12 16h.01"/></>,
    play: <path d="m8 5 12 7-12 7V5Z" fill="currentColor" stroke="none"/>,
    pause: <><path d="M8 5v14M16 5v14" strokeWidth="3"/></>,
    back: <><path d="m14 5-7 7 7 7"/><path d="M20 12H7"/></>,
    next: <><path d="m10 5 7 7-7 7"/><path d="M4 12h13"/></>,
    check: <path d="m5 12 4 4L19 6"/>,
    audio: <><path d="M4 10v4M8 7v10M12 4v16M16 7v10M20 10v4"/></>,
    offline: <><path d="m2 2 20 20M8.5 8.5A5 5 0 0 1 17 12M5 5a11 11 0 0 1 14 0M2 9a16 16 0 0 1 3-2M22 9a16 16 0 0 0-3-2M12 20h.01"/></>,
    pin: <><path d="M20 10c0 5-8 12-8 12S4 15 4 10a8 8 0 1 1 16 0Z"/><circle cx="12" cy="10" r="2.5"/></>,
    arrow: <><path d="M7 17 17 7M7 7h10v10"/></>,
    menu: <><path d="M4 7h16M4 12h16M4 17h16"/></>,
    close: <><path d="m6 6 12 12M18 6 6 18"/></>,
    download: <><path d="M12 3v12m0 0 5-5m-5 5-5-5"/><path d="M4 17v4h16v-4"/></>,
    shield: <><path d="M12 3 4 6v6c0 5 3.4 8 8 9 4.6-1 8-4 8-9V6l-8-3Z"/><path d="m9 12 2 2 4-4"/></>,
  };
  return <svg {...common}>{paths[name] || <circle cx="12" cy="12" r="8"/>}</svg>;
}

export function Pill({ children, tone = 'neutral', className = '' }: PropsWithChildren<{ tone?: 'neutral' | 'green' | 'amber' | 'red' | 'blue' | 'violet'; className?: string }>) {
  return <span className={`pill pill-${tone} ${className}`}>{children}</span>;
}

export function Panel({ children, className = '', title, aside }: PropsWithChildren<{ className?: string; title?: string; aside?: ReactNode }>) {
  return <section className={`panel ${className}`}>
    {(title || aside) && <div className="panel-heading">{title && <h2>{title}</h2>}{aside}</div>}
    {children}
  </section>;
}

export function EmptyState({ title, detail, icon = 'pin' }: { title: string; detail: string; icon?: string }) {
  return <div className="empty-state"><span className="empty-icon"><Icon name={icon} size={20}/></span><strong>{title}</strong><p>{detail}</p></div>;
}

export function SectionEyebrow({ children }: PropsWithChildren) { return <div className="eyebrow">{children}</div>; }

