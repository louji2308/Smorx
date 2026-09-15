'use client';

import { forwardRef, type HTMLAttributes } from 'react';
import { cn } from '@/lib/design-tokens';
import { StateBadge, type TrustState } from './StateBadge';
import { lucideReact } from '@/lib/lucide-imports';

const { GitBranch, ChevronRight, FileText, Terminal, FlaskConical } = lucideReact;

/**
 * ProvenanceLink - Displays a provenance chain link with type and target
 */
export interface ProvenanceLinkProps extends Omit<HTMLAttributes<HTMLDivElement>, 'onSelect'> {
  link: ProvenanceLinkData;
  variant?: 'card' | 'compact' | 'list';
  onSelect?: (link: ProvenanceLinkData) => void;
  selected?: boolean;
}

export interface ProvenanceLinkData {
  id: string;
  evidenceId: string;
  type: 'task' | 'run' | 'agent_run' | 'subagent_run' | 'execution' | 'verification_case';
  targetId: string;
  targetLabel: string;
  timestamp?: string;
  description?: string;
}

const typeIcons = {
  task: <FileText size={14} />,
  run: <Terminal size={14} />,
  agent_run: <GitBranch size={14} />,
  subagent_run: <GitBranch size={14} />,
  execution: <Terminal size={14} />,
  verification_case: <FlaskConical size={14} />,
} as const;

const typeLabels = {
  task: 'Task',
  run: 'Run',
  agent_run: 'Agent Run',
  subagent_run: 'Subagent Run',
  execution: 'Execution',
  verification_case: 'Verification Case',
} as const;

export const ProvenanceLink = forwardRef<HTMLDivElement, ProvenanceLinkProps>(
  ({ link, variant = 'card', onSelect, selected, className, ...props }, ref) => {
    const handleClick = () => onSelect?.(link);
    const Icon = typeIcons[link.type] || <FileText size={14} />;
    const typeLabel = typeLabels[link.type] || link.type;

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
            <p className="text-body-sm font-medium truncate">{typeLabel}</p>
            <p className="text-caption text-[var(--color-text-muted)] truncate">{link.targetLabel}</p>
          </div>
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
              <p className="text-body-sm font-medium">{typeLabel}</p>
              <p className="text-caption text-[var(--color-text-muted)] truncate">{link.targetLabel}</p>
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
            <span className="flex items-center justify-center w-10 h-10 rounded-lg bg-[var(--color-surface)] border border-[var(--color-surface-border)] text-[var(--color-text-muted)]">
              {Icon}
            </span>
            <div>
              <p className="text-body font-medium">{typeLabel}</p>
              <p className="text-caption text-[var(--color-text-muted)]">{link.targetLabel}</p>
            </div>
          </div>
          <span className="font-mono text-code-sm text-[var(--color-text-muted)]">{link.targetId.slice(0, 16)}...</span>
        </div>

        <div className="grid grid-cols-2 gap-4 mb-3">
          <div>
            <p className="text-caption text-[var(--color-text-muted)] mb-1">Evidence</p>
            <p className="text-body-sm font-mono truncate">{link.evidenceId.slice(0, 16)}...</p>
          </div>
          {link.timestamp && (
            <div>
              <p className="text-caption text-[var(--color-text-muted)] mb-1">Timestamp</p>
              <p className="text-body-sm font-mono">{new Date(link.timestamp).toLocaleString()}</p>
            </div>
          )}
        </div>

        {link.description && (
          <div className="pt-3 border-t border-[var(--color-surface-border)]">
            <p className="text-caption text-[var(--color-text-muted)] mb-1">Description</p>
            <p className="text-body-sm">{link.description}</p>
          </div>
        )}
      </div>
    );
  }
);

ProvenanceLink.displayName = 'ProvenanceLink';