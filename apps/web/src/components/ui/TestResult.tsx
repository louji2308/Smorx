'use client';

import { forwardRef, type HTMLAttributes } from 'react';
import { cn } from '@/lib/design-tokens';
import { StateBadge, type TrustState } from './StateBadge';
import { lucideReact } from '@/lib/lucide-imports';

const { FileText, CheckCircle, XCircle, AlertTriangle, Clock, ChevronRight, SkipForward } = lucideReact;

/**
 * TestResult - Displays a test result with status, duration, and output
 */
export interface TestResultProps extends Omit<HTMLAttributes<HTMLDivElement>, 'onSelect'> {
  result: TestResultData;
  variant?: 'card' | 'compact' | 'list';
  onSelect?: (result: TestResultData) => void;
  selected?: boolean;
}

export interface TestResultData {
  id: string;
  executionId: string;
  name: string;
  status: 'passed' | 'failed' | 'skipped' | 'error';
  duration: number;
  stdout?: string;
  stderr?: string;
  file?: string;
  line?: number;
}

const statusConfig = {
  passed: { label: 'PASSED', state: 'CERTIFIED' as TrustState, icon: <CheckCircle size={14} />, color: 'text-[var(--color-trust-certified)]' },
  failed: { label: 'FAILED', state: 'VIOLATED' as TrustState, icon: <XCircle size={14} />, color: 'text-[var(--color-trust-violated)]' },
  skipped: { label: 'SKIPPED', state: 'OBSERVED' as TrustState, icon: <SkipForward size={14} />, color: 'text-[var(--color-text-muted)]' },
  error: { label: 'ERROR', state: 'REPAIR_REQUIRED' as TrustState, icon: <AlertTriangle size={14} />, color: 'text-[var(--color-trust-repair)]' },
} as const;

export const TestResult = forwardRef<HTMLDivElement, TestResultProps>(
  ({ result, variant = 'card', onSelect, selected, className, ...props }, ref) => {
    const handleClick = () => onSelect?.(result);
    const config = statusConfig[result.status];

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
          <span className={cn('flex-shrink-0', config.color)}>
            {config.icon}
          </span>
          <div className="flex-1 min-w-0">
            <p className="text-body-sm font-medium truncate">{result.name}</p>
            <p className="text-caption text-[var(--color-text-muted)] truncate">{result.file || ''}</p>
          </div>
          <StateBadge state={config.state} size="sm" variant="dot" />
          <span className="text-caption font-mono text-[var(--color-text-muted)]">{result.duration}ms</span>
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
            <span className={cn('flex-shrink-0', config.color)}>
              {config.icon}
            </span>
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-2">
                <span className="text-body-sm font-medium truncate">{result.name}</span>
                <StateBadge state={config.state} size="sm" variant="dot" />
              </div>
              <div className="flex items-center gap-3 mt-1 text-caption text-[var(--color-text-muted)]">
                {result.file && <span className="flex items-center gap-1 truncate max-w-[200px]"><FileText size={12} />{result.file}</span>}
                <span className="flex items-center gap-1"><Clock size={12} />{result.duration}ms</span>
              </div>
            </div>
            <ChevronRight className="text-[var(--color-text-muted)] flex-shrink-0" size={16} />
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
            <span className={cn('flex-shrink-0', config.color)}>
              {config.icon}
            </span>
            <div>
              <p className="text-body font-medium truncate max-w-[400px]">{result.name}</p>
              {result.file && <p className="text-caption text-[var(--color-text-muted)]">{result.file}{result.line ? `:${result.line}` : ''}</p>}
            </div>
          </div>
          <div className="flex items-center gap-2">
            <StateBadge state={config.state} size="sm" />
            <span className="font-mono text-code-sm text-[var(--color-text-muted)]">{result.duration}ms</span>
          </div>
        </div>

        <div className="grid grid-cols-2 gap-4 mb-3">
          <div>
            <p className="text-caption text-[var(--color-text-muted)] mb-1">Status</p>
            <p className={cn('text-body-sm font-mono', config.color)}>{config.label}</p>
          </div>
          <div>
            <p className="text-caption text-[var(--color-text-muted)] mb-1">Execution</p>
            <p className="text-body-sm font-mono truncate">{result.executionId.slice(0, 16)}...</p>
          </div>
        </div>

        {(result.stdout || result.stderr) && (
          <details className="mb-3">
            <summary className="flex items-center gap-2 text-caption text-[var(--color-text-muted)] cursor-pointer">
              <ChevronRight size={12} className="transition-transform" />
              Output
            </summary>
            <div className="mt-2 space-y-2">
              {result.stdout && (
                <div>
                  <p className="text-caption text-[var(--color-text-muted)] mb-1">stdout</p>
                  <pre className="p-3 bg-[var(--color-surface)] rounded border border-[var(--color-surface-border)] overflow-x-auto text-code-sm text-[var(--color-text-secondary)] max-h-[200px] overflow-y-auto">
                    <code>{result.stdout}</code>
                  </pre>
                </div>
              )}
              {result.stderr && (
                <div>
                  <p className="text-caption text-[var(--color-trust-violated)] mb-1">stderr</p>
                  <pre className="p-3 bg-[var(--color-surface)] rounded border border-[var(--color-surface-border)] overflow-x-auto text-code-sm text-[var(--color-trust-violated)] max-h-[200px] overflow-y-auto">
                    <code>{result.stderr}</code>
                  </pre>
                </div>
              )}
            </div>
          </details>
        )}
      </div>
    );
  }
);

TestResult.displayName = 'TestResult';