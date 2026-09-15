'use client';

import { useState } from 'react';
import { JourneyPage, Section, LoadingState } from '@/components/shell/AppShell';
import { useAppStore } from '@/store/appStore';
import { lucideReact } from '@/lib/lucide-imports';
import { stageColors } from '@/lib/design-tokens';
import type { Certificate, JourneyTab } from '@/types';

const {
  BadgeCheck,
  Shield,
  CheckCircle2,
  Hash,
  ChevronDown,
  Link,
  ArrowRight,
} = lucideReact;

const certStatusConfig: Record<Certificate['status'], { color: string; tint: string; border: string }> = {
  DRAFT:    { color: '#8A94A8', tint: '#EEF1F8', border: '#E3E8F2' },
  ISSUED:   { color: '#3D86F4', tint: '#EDF3FE', border: '#D9E6FC' },
  CERTIFIED: { color: '#14936B', tint: '#ECF8F4', border: '#D5EFE6' },
  REVOKED:  { color: '#D8493C', tint: '#FCEFEE', border: '#F5D5D3' },
};

const certifyPhases = [
  { id: 'bind', label: 'Binding evidence to certificate', color: '#DB5F9C' },
  { id: 'hash', label: 'Computing certificate hash', color: '#B33D78' },
  { id: 'seal', label: 'Sealing immutable record', color: '#14936B' },
];

function StatusPill({ label, color, tint, border }: { label: string; color: string; tint: string; border: string }) {
  return (
    <span className="pill border font-medium" style={{ background: tint, color, borderColor: border }}>
      {label}
    </span>
  );
}

function truncateMiddle(value: string, keep = 10): string {
  if (value.length <= keep * 2 + 3) return value;
  return `${value.slice(0, keep)}…${value.slice(-keep)}`;
}

function BoundField({ label, value, mono = false }: { label: string; value: string; mono?: boolean }) {
  return (
     <div className="p-2.5 rounded-xl">
      <p className="text-caption text-[var(--color-text-muted)] mb-0.5">{label}</p>
      <p className={mono ? 'text-body-sm font-mono text-[var(--color-text-primary)]' : 'text-body-sm text-[var(--color-text-primary)]'}>{value}</p>
    </div>
  );
}

