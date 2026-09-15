'use client';

import { forwardRef, type HTMLAttributes } from 'react';
import { cn, formatRelativeTime } from '@/lib/design-tokens';
import { StateBadge, type TrustState } from './StateBadge';
import { lucideReact } from '@/lib/lucide-imports';

const { Terminal, Clock, ChevronRight, FileCode, FlaskConical } = lucideReact;

/**
 * ExecutionEvent - Displays a sandbox execution event with command, result, and timing
 */
export interface ExecutionEventProps extends Omit<HTMLAttributes<HTMLDivElement>, 'onSelect'> {
  event: ExecutionEventData;
  variant?: 'card' | 'compact' | 'list';
  onSelect?: (event: ExecutionEventData) => void;
  selected?: boolean;
}

export interface ExecutionEventData {
  id: string;
  runId: string;
  agentRunId?: string;
  kind: 'COMMAND' | 'TEST' | 'BUILD' | 'VERIFICATION';
  command?: string;
  cwd?: string;
  exitCode?: number;
  stdout?: string;
  stderr?: string;
  durationMs?: number;
  status: 'PENDING' | 'RUNNING' | 'COMPLETED' | 'FAILED';
  startedAt?: string;
  finishedAt?: string;
  machineResult: Record<string, unknown>;
}

const kindIcons = {
  COMMAND: <Terminal size={14} />,
  TEST: <FileCode size={14} />,
  BUILD: <FileCode size={14} />,
  VERIFICATION: <FlaskConical size={14} />,
} as const;

const kindLabels = {
  COMMAND: 'Command',
  TEST: 'Test',
  BUILD: 'Build',
  VERIFICATION: 'Verification',
} as const;

