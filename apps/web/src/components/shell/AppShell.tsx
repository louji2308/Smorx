'use client';

import { useEffect } from 'react';
import { useAppStore } from '@/store/appStore';
import { Navigation } from './Navigation';
import { WorkflowProgress } from './WorkflowProgress';
import { ContextDrawer } from '@/components/ui/ContextDrawer';
import { cn } from '@/lib/design-tokens';
import { lucideReact } from '@/lib/lucide-imports';

const { AlertTriangle } = lucideReact;

export function AppShell({ children }: { children: React.ReactNode }) {
  const { drawerState } = useAppStore();

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && drawerState.isOpen) {}
      if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
        e.preventDefault();
      }
    };
    document.addEventListener('keydown', handleKeyDown);
    return () => document.removeEventListener('keydown', handleKeyDown);
  }, [drawerState.isOpen]);

  return (
    <div className="layout-shell">
      <Navigation />
      <main className="layout-main flex-1 flex flex-col overflow-hidden">
        <div className="layout-content flex-1 overflow-auto bg-[var(--color-smoke)]">
          <WorkflowProgress />
          {children}
        </div>
      </main>
      <ContextDrawer
        isOpen={drawerState.isOpen}
        onClose={() => useAppStore.getState().closeDrawer()}
        type={drawerState.type}
        title={drawerState.type ? drawerState.type.charAt(0).toUpperCase() + drawerState.type.slice(1).replace('-', ' ') : ''}
        data={drawerState.data}
        size="lg"
      />
    </div>
  );
}

export function JourneyPage({ title, description, children, actions }: {
  title: string;
  description?: string;
  children: React.ReactNode;
  actions?: React.ReactNode;
}) {
  return (
    <div className="space-y-5 p-6">
      <div className="flex items-start justify-between gap-4">
        <div>
          <h1 className="text-[1.6rem] font-bold text-[var(--color-text-primary)] tracking-tight font-display">{title}</h1>
          {description && (
            <p className="text-[0.875rem] text-[var(--color-text-secondary)] mt-1 max-w-2xl">{description}</p>
          )}
        </div>
        {actions && (
          <div className="flex-shrink-0 flex items-center gap-2">
            {actions}
          </div>
        )}
      </div>
      {children}
    </div>
  );
}

export function Section({ title, description, children, className }: {
  title: string;
  description?: string;
  children: React.ReactNode;
  className?: string;
}) {
  return (
    <section className={cn('space-y-4', className)}>
      <header className="flex items-center justify-between">
        <div>
          <h2 className="text-[1rem] font-bold text-[var(--color-text-primary)]">{title}</h2>
          {description && <p className="text-[0.8rem] text-[var(--color-text-muted)] mt-0.5">{description}</p>}
        </div>
      </header>
      <div>{children}</div>
    </section>
  );
}

export function EmptyState({ icon: Icon, title, description, action }: {
  icon: React.ReactNode;
  title: string;
  description?: string;
  action?: React.ReactNode;
}) {
  return (
    <div className="flex flex-col items-center justify-center py-20 px-8 text-center">
      <div className="flex items-center justify-center w-20 h-20 rounded-2xl bg-[var(--color-accent-tint)] border border-[var(--color-accent-soft)] text-[var(--color-accent-primary)] mb-5">
        {Icon}
      </div>
      <h3 className="text-[1.1rem] font-bold text-[var(--color-text-primary)]">{title}</h3>
      {description && <p className="text-[0.875rem] text-[var(--color-text-secondary)] mt-2 max-w-md leading-relaxed">{description}</p>}
      {action && <div className="mt-5">{action}</div>}
    </div>
  );
}

export function LoadingState({ message = 'Loading...' }: { message?: string }) {
  return (
    <div className="flex flex-col items-center justify-center py-16 px-8 text-center">
      <div className="w-8 h-8 border-[2.5px] border-[var(--color-accent-soft)] border-t-[var(--color-accent-primary)] rounded-full animate-spin mb-4" />
      <p className="text-[0.875rem] text-[var(--color-text-secondary)]">{message}</p>
    </div>
  );
}

export function ErrorState({ title = 'Error', message, onRetry }: {
  title?: string;
  message: string;
  onRetry?: () => void;
}) {
  return (
    <div className="flex flex-col items-center justify-center py-16 px-8 text-center">
      <div className="flex items-center justify-center w-16 h-16 rounded-2xl bg-[#fcefee] border border-[#f5d5d3] text-[#d8493c] mb-4">
        <AlertTriangle size={28} strokeWidth={1.75} />
      </div>
      <h3 className="text-[1.1rem] font-bold text-[var(--color-text-primary)]">{title}</h3>
      <p className="text-[0.875rem] text-[var(--color-text-secondary)] mt-2 max-w-md">{message}</p>
      {onRetry && (
        <button onClick={onRetry} className="btn btn--primary mt-5">Try Again</button>
      )}
    </div>
  );
}
