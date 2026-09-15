'use client';

import { useState, type ReactNode } from 'react';
import { useAppStore } from '@/store/appStore';
import { Section } from '@/components/shell/AppShell';
import { StateBadge, type TrustState } from '@/components/ui/StateBadge';
import { lucideReact } from '@/lib/lucide-imports';
import { cn } from '@/lib/design-tokens';

const { Shield, Database, FileText, CheckCircle2, CheckCircle, FlaskConical, Lock, ArrowRight } = lucideReact;

interface ReadinessStep {
  id: string;
  label: string;
  state: TrustState;
  met: boolean;
  icon: ReactNode;
}

/**
 * ConstitutionActivation - Screen 2: Activation & Ratification
 * Ratify the Behavioral Constitution to make protected claims binding
 */
export function ConstitutionActivation() {
  const { constitution, workflow, setConstitution, setWorkflowState, setActiveTab } = useAppStore();
  const [activated, setActivated] = useState(false);

  // Demo fixture data (deterministic; backend wiring is a later phase)
  const readinessSteps: ReadinessStep[] = [
    {
      id: 'evidence',
      label: 'Evidence repositories indexed',
      state: 'CERTIFIED',
      met: true,
      icon: <Database size={16} />,
    },
    {
      id: 'claims',
      label: '42 claims drafted',
      state: 'PROTECTED',
      met: true,
      icon: <FileText size={16} />,
    },
    {
      id: 'verified',
      label: '32 protected claims verified',
      state: 'PROTECTED',
      met: true,
      icon: <CheckCircle2 size={16} />,
    },
    {
      id: 'verify-plan',
      label: 'Independent verification plan ready',
      state: 'OBSERVED',
      met: true,
      icon: <FlaskConical size={16} />,
    },
    {
      id: 'human',
      label: 'Human approval required',
      state: activated ? 'CERTIFIED' : 'LOCKED',
      met: activated,
      icon: <Lock size={16} />,
    },
  ];

  const automatedSteps = readinessSteps.filter((s) => s.id !== 'human');
  const ready = automatedSteps.every((s) => s.met) && !activated;
  const metCount = readinessSteps.filter((s) => s.met).length;

  const summary = {
    title: constitution?.title ?? 'Behavioral Constitution v1.0',
    version: constitution?.version ?? 1,
    claimCount: constitution?.claimCount ?? 42,
    protectedCount: constitution?.protectedCount ?? 32,
  };
  const domains = [
    'Tenant Isolation',
    'Authentication Contract',
    'Session Compatibility',
    'Audit Trail',
    'Payment Idempotency',
  ];

  const handleActivate = () => {
    setConstitution({
      id: 'const-1',
      title: 'Behavioral Constitution v1.0',
      version: 1,
      status: 'ACTIVE',
      claimCount: 42,
      protectedCount: 32,
      locked: true,
    });
    setWorkflowState({
      currentStage: 'Govern',
      completedStages: ['Discover', 'Govern'],
      trustStatus: 'PROTECTED',
    });
    setActivated(true);
  };

  return (
    <div className="space-y-6">
      <Section
        title="Constitution Activation"
        description="Ratify the Behavioral Constitution to make protected claims binding"
      >
      {/* Readiness / Ratification Checklist */}
      <div className="surface-card p-4">
        <div className="flex items-center justify-between flex-wrap gap-4 mb-4">
          <div>
            <h3 className="text-subheading font-semibold">Ratification Readiness</h3>
            <p className="text-body-sm text-[var(--color-text-muted)]">
              {metCount} of {readinessSteps.length} readiness prerequisites met
            </p>
          </div>
          <div className="flex items-center gap-1">
            <div className="flex h-1.5 w-40 bg-[var(--color-surface-border)] rounded-full overflow-hidden">
              <div
                className={cn(
                  'h-full rounded-full transition-all duration-300',
                  activated ? 'bg-[var(--color-trust-certified)]' : 'bg-[var(--color-trust-protected)]',
                )}
                style={{ width: `${(metCount / readinessSteps.length) * 100}%` }}
              />
            </div>
            <span className="text-caption font-mono text-[var(--color-text-muted)]">
              {Math.round((metCount / readinessSteps.length) * 100)}%
            </span>
          </div>
        </div>
        <ul className="space-y-2">
          {readinessSteps.map((step) => (
            <li
              key={step.id}
              className={cn(
                'flex items-center gap-3 px-3 py-2.5 rounded-lg border transition-all',
                step.met
                  ? 'bg-[var(--color-surface)] border-[var(--color-surface-border)]'
                  : 'bg-[color-mix(in_srgb,_var(--color-trust-locked)_5%,_transparent)] border-[color-mix(in_srgb,_var(--color-trust-locked)_30%,_transparent)]',
              )}
            >
              <span className="flex-shrink-0 text-[var(--color-text-muted)]">{step.icon}</span>
              <span className="flex-1 text-body-sm font-medium">{step.label}</span>
              <StateBadge state={step.state} size="sm" variant="pill" />
            </li>
          ))}
        </ul>
      </div>

      {/* Constitution Summary */}
      <div className="surface-card p-4">
        <div className="flex items-start justify-between flex-wrap gap-4">
          <div className="flex items-center gap-4">
            <div className="flex items-center justify-center w-12 h-12 rounded-lg bg-[color-mix(in_srgb,_var(--color-trust-protected)_15%,_transparent)] text-[var(--color-trust-protected)]">
              <Shield size={24} />
            </div>
            <div>
              <h3 className="text-heading font-semibold">{summary.title}</h3>
              <p className="text-body-sm text-[var(--color-text-muted)]">
                Version v{summary.version} · {summary.claimCount} claims · {summary.protectedCount} protected behaviors
              </p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <StateBadge state={activated ? 'CERTIFIED' : 'PROTECTED'} size="sm" variant="pill" />
            <StateBadge state="LOCKED" size="sm" variant="pill" />
          </div>
        </div>
        <div className="mt-4">
          <p className="text-caption text-[var(--color-text-muted)] mb-2">Affected Behavior Domains</p>
          <div className="flex flex-wrap gap-2">
            {domains.map((domain) => (
              <span
                key={domain}
                className="px-2.5 py-1 text-caption font-medium bg-[var(--color-surface)] border border-[var(--color-surface-border)] rounded-lg"
              >
                {domain}
              </span>
            ))}
          </div>
        </div>
      </div>

      {/* Trust Semantics */}
      <div className="surface-card p-4">
        <h3 className="text-subheading font-semibold mb-2">Trust Semantics</h3>
        <p className="text-body-sm text-[var(--color-text-secondary)] leading-relaxed">
          Activating the constitution ratifies protected claims as binding and locks them as immutable governing
          context. The Behavioral Constitution becomes the <span className="font-medium text-[var(--color-trust-locked)]">LOCKED</span>{' '}
          active context and the overall workflow trust status moves to{' '}
          <span className="font-medium text-[var(--color-trust-protected)]">PROTECTED</span>.
        </p>
        <div className="flex flex-wrap items-center gap-3 mt-3">
          <div className="flex items-center gap-2">
            <span className="text-caption text-[var(--color-text-muted)]">Trust status before:</span>
            <StateBadge state={activated ? 'PROTECTED' : (workflow.trustStatus)} size="sm" variant="pill" />
          </div>
          <ArrowRight size={16} className="text-[var(--color-text-muted)]" />
          <div className="flex items-center gap-2">
            <span className="text-caption text-[var(--color-text-muted)]">After ratification:</span>
            <StateBadge state="PROTECTED" size="sm" variant="pill" />
          </div>
        </div>
      </div>

      {/* Approval Gate */}
      <div className="surface-card p-4">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div>
            <h3 className="text-subheading font-semibold">Human Approval Gate</h3>
            <p className="text-body-sm text-[var(--color-text-muted)]">
              A human must ratify the constitution before protected claims become binding.
            </p>
          </div>
          <button className="btn btn--primary" disabled={!ready} onClick={handleActivate}>
            <CheckCircle2 size={16} />
            Activate Constitution
          </button>
        </div>
        {!ready && !activated && (
          <p className="text-caption text-[var(--color-trust-locked)] mt-3">
            Complete all readiness prerequisites to enable ratification.
          </p>
        )}
      </div>

      {/* Success Panel */}
      {activated && (
        <div className="surface-card p-6 border border-[color-mix(in_srgb,_var(--color-trust-protected)_30%,_transparent)]">
          <div className="flex flex-col items-center text-center">
            <div className="flex items-center justify-center w-14 h-14 rounded-full bg-[color-mix(in_srgb,_var(--color-trust-protected)_15%,_transparent)] text-[var(--color-trust-protected)] mb-4">
              <CheckCircle size={28} />
            </div>
            <h3 className="text-heading font-semibold text-[var(--color-trust-protected)]">Constitution Ratified</h3>
            <p className="text-body text-[var(--color-text-secondary)] mt-2 max-w-lg">
              Behavioral Constitution v1.0 is now the LOCKED active governing context for Change #184. 32 protected
              behaviors are binding; workflow trust status is PROTECTED.
            </p>
            <div className="flex items-center gap-2 mt-4">
              <StateBadge state="LOCKED" size="md" variant="pill" />
              <StateBadge state="PROTECTED" size="md" variant="pill" />
            </div>
            <button className="btn btn--primary mt-6" onClick={() => setActiveTab('Define')}>
              Proceed to Define
              <ArrowRight size={16} />
            </button>
          </div>
        </div>
      )}
      </Section>
    </div>
  );
}