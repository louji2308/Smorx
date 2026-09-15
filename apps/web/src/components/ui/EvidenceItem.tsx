'use client';

import { forwardRef, type HTMLAttributes } from 'react';
import { cn, formatRelativeTime, truncate } from '@/lib/design-tokens';
import { StateBadge, type TrustState } from './StateBadge';
import { lucideReact } from '@/lib/lucide-imports';

const { FileText, GitBranch, Terminal, FlaskConical, AlertTriangle, Clock, Hash, ChevronRight, Eye, Shield, Lock } = lucideReact;

/**
 * EvidenceItem - Displays a single evidence item with type, source, and provenance
 */
export interface EvidenceItemProps extends Omit<HTMLAttributes<HTMLDivElement>, 'onSelect'> {
  evidence: EvidenceData;
  variant?: 'card' | 'compact' | 'list';
  onSelect?: (evidence: EvidenceData) => void;
  selected?: boolean;
}

export interface EvidenceData {
  id: string;
  claimId?: string;
  evidenceType: string;
  source: string;
  timestamp: string;
  provenance?: string;
  relatedTaskId?: string;
  relatedRunId?: string;
  relatedArtifact?: string;
  machineResult: Record<string, unknown>;
  hash: string;
}

const evidenceTypeIcons: Record<string, React.ReactNode> = {
  STATIC_ANALYSIS: <FlaskConical size={14} />,
  DIFFERENTIAL_EXECUTION: <GitBranch size={14} />,
  HISTORICAL_GHOST_REPLAY: <AlertTriangle size={14} />,
  METAMORPHIC_CHECK: <FlaskConical size={14} />,
  ADVERSARIAL_SCENARIO: <AlertTriangle size={14} />,
  MUTATION_TEST: <FlaskConical size={14} />,
  EXECUTION_TRACE: <Terminal size={14} />,
  TEST_RESULT: <FileText size={14} />,
  RUNTIME_OBSERVATION: <Eye size={14} />,
  REPOSITORY_SNAPSHOT: <GitBranch size={14} />,
  MODEL_DECISION: <Shield size={14} />,
  CERTIFICATE_BINDING: <Lock size={14} />,
};

const evidenceTypeLabels: Record<string, string> = {
  STATIC_ANALYSIS: 'Static Analysis',
  DIFFERENTIAL_EXECUTION: 'Differential Execution',
  HISTORICAL_GHOST_REPLAY: 'Ghost Replay',
  METAMORPHIC_CHECK: 'Metamorphic Check',
  ADVERSARIAL_SCENARIO: 'Adversarial',
  MUTATION_TEST: 'Mutation Test',
  EXECUTION_TRACE: 'Execution Trace',
  TEST_RESULT: 'Test Result',
  RUNTIME_OBSERVATION: 'Runtime Observation',
  REPOSITORY_SNAPSHOT: 'Repository Snapshot',
  MODEL_DECISION: 'Model Decision',
  CERTIFICATE_BINDING: 'Certificate Binding',
};

