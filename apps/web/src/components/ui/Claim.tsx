'use client';

import { forwardRef, type HTMLAttributes } from 'react';
import { cn } from '@/lib/design-tokens';
import { StateBadge, type TrustState } from './StateBadge';
import { lucideReact } from '@/lib/lucide-imports';

const { ChevronRight, FileText, GitBranch, FlaskConical, Clock } = lucideReact;

/**
 * Claim - Displays a constitutional/governance claim with authority, confidence, and evidence
 */
export interface ClaimProps extends Omit<HTMLAttributes<HTMLDivElement>, 'onSelect'> {
  claim: ClaimData;
  variant?: 'card' | 'compact' | 'list';
  onSelect?: (claim: ClaimData) => void;
  selected?: boolean;
}

export interface ClaimData {
  id: string;
  claimId: string;
  statement: string;
  authority: string;
  confidence: number;
  status: TrustState;
  locked: boolean;
  createdAt: string;
  evidenceIds: string[];
  affectedSoftware?: string[];
  governanceConsequence?: string;
  verificationRequirements?: string[];
}

export const Claim = forwardRef<HTMLDivElement, ClaimProps>(
  ({ claim, variant = 'card', onSelect, selected, className, ...props }, ref) => {
    const handleClick = () => onSelect?.(claim);

    const confidencePercent = Math.round(claim.confidence * 100);
    const isHighConfidence = claim.confidence >= 0.8;
    const isMediumConfidence = claim.confidence >= 0.5;

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
          <StateBadge state={claim.status} size="sm" />
          <div className="flex-1 min-w-0">
            <p className="text-body font-medium truncate">{claim.statement}</p>
            <div className="flex items-center gap-3 text-caption text-[var(--color-text-muted)]">
              <span className={cn('font-mono', isHighConfidence ? 'text-[var(--color-trust-certified)]' : isMediumConfidence ? 'text-[var(--color-trust-unverified)]' : 'text-[var(--color-trust-violated)]')}>
                {confidencePercent}% confidence
              </span>
              <span className="font-mono">{claim.authority}</span>
              {claim.locked && <span className="text-[var(--color-trust-locked)]">LOCKED</span>}
            </div>
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
          <div className="flex items-start gap-3">
            <StateBadge state={claim.status} size="sm" />
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-2">
                <span className="font-mono text-caption text-[var(--color-text-muted)]">{claim.claimId}</span>
                {claim.locked && <span className="text-[var(--color-trust-locked)] text-caption">LOCKED</span>}
              </div>
              <p className="text-body mt-1">{claim.statement}</p>
              <div className="flex items-center gap-4 mt-2 text-caption text-[var(--color-text-muted)]">
                <span className="flex items-center gap-1">
                  <FileText size={12} />
                  {claim.evidenceIds.length} evidence
                </span>
                <span className="flex items-center gap-1">
                  <Clock size={12} />
                  {new Date(claim.createdAt).toLocaleDateString()}
                </span>
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
          <div className="flex items-center gap-2 flex-wrap">
            <StateBadge state={claim.status} size="md" />
            <span className="font-mono text-caption text-[var(--color-text-muted)]">{claim.claimId}</span>
            {claim.locked && <span className="text-[var(--color-trust-locked)] text-caption font-medium">LOCKED</span>}
          </div>
        </div>

        <p className="text-body mb-4 leading-relaxed">{claim.statement}</p>

        <div className="grid grid-cols-2 gap-4 mb-4">
          <div>
            <p className="text-caption text-[var(--color-text-muted)] mb-1">Authority</p>
            <p className="text-body font-mono font-medium">{claim.authority}</p>
          </div>
          <div>
            <p className="text-caption text-[var(--color-text-muted)] mb-1">Confidence</p>
            <div className="flex items-center gap-2">
              <div className="flex-1 h-1.5 bg-[var(--color-surface-border)] rounded-full overflow-hidden">
                <div
                  className={cn(
                    'h-full rounded-full transition-all duration-300',
                    isHighConfidence ? 'bg-[var(--color-trust-certified)]' :
                    isMediumConfidence ? 'bg-[var(--color-trust-unverified)]' :
                    'bg-[var(--color-trust-violated)]'
                  )}
                  style={{ width: `${confidencePercent}%` }}
                />
              </div>
              <span className={cn('text-caption font-mono font-medium',
                isHighConfidence ? 'text-[var(--color-trust-certified)]' :
                isMediumConfidence ? 'text-[var(--color-trust-unverified)]' :
                'text-[var(--color-trust-violated)]'
              )}>
                {confidencePercent}%
              </span>
            </div>
          </div>
        </div>

        <div className="flex flex-wrap gap-2 mb-3">
          {claim.evidenceIds.length > 0 && (
            <span className="flex items-center gap-1 px-2 py-1 text-caption bg-[var(--color-surface)] rounded border border-[var(--color-surface-border)]">
              <FileText size={12} />
              {claim.evidenceIds.length} evidence
            </span>
          )}
          {claim.affectedSoftware && claim.affectedSoftware.length > 0 && (
            <span className="flex items-center gap-1 px-2 py-1 text-caption bg-[var(--color-surface)] rounded border border-[var(--color-surface-border)]">
              <GitBranch size={12} />
              {claim.affectedSoftware.length} components
            </span>
          )}
        </div>

        {claim.governanceConsequence && (
          <div className="pt-3 border-t border-[var(--color-surface-border)]">
            <p className="text-caption text-[var(--color-text-muted)] mb-1">Governance Consequence</p>
            <p className="text-body-sm">{claim.governanceConsequence}</p>
          </div>
        )}

        {claim.verificationRequirements && claim.verificationRequirements.length > 0 && (
          <div className="pt-3 border-t border-[var(--color-surface-border)]">
            <p className="text-caption text-[var(--color-text-muted)] mb-1">Verification Requirements</p>
            <ul className="space-y-1">
              {claim.verificationRequirements.map((req, i) => (
                <li key={i} className="text-body-sm flex items-center gap-2">
                  <FlaskConical size={12} className="text-[var(--color-text-muted)]" />
                  {req}
                </li>
              ))}
            </ul>
          </div>
        )}
      </div>
    );
  }
);

Claim.displayName = 'Claim';