export const ExecutionEvent = forwardRef<HTMLDivElement, ExecutionEventProps>(
  ({ event, variant = 'card', onSelect, selected, className, ...props }, ref) => {
    const handleClick = () => onSelect?.(event);
    const Icon = kindIcons[event.kind] || <Terminal size={14} />;
    const kindLabel = kindLabels[event.kind] || event.kind;

    const statusState: TrustState = 
      event.status === 'COMPLETED' && event.exitCode === 0 ? 'CERTIFIED' :
      event.status === 'FAILED' || (event.exitCode !== undefined && event.exitCode !== 0) ? 'VIOLATED' :
      event.status === 'RUNNING' ? 'UNVERIFIED' :
      'OBSERVED';

    if (variant === 'compact') {
      return (
        <div
          ref={ref}
          className={cn(
            'flex items-center gap-3 px-3 py-2 rounded-lg border transition-all',
            'bg-[var(--color-surface-elevated)] border-[var(--color-surface-border)]',
            selected && 'border-[var(--color-accent-primary)] bg-[color-mix(in_srgb,_var(--color-accent-primary)_5%,_transparent)]',
            className
          )}
          onClick={handleClick}
          {...props}
        >
          <span className="flex items-center justify-center w-8 h-8 rounded-lg bg-[var(--color-surface)] border border-[var(--color-surface-border)] text-[var(--color-text-muted)]">
            {Icon}
          </span>
          <div className="flex-1 min-w-0">
            <p className="text-body-sm font-medium truncate">{event.command || kindLabel}</p>
            <p className="text-caption text-[var(--color-text-muted)] truncate">{event.cwd || event.runId.slice(0, 12)}...</p>
          </div>
          <StateBadge state={statusState} size="sm" variant="dot" />
          <ChevronRight className="text-[var(--color-text-muted)] flex-shrink-0" size={16} />
        </div>
      );
    }

    if (variant === 'list') {
      return (
        <div
          ref={ref}
          className={cn(
            'px-3 py-2 rounded-lg border transition-all',
            'bg-[var(--color-surface-elevated)] border-[var(--color-surface-border)]',
            selected && 'border-[var(--color-accent-primary)] bg-[color-mix(in_srgb,_var(--color-accent-primary)_5%,_transparent)]',
            className
          )}
          onClick={handleClick}
          {...props}
        >
          <div className="flex items-center gap-3">
            <span className="flex items-center justify-center w-8 h-8 rounded-lg bg-[var(--color-surface)] border border-[var(--color-surface-border)] text-[var(--color-text-muted)] flex-shrink-0">
              {Icon}
            </span>
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-2">
                <span className="text-body-sm font-medium truncate">{event.command || kindLabel}</span>
                <StateBadge state={statusState} size="sm" variant="dot" />
              </div>
              <p className="text-caption text-[var(--color-text-muted)] truncate mt-1">{event.cwd || ''}</p>
              <div className="flex items-center gap-3 mt-1 text-caption text-[var(--color-text-muted)]">
                <span className="flex items-center gap-1">
                  <Clock size={12} />
                  {event.startedAt ? formatRelativeTime(event.startedAt) : 'Not started'}
                </span>
                {event.durationMs && (
                  <span className="flex items-center gap-1">
                    {event.durationMs}ms
                  </span>
                )}
              </div>
            </div>
            <ChevronRight className="text-[var(--color-text-muted)] flex-shrink-0 mt-1" size={16} />
          </div>
        </div>
      );
    }

    return (
      <div
        ref={ref}
        className={cn(
          'surface-card p-4 transition-all',
          selected && 'border-[var(--color-accent-primary)] shadow-[var(--shadow-elevation-2)]',
          className
        )}
        onClick={handleClick}
        {...props}
      >
        <div className="flex items-start justify-between gap-4 mb-3">
          <div className="flex items-center gap-3">
            <span className="flex items-center justify-center w-10 h-10 rounded-lg bg-[var(--color-surface)] border border-[var(--color-surface-border)] text-[var(--color-text-muted)]">
              {Icon}
            </span>
            <div>
              <p className="text-body font-medium truncate max-w-[400px]">{event.command || kindLabel}</p>
              <p className="text-caption text-[var(--color-text-muted)]">{event.cwd || 'N/A'}</p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <StateBadge state={statusState} size="sm" />
            <span className="font-mono text-code-sm text-[var(--color-text-muted)]">{event.id.slice(0, 12)}...</span>
          </div>
        </div>

        <div className="grid grid-cols-3 gap-4 mb-3">
          <div>
            <p className="text-caption text-[var(--color-text-muted)] mb-1">Kind</p>
            <p className="text-body-sm font-mono">{kindLabel}</p>
          </div>
          <div>
            <p className="text-caption text-[var(--color-text-muted)] mb-1">Exit Code</p>
            <p className={cn('text-body-sm font-mono', event.exitCode === 0 ? 'text-[var(--color-trust-certified)]' : event.exitCode !== undefined ? 'text-[var(--color-trust-violated)]' : 'text-[var(--color-text-muted)]')}>
              {event.exitCode !== undefined ? event.exitCode : '—'}
            </p>
          </div>
          <div>
            <p className="text-caption text-[var(--color-text-muted)] mb-1">Duration</p>
            <p className="text-body-sm font-mono">{event.durationMs !== undefined ? `${event.durationMs}ms` : '—'}</p>
          </div>
        </div>

        {(event.stdout || event.stderr) && (
          <details className="mb-3">
            <summary className="flex items-center gap-2 text-caption text-[var(--color-text-muted)] cursor-pointer">
              <ChevronRight size={12} className="transition-transform" />
              Output
            </summary>
            <div className="mt-2 space-y-2">
              {event.stdout && (
                <div>
                  <p className="text-caption text-[var(--color-text-muted)] mb-1">stdout</p>
                  <pre className="p-3 bg-[var(--color-surface)] rounded border border-[var(--color-surface-border)] overflow-x-auto text-code-sm text-[var(--color-text-secondary)] max-h-[200px] overflow-y-auto">
                    <code>{event.stdout}</code>
                  </pre>
                </div>
              )}
              {event.stderr && (
                <div>
                  <p className="text-caption text-[var(--color-trust-violated)] mb-1">stderr</p>
                  <pre className="p-3 bg-[var(--color-surface)] rounded border border-[var(--color-surface-border)] overflow-x-auto text-code-sm text-[var(--color-trust-violated)] max-h-[200px] overflow-y-auto">
                    <code>{event.stderr}</code>
                  </pre>
                </div>
              )}
            </div>
          </details>
        )}

        <details className="pt-3 border-t border-[var(--color-surface-border)]">
          <summary className="flex items-center gap-2 text-caption text-[var(--color-text-muted)] cursor-pointer">
            <ChevronRight size={12} className="transition-transform" />
            Machine Result
          </summary>
          <pre className="mt-2 p-3 bg-[var(--color-surface)] rounded border border-[var(--color-surface-border)] overflow-x-auto text-code-sm">
            <code>{JSON.stringify(event.machineResult, null, 2)}</code>
          </pre>
        </details>
      </div>
    );
  }
);

ExecutionEvent.displayName = 'ExecutionEvent';