export const EvidenceItem = forwardRef<HTMLDivElement, EvidenceItemProps>(
  ({ evidence, variant = 'card', onSelect, selected, className, ...props }, ref) => {
    const handleClick = () => onSelect?.(evidence);
    const Icon = evidenceTypeIcons[evidence.evidenceType] || <FileText size={14} />;
    const typeLabel = evidenceTypeLabels[evidence.evidenceType] || evidence.evidenceType;

    // Determine trust state from evidence type or machine result
    let trustState: TrustState = 'OBSERVED';
    if (evidence.machineResult?.status === 'passed' || evidence.machineResult?.exitCode === 0) {
      trustState = 'CERTIFIED';
    } else if (evidence.machineResult?.status === 'failed' || (evidence.machineResult?.exitCode && evidence.machineResult.exitCode !== 0)) {
      trustState = 'VIOLATED';
    }

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
            <p className="text-caption text-[var(--color-text-muted)] truncate">{evidence.source}</p>
          </div>
          <StateBadge state={trustState} size="sm" variant="dot" />
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
          <div className="flex items-start gap-3">
            <span className="flex items-center justify-center w-8 h-8 rounded-lg bg-[var(--color-surface)] border border-[var(--color-surface-border)] text-[var(--color-text-muted)] flex-shrink-0">
              {Icon}
            </span>
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-2">
                <span className="text-body-sm font-medium">{typeLabel}</span>
                <StateBadge state={trustState} size="sm" variant="dot" />
              </div>
              <p className="text-caption text-[var(--color-text-muted)] truncate mt-1">{evidence.source}</p>
              <div className="flex items-center gap-3 mt-1 text-caption text-[var(--color-text-muted)]">
                <span className="flex items-center gap-1">
                  <Clock size={12} />
                  {formatRelativeTime(evidence.timestamp)}
                </span>
                {evidence.provenance && (
                  <span className="flex items-center gap-1 truncate max-w-[200px]">
                    <Hash size={12} />
                    {truncate(evidence.provenance, 50)}
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
              <p className="text-body font-medium">{typeLabel}</p>
              <p className="text-caption text-[var(--color-text-muted)]">{evidence.source}</p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <StateBadge state={trustState} size="sm" />
            <span className="font-mono text-code-sm text-[var(--color-text-muted)]">{evidence.hash.slice(0, 16)}...</span>
          </div>
        </div>

        <div className="grid grid-cols-2 gap-4 mb-3">
          <div>
            <p className="text-caption text-[var(--color-text-muted)] mb-1">Timestamp</p>
            <p className="text-body-sm font-mono">{formatRelativeTime(evidence.timestamp)}</p>
          </div>
          <div>
            <p className="text-caption text-[var(--color-text-muted)] mb-1">Type</p>
            <p className="text-body-sm font-mono">{evidence.evidenceType}</p>
          </div>
        </div>

        {evidence.provenance && (
          <div className="mb-3">
            <p className="text-caption text-[var(--color-text-muted)] mb-1">Provenance</p>
            <p className="text-body-sm font-mono truncate">{evidence.provenance}</p>
          </div>
        )}

        {evidence.relatedArtifact && (
          <div className="mb-3">
            <p className="text-caption text-[var(--color-text-muted)] mb-1">Artifact</p>
            <p className="text-body-sm font-mono truncate">{evidence.relatedArtifact}</p>
          </div>
        )}

        <div className="flex flex-wrap gap-2">
          {evidence.claimId && (
            <span className="flex items-center gap-1 px-2 py-1 text-caption bg-[var(--color-surface)] rounded border border-[var(--color-surface-border)]">
              <Shield size={12} />
              {evidence.claimId.slice(0, 12)}...
            </span>
          )}
          {evidence.relatedTaskId && (
            <span className="flex items-center gap-1 px-2 py-1 text-caption bg-[var(--color-surface)] rounded border border-[var(--color-surface-border)]">
              <FileText size={12} />
              Task
            </span>
          )}
          {evidence.relatedRunId && (
            <span className="flex items-center gap-1 px-2 py-1 text-caption bg-[var(--color-surface)] rounded border border-[var(--color-surface-border)]">
              <Terminal size={12} />
              Run
            </span>
          )}
        </div>

        <details className="mt-3 pt-3 border-t border-[var(--color-surface-border)]">
          <summary className="flex items-center gap-2 text-caption text-[var(--color-text-muted)] cursor-pointer">
            <ChevronRight size={12} className="transition-transform" />
            Machine Result
          </summary>
          <pre className="mt-2 p-3 bg-[var(--color-surface)] rounded border border-[var(--color-surface-border)] overflow-x-auto text-code-sm">
            <code>{JSON.stringify(evidence.machineResult, null, 2)}</code>
          </pre>
        </details>
      </div>
    );
  }
);

EvidenceItem.displayName = 'EvidenceItem';