export default function CertifyTab() {
  const domain = useAppStore((s) => s.domain);
  const change = useAppStore((s) => s.change);
  const updateDomain = useAppStore((s) => s.updateDomain);
  const completeStage = useAppStore((s) => s.completeStage);
  const setActiveTab = useAppStore((s) => s.setActiveTab);
  const setWorkflowState = useAppStore((s) => s.setWorkflowState);
  const openDrawer = useAppStore((s) => s.openDrawer);
  const [phaseIndex, setPhaseIndex] = useState(0);
  const [isRunning, setIsRunning] = useState(false);

  if (!domain.certificate) return <LoadingState message="Loading certificate context…" />;

  const colors = stageColors.Certify;
  const certificate = domain.certificate;
  const certified = certificate.status === 'CERTIFIED';
  const changeId = change?.externalId ?? '#184';

  const environmentLabel = Object.entries(certificate.environment)
    .map(([key, value]) => `${key}: ${String(value)}`)
    .join(' · ');
  const dependencyLabel = Object.entries(certificate.dependencyState)
    .map(([key, value]) => `${key} → ${String(value)}`)
    .join(' · ');

  const finish = (stage: JourneyTab) => {
    completeStage(stage);
    setActiveTab(stage);
  };

  const handleIssue = async () => {
    if (isRunning || certified || !certificate) return;
    setIsRunning(true);
    setPhaseIndex(0);
    for (let i = 0; i < certifyPhases.length; i++) {
      setPhaseIndex(i);
      await new Promise((resolve) => setTimeout(resolve, 700));
    }
    updateDomain({ certificate: { ...certificate, status: 'CERTIFIED' as const } });
    setWorkflowState({ currentStage: 'Certify', trustStatus: 'CERTIFIED' });
    setIsRunning(false);
    finish('Certify');
  };

  return (
    <JourneyPage
      title="Certify"
      description="Bind evidence to the certificate, seal the immutable trust record, and close the behavioral memory loop."
    >
      <div className="space-y-5">
        {/* Lead Card */}
        <div className="rounded-2xl border bg-white overflow-hidden shadow-sm" style={{ borderColor: colors.border }}>
          <div className="h-1 w-full" style={{ background: colors.tint }} />
          <div className="px-6 py-6 space-y-5">
            <div className="flex flex-wrap items-start justify-between gap-4">
              <div className="flex items-center gap-3">
                <div
                  className="flex items-center justify-center w-12 h-12 rounded-2xl flex-shrink-0"
                  style={{ background: colors.tint, color: colors.active }}
                >
                  <BadgeCheck size={22} strokeWidth={2} />
                </div>
                <div>
                  <h2 className="text-heading font-bold text-[var(--color-text-primary)]">Certificate {certificate.certificateId}</h2>
                  <div className="flex flex-wrap items-center gap-2 mt-1.5">
                    <StatusPill {...certStatusConfig[certificate.status]} label={certificate.status} />
                    <span className="pill border font-medium" style={{ background: colors.tint, color: colors.strong, borderColor: colors.border }}>
                      Change {changeId}
                    </span>
                    <button
                      onClick={() => openDrawer('certificate', { ...certificate })}
                      type="button"
                      className="btn btn--secondary btn-sm"
                    >
                      View Certificate
                    </button>
                  </div>
                </div>
              </div>
              <div className="text-right space-y-1.5">
                <div>
                  <p className="text-caption text-[var(--color-text-muted)]">Commit</p>
                  <p className="text-code-sm font-mono text-[var(--color-text-primary)]">{certificate.commit}</p>
                </div>
                <div>
                  <p className="text-caption text-[var(--color-text-muted)]">Certificate Hash</p>
                  <p className="text-code-sm font-mono text-[var(--color-text-primary)]" title={certificate.certificateHash}>
                    {truncateMiddle(certificate.certificateHash)}
                  </p>
                </div>
                <div>
                  <p className="text-caption text-[var(--color-text-muted)]">Issued</p>
                  <p className="text-code-sm font-mono text-[var(--color-text-primary)]">
                    {new Date(certificate.issuedAt).toLocaleString()}
                  </p>
                </div>
              </div>
            </div>
            <p className="text-body-sm text-[var(--color-text-secondary)] leading-relaxed max-w-3xl">
              {certified
                ? 'This certificate is sealed: the immutable trust record binds change #184 to its evidence, and the behavioral memory loop is closed.'
                : 'This certificate is issued and ready. Seal it to bind the evidence traversal, protected behaviors, and bound artifacts into the immutable trust record.'}
            </p>
          </div>
        </div>

        {/* Evidence Traversal */}
        <Section
          title="Evidence Traversal"
          description="The certificate binds to a provable chain from intent through evidence to the code and environment."
        >
          <div className="surface-card p-5">
            <div className="flex flex-col">
              <div className="flex items-center gap-2.5">
                <span
                  className="flex items-center justify-center w-5 h-5 rounded-full text-[0.6rem] font-bold flex-shrink-0"
                  style={{ background: colors.tint, color: colors.strong }}
                >
                  1
                </span>
                <span className="text-code-sm font-mono text-[var(--color-text-secondary)]">
                  Certificate → Claim → Behavioral Delta → Experiment → Execution Trace → Code/Environment
                </span>
              </div>
              {certificate.evidenceTraversal.map((step, i) => (
                <div key={`${step}-${i}`}>
                  <ChevronDown size={14} className="ml-[7px] my-0.5 text-[var(--color-text-muted)]" />
                  <div className="flex items-center gap-2.5">
                    <span
                      className="flex items-center justify-center w-5 h-5 rounded-full text-[0.6rem] font-bold flex-shrink-0"
                      style={{ background: colors.tint, color: colors.strong }}
                    >
                      {i + 2}
                    </span>
                    <Hash size={11} className="text-[var(--color-text-muted)]" />
                    <span className="text-code-sm font-mono text-[var(--color-text-primary)]">{step}</span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </Section>

        {/* Bound Artifacts */}
        <Section
          title="Bound Artifacts"
          description="The certificate seals the exact artifacts the decision and evidence proved."
        >
          <div className="surface-card p-5">
            <dl className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <BoundField label="Intent Ledger" value={certificate.intentLedgerId} mono />
              <BoundField label="Behavioral Delta" value={certificate.behavioralDeltaId} mono />
              <BoundField label="Candidate Patch" value={certificate.candidatePatchId} mono />
              <BoundField label="Change" value={`${changeId} · ${certificate.changeId}`} mono />
            </dl>
            <div className="mt-4 pt-4 border-t border-[var(--color-surface-border)]">
              <p className="text-caption text-[var(--color-text-muted)] mb-2">Verification Evidence Bound</p>
              <div className="flex flex-wrap gap-2">
                {certificate.verificationEvidenceIds.map((id) => (
                  <span key={id} className="pill border font-medium" style={{ background: '#EDF3FE', color: '#3D86F4', borderColor: '#D9E6FC' }}>
                    {id}
                  </span>
                ))}
              </div>
            </div>
            <div className="mt-4 pt-4 border-t border-[var(--color-surface-border)] grid grid-cols-1 sm:grid-cols-2 gap-4">
              <BoundField label="Environment" value={environmentLabel} mono />
              <BoundField label="Dependency State" value={dependencyLabel} mono />
            </div>
          </div>
        </Section>

        {/* Protected Behaviors Sealed */}
        <Section
          title="Protected Behaviors Sealed"
          description="Every protected behavior bound to this certificate is sealed into the trust record."
        >
          <div className="surface-card p-5">
            <div className="flex flex-wrap gap-2">
              {certificate.protectedBehaviors.map((behavior) => (
                <span
                  key={behavior}
                  className="pill border font-medium"
                  style={{ background: '#FCEEF5', color: '#DB5F9C', borderColor: '#F5D9E6' }}
                >
                  <Shield size={12} strokeWidth={2} /> {behavior}
                </span>
              ))}
            </div>
          </div>
        </Section>

        {/* Primary Action */}
        <div className="surface-card p-5">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div>
              <h2 className="text-heading text-[var(--color-text-primary)]">Issue &amp; Seal Certificate</h2>
              <p className="text-body-sm text-[var(--color-text-secondary)] mt-1 max-w-2xl">
                Bind the evidence traversal, compute the certificate hash, and seal the immutable record.
              </p>
            </div>
            {certified && (
              <span className="pill border font-medium" style={{ background: '#ECF8F4', color: '#14936B', borderColor: '#D5EFE6' }}>
                Change #184 is evidence-bound
              </span>
            )}
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-2 mt-4">
            {certifyPhases.map((phase, i) => {
              const active = isRunning && phaseIndex === i;
              const done = isRunning ? phaseIndex > i : certified;
              return (
                <div
                  key={phase.id}
                   className="flex items-center gap-3 p-2.5 rounded-xl border transition-all"
                  style={
                    active
                      ? { background: phase.color + '10', borderColor: phase.color + '55' }
                      : done
                      ? { background: '#EBF9F4', borderColor: '#D4F1E7' }
                      : { background: '#F5F7FB', borderColor: '#E3E8F2' }
                  }
                >
                  <div
                    className="flex items-center justify-center w-8 h-8 rounded-lg flex-shrink-0"
                    style={active ? { background: phase.color, color: 'white' } : done ? { background: '#0E9F6E', color: 'white' } : { background: phase.color + '15', color: phase.color }}
                  >
                    {active ? (
                      <div className="w-3.5 h-3.5 border-2 border-white border-t-transparent rounded-full animate-spin" />
                    ) : done ? (
                      <CheckCircle2 size={14} strokeWidth={2} />
                    ) : (
                      <Link size={14} strokeWidth={2} />
                    )}
                  </div>
                  <span className="text-[0.8rem] font-semibold text-[var(--color-text-primary)]">{phase.label}</span>
                  <span className="text-[0.65rem] font-mono ml-auto">
                    {active ? 'Running…' : done ? 'Done' : 'Pending'}
                  </span>
                </div>
              );
            })}
          </div>

          {isRunning && (
            <div className="mt-4">
              <div className="flex items-center justify-between text-[0.7rem] font-medium mb-1.5">
                <span className="text-[var(--color-text-secondary)]">Progress</span>
                <span className="font-mono" style={{ color: '#DB5F9C' }}>
                  {Math.round(((phaseIndex + 1) / certifyPhases.length) * 100)}%
                </span>
              </div>
              <div className="h-2 rounded-full overflow-hidden" style={{ background: '#F5D9E6' }}>
                <div
                  className="h-full rounded-full transition-all duration-300"
                  style={{ background: '#DB5F9C', width: `${((phaseIndex + 1) / certifyPhases.length) * 100}%` }}
                />
              </div>
            </div>
          )}

          {!isRunning && !certified && (
            <button onClick={handleIssue} type="button" className="btn btn--primary w-full mt-4" style={{ padding: '0.875rem 1.5rem' }}>
              <BadgeCheck size={18} strokeWidth={2} /> Issue &amp; Seal Certificate
            </button>
          )}

          {certified && (
            <div className="mt-4 p-4 rounded-xl" style={{ background: '#ECF8F4', border: '1px solid #D5EFE6' }}>
              <div className="flex flex-wrap items-center justify-between gap-3">
                <div className="flex items-center gap-3">
                  <div className="flex items-center justify-center w-9 h-9 rounded-xl" style={{ background: '#14936B', color: 'white' }}>
                    <CheckCircle2 size={18} strokeWidth={2} />
                  </div>
                  <div>
                    <p className="text-[0.8rem] font-bold" style={{ color: '#14936B' }}>Certificate sealed — Change {changeId} is evidence-bound</p>
                    <p className="text-[0.7rem]" style={{ color: '#14936B' }}>Immutable trust record bound; behavioral memory loop is ready to close</p>
                  </div>
                </div>
                <div className="flex flex-wrap gap-2">
                  <button onClick={() => openDrawer('certificate', { ...certificate })} type="button" className="btn btn--secondary btn-sm">
                    View Evidence Traversal
                  </button>
                  <button onClick={() => setActiveTab('Discover')} type="button" className="btn btn--primary btn-sm">
                    Merge &amp; Close Behavioral Memory <ArrowRight size={16} strokeWidth={2} />
                  </button>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </JourneyPage>
  );
}