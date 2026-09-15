'use client';

import { useState } from 'react';
import { JourneyPage, Section, LoadingState } from '@/components/shell/AppShell';
import { useAppStore } from '@/store/appStore';
import { lucideReact } from '@/lib/lucide-imports';
import { stageColors } from '@/lib/design-tokens';
import type { DecisionEntry, DecisionSummary, JourneyTab } from '@/types';

const {
  Gavel,
  Shield,
  CheckCircle2,
  AlertTriangle,
  Wrench,
  FlaskConical,
  ChevronDown,
  ChevronRight,
  Hash,
} = lucideReact;

const classConfig: Record<DecisionEntry['classification'], { color: string; tint: string; border: string }> = {
  UNCHANGED:   { color: '#8A94A8', tint: '#EEF1F8', border: '#E3E8F2' },
  ALTERED:     { color: '#3D86F4', tint: '#EDF3FE', border: '#D9E6FC' },
  ADDED:       { color: '#1EAF8C', tint: '#EBF9F4', border: '#D4F1E7' },
  REMOVED:     { color: '#D8493C', tint: '#FCEFEE', border: '#F5D5D3' },
  UNEXPLAINED: { color: '#E98C4E', tint: '#FDF1EA', border: '#F8DECF' },
};

const alignConfig: Record<DecisionEntry['alignment'], { color: string; tint: string; border: string }> = {
  ALIGNED:    { color: '#0E9F6E', tint: '#EBF9F4', border: '#D4F1E7' },
  PENDING:    { color: '#C08A17', tint: '#FBF6E8', border: '#F2E7CC' },
  MISALIGNED: { color: '#D8493C', tint: '#FCEFEE', border: '#F5D5D3' },
};

const decisionStatusConfig: Record<DecisionSummary['status'], { color: string; tint: string; border: string }> = {
  REVIEWING:        { color: '#C08A17', tint: '#FBF6E8', border: '#F2E7CC' },
  DECIDED:          { color: '#14936B', tint: '#ECF8F4', border: '#D5EFE6' },
  REPAIR_REQUIRED:  { color: '#D8493C', tint: '#FCEFEE', border: '#F5D5D3' },
};

const decidePhases = [
  { id: 'eval', label: 'Evaluating behavioral deltas', color: '#E98C4E' },
  { id: 'align', label: 'Verifying intent alignment', color: '#0E9F6E' },
  { id: 'authorize', label: 'Authorizing change', color: 'var(--color-ink)' },
];

function StatusPill({ label, color, tint, border }: { label: string; color: string; tint: string; border: string }) {
  return (
    <span className="pill border font-medium" style={{ background: tint, color, borderColor: border }}>
      {label}
    </span>
  );
}

function DeltaCard({ entry }: { entry: DecisionEntry }) {
  const cls = classConfig[entry.classification];
  const aln = alignConfig[entry.alignment];
  return (
    <div className="surface-card p-5">
      <div className="flex flex-wrap items-center gap-2">
        <StatusPill {...cls} label={entry.classification} />
        <span className="text-code-sm font-mono text-[var(--color-text-muted)]">{entry.deltaId}</span>
        <span className="flex-1" />
        <span
          className="text-code-sm font-mono px-2 py-0.5 rounded-md"
          style={{ background: '#EDF3FE', color: '#3D86F4', border: '1px solid #D9E6FC' }}
        >
          {entry.claimId}
        </span>
      </div>
      <h3 className="text-subheading text-[var(--color-text-primary)] mt-3">{entry.claimLabel}</h3>
      <div className="flex flex-wrap items-center gap-3 mt-3">
        <span className="text-code-sm font-mono font-semibold" style={{ color: '#E98C4E' }}>
          Δ {entry.magnitude.toFixed(2)}
        </span>
        <span className="text-[0.7rem] text-[var(--color-text-muted)]">{entry.magnitude === 0 ? 'no behavioral shift' : 'behavioral shift'}</span>
        <span className="flex-1" />
        <StatusPill {...aln} label={entry.alignment} />
      </div>
      <p className="text-body-sm text-[var(--color-text-secondary)] mt-3 leading-relaxed">{entry.reasoning}</p>
      <div className="flex flex-wrap items-center gap-1.5 mt-3 pt-3 border-t border-[var(--color-surface-border)]">
        <Hash size={12} className="text-[var(--color-text-muted)]" />
        {entry.evidenceIds.map((id) => (
          <span key={id} className="pill border font-medium" style={{ background: '#EDF3FE', color: '#3D86F4', borderColor: '#D9E6FC' }}>
            {id}
          </span>
        ))}
      </div>
    </div>
  );
}

export default function DecideTab() {
  const domain = useAppStore((s) => s.domain);
  const change = useAppStore((s) => s.change);
  const updateDomain = useAppStore((s) => s.updateDomain);
  const completeStage = useAppStore((s) => s.completeStage);
  const setActiveTab = useAppStore((s) => s.setActiveTab);
  const setWorkflowState = useAppStore((s) => s.setWorkflowState);
  const [phaseIndex, setPhaseIndex] = useState(0);
  const [isRunning, setIsRunning] = useState(false);

  if (!domain.decision || !domain.certificate) return <LoadingState message="Loading decision context…" />;

  const colors = stageColors.Decide;
  const decision = domain.decision;
  const certificate = domain.certificate;
  const decided = decision.status === 'DECIDED';
  const changeId = change?.externalId ?? '#184';

  const protectedEntries = decision.entries.filter((e) =>
    certificate.protectedBehaviors.some((p) => p.startsWith(e.claimId)),
  );
  const protectedAligned = protectedEntries.filter((e) => e.alignment === 'ALIGNED').length;
  const unauthorizedChanges = decision.entries.filter((e) => e.alignment !== 'ALIGNED').length;
  const repairsCompleted = domain.candidatePatches.reduce((sum, p) => sum + p.failureHistory.length, 0);

  const repairPatch = domain.candidatePatches.find((p) => p.failureHistory.some((f) => f.id === 'F-183'));
  const failure = repairPatch?.failureHistory.find((f) => f.id === 'F-183');
  const affectedClaim = failure?.notes.match(/\bAUTH-\d{3}\b/)?.[0] ?? 'AUTH-023';
  const reVerification = domain.verificationRuns.find((r) => r.id === 'VER-184-R2');
  const vc06 = reVerification?.cases.find((c) => c.id === 'VC-06');
  const baseline = repairPatch?.execution.find((e) => e.command?.includes('npm test'))?.stdout ?? '';
  const mutationSummary =
    vc06 && vc06.result
      ? `${vc06.result.passed}/${vc06.result.passed + vc06.result.failed} mutants killed, ${vc06.result.failed === 0 ? '0 survivors' : `${vc06.result.failed} survivors`}`
      : '7/7 mutants killed, 0 survivors';

  const repairCriteria = [
    'tampered-expiration mutant killed',
    '42+ baseline tests pass',
    'no behavior outside auth/session.ts altered',
  ];

  const finish = (stage: JourneyTab) => {
    completeStage(stage);
    setActiveTab(stage);
  };

  const handleAuthorize = async () => {
    if (isRunning || decided || !decision) return;
    setIsRunning(true);
    setPhaseIndex(0);
    for (let i = 0; i < decidePhases.length; i++) {
      setPhaseIndex(i);
      await new Promise((resolve) => setTimeout(resolve, 700));
    }
    updateDomain({ decision: { ...decision, status: 'DECIDED' as const } });
    setWorkflowState({ currentStage: 'Decide', trustStatus: 'PROTECTED' });
    setIsRunning(false);
    finish('Decide');
  };

  return (
    <JourneyPage
      title="Decide"
      description="Are the observed behavioral changes authorized? Evaluate deltas, verify intent alignment, and drive the repair loop when required."
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
                  <Gavel size={22} strokeWidth={2} />
                </div>
                <div>
                  <h2 className="text-heading font-bold text-[var(--color-text-primary)]">Authorization Review — {decision.id}</h2>
                  <div className="flex flex-wrap items-center gap-2 mt-1.5">
                    <StatusPill
                      {...decisionStatusConfig[decision.status]}
                      label={decision.status === 'REPAIR_REQUIRED' ? 'REPAIR REQUIRED' : decision.status}
                    />
                    <span className="pill border font-medium" style={{ background: colors.tint, color: colors.strong, borderColor: colors.border }}>
                      Change {changeId}
                    </span>
                    <span className="pill border font-medium" style={{ background: colors.tint, color: colors.strong, borderColor: colors.border }}>
                      {change?.title}
                    </span>
                  </div>
                </div>
              </div>
              <div className="text-right space-y-1">
                <div>
                  <p className="text-caption text-[var(--color-text-muted)]">Decision</p>
                  <p className="text-code-sm font-mono text-[var(--color-text-primary)]">{decision.id}</p>
                </div>
                <div>
                  <p className="text-caption text-[var(--color-text-muted)]">Behavioral Deltas</p>
                  <p className="text-code-sm font-mono text-[var(--color-text-primary)]">{decision.entries.length} observed</p>
                </div>
              </div>
            </div>
            <p className="text-body-sm text-[var(--color-text-secondary)] leading-relaxed max-w-3xl">{decision.summary}</p>
          </div>
        </div>

        {/* Behavioral Delta Review */}
        <Section
          title="Behavioral Delta Review"
          description="Every observable behavioral delta is classified and measured against the protected constitution."
        >
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
            {decision.entries.map((entry) => (
              <DeltaCard key={entry.deltaId} entry={entry} />
            ))}
          </div>
        </Section>

        {/* Failure → Repair + Intent Alignment Summary */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-5">
          <div className="lg:col-span-2 space-y-5">
            <Section
              title="Failure → Repair"
              description="Failure archaeology preserves the failed candidate and the evidence-driven repair that closed it."
            >
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {/* Failure */}
                <div className="surface-card p-5">
                  <div className="flex items-center gap-3">
                    <div className="flex items-center justify-center w-9 h-9 rounded-xl" style={{ background: '#FCEFEE', color: '#D8493C' }}>
                      <AlertTriangle size={16} strokeWidth={2} />
                    </div>
                    <div className="flex-1">
                      <h3 className="text-subheading text-[var(--color-text-primary)]">Failure {failure?.id ?? 'F-183'}</h3>
                      <p className="text-caption text-[var(--color-text-muted)]">Run {failure?.runId ?? 'VER-184-R1'}</p>
                    </div>
                  </div>
                  <div className="flex flex-wrap items-center gap-2 mt-3">
                    <StatusPill {...{ color: '#D8493C', tint: '#FCEFEE', border: '#F5D5D3' }} label={(failure?.classification ?? 'acceptance-criterion failure').replace(/\b\w/g, (c) => c.toUpperCase())} />
                    {failure?.evidenceId && (
                      <span className="pill border font-medium" style={{ background: '#EDF3FE', color: '#3D86F4', borderColor: '#D9E6FC' }}>
                        {failure.evidenceId}
                      </span>
                    )}
                  </div>
                  <p className="text-body-sm text-[var(--color-text-secondary)] mt-3 leading-relaxed">{failure?.notes}</p>
                </div>

                {/* Repair Package */}
                <div className="surface-card p-5">
                  <div className="flex items-center gap-3">
                    <div className="flex items-center justify-center w-9 h-9 rounded-xl" style={{ background: '#EBF9F4', color: '#0E9F6E' }}>
                      <Wrench size={16} strokeWidth={2} />
                    </div>
                    <div className="flex-1">
                      <h3 className="text-subheading text-[var(--color-text-primary)]">Repair Package</h3>
                      <p className="text-caption text-[var(--color-text-muted)] font-mono">{repairPatch?.id ?? 'PATCH-184-2'}</p>
                    </div>
                    <StatusPill {...{ color: '#14936B', tint: '#ECF8F4', border: '#D5EFE6' }} label="COMPLETED" />
                  </div>
                  <div className="grid grid-cols-2 gap-3 mt-3">
                    <div className="p-3 rounded-xl">
                      <p className="text-caption text-[var(--color-text-muted)] mb-0.5">Affected Claim</p>
                      <p className="text-code-sm font-mono text-[var(--color-text-primary)]">{affectedClaim}</p>
                    </div>
                    <div className="p-3 rounded-xl">
                      <p className="text-caption text-[var(--color-text-muted)] mb-0.5">Change Scope</p>
                      <p className="text-code-sm font-mono text-[var(--color-text-primary)] truncate">
                        {repairPatch?.filesChanged.join(', ') ?? 'auth/session.ts'}
                      </p>
                    </div>
                  </div>
                  <p className="text-body-sm text-[var(--color-text-secondary)] mt-3 leading-relaxed">
                    Required outcome: close the session-expiration mutation gap (F-183) so {affectedClaim} is provable before certification.
                  </p>
                  <div className="space-y-1.5 mt-3">
                    {repairCriteria.map((criterion) => (
                      <div key={criterion} className="flex items-center gap-2">
                        <CheckCircle2 size={14} strokeWidth={2} className="flex-shrink-0" style={{ color: '#0E9F6E' }} />
                        <span className="text-body-sm text-[var(--color-text-secondary)]">{criterion}</span>
                      </div>
                    ))}
                  </div>
                </div>
              </div>

              {/* Re-verification */}
              <div className="surface-card p-5 mt-4">
                <div className="flex flex-wrap items-center gap-3">
                  <div className="flex items-center justify-center w-9 h-9 rounded-xl" style={{ background: '#EDF3FE', color: '#3D86F4' }}>
                    <FlaskConical size={16} strokeWidth={2} />
                  </div>
                  <div className="flex-1">
                    <h3 className="text-subheading text-[var(--color-text-primary)]">Re-verification</h3>
                    <p className="text-caption text-[var(--color-text-muted)] font-mono">{reVerification?.id ?? 'VER-184-R2'} · {reVerification?.label}</p>
                  </div>
                  <StatusPill {...{ color: '#14936B', tint: '#ECF8F4', border: '#D5EFE6' }} label="PASSED" />
                </div>
                <div className="flex flex-wrap items-center gap-3 mt-3">
                  <span className="pill border font-medium" style={{ background: '#EEF1F8', color: '#8A94A8', borderColor: '#E3E8F2' }}>
                    {vc06?.id ?? 'VC-06'}
                  </span>
                  <span className="text-code-sm font-mono font-semibold" style={{ color: '#0E9F6E' }}>{mutationSummary}</span>
                  {(vc06?.evidenceIds ?? ['EV-406']).map((id) => (
                    <span key={id} className="pill border font-medium" style={{ background: '#EDF3FE', color: '#3D86F4', borderColor: '#D9E6FC' }}>
                      {id}
                    </span>
                  ))}
                  {baseline && (
                    <span className="text-caption text-[var(--color-text-muted)]">Baseline: {baseline}</span>
                  )}
                </div>
              </div>
            </Section>
          </div>

          {/* Intent Alignment Summary */}
          <div className="space-y-5">
            <Section
              title="Intent Alignment Summary"
              description="Do the observed deltas match what the change was authorized to do?"
            >
              <div className="surface-card p-5">
                <div className="grid grid-cols-2 gap-3">
                  <div className="rounded-xl border p-4" style={{ borderColor: '#D4F1E7', background: '#EBF9F4' }}>
                    <p className="text-[0.65rem] font-semibold uppercase tracking-wider" style={{ color: '#0E9F6E' }}>
                      Protected Claims Aligned
                    </p>
                    <p className="text-[1.4rem] font-semibold mt-1 font-mono" style={{ color: '#0E9F6E' }}>
                      {protectedAligned}/{protectedEntries.length}
                    </p>
                  </div>
                  <div className="rounded-xl border p-4" style={{ borderColor: unauthorizedChanges > 0 ? '#F5D5D3' : '#E3E8F2', background: unauthorizedChanges > 0 ? '#FCEFEE' : '#F5F7FB' }}>
                    <p className="text-[0.65rem] font-semibold uppercase tracking-wider" style={{ color: unauthorizedChanges > 0 ? '#D8493C' : '#8A94A8' }}>
                      Unauthorized Changes
                    </p>
                    <p className="text-[1.4rem] font-semibold mt-1 font-mono" style={{ color: unauthorizedChanges > 0 ? '#D8493C' : '#8A94A8' }}>
                      {unauthorizedChanges}
                    </p>
                  </div>
                  <div className="rounded-xl border p-4" style={{ borderColor: '#D5EFE6', background: '#ECF8F4' }}>
                    <p className="text-[0.65rem] font-semibold uppercase tracking-wider" style={{ color: '#14936B' }}>
                      Repairs Completed
                    </p>
                    <p className="text-[1.4rem] font-semibold mt-1 font-mono" style={{ color: '#14936B' }}>
                      {repairsCompleted}
                    </p>
                  </div>
                  <div className="rounded-xl border p-4" style={{ borderColor: '#F2E7CC', background: '#FBF6E8' }}>
                    <p className="text-[0.65rem] font-semibold uppercase tracking-wider" style={{ color: '#C08A17' }}>
                      Trust State
                    </p>
                    <p className="text-[1rem] font-semibold mt-1" style={{ color: '#C08A17' }}>
                      Certified-ready
                    </p>
                  </div>
                </div>

                <div className="mt-4 pt-4 border-t border-[var(--color-surface-border)]">
                  <p className="text-caption text-[var(--color-text-muted)] mb-2">Authorization Chain</p>
                  <div className="flex flex-col gap-1">
                    {[
                      { label: 'Behavioral Delta', note: `${decision.entries.length} deltas observed`, color: '#E98C4E', tint: '#FDF1EA', border: '#F8DECF' },
                      { label: 'Intent Aligned', note: `${protectedAligned}/${protectedEntries.length} protected claims`, color: '#0E9F6E', tint: '#EBF9F4', border: '#D4F1E7' },
                      { label: 'Authorized', note: 'Change #184 ready to certify', color: 'var(--color-ink)', tint: 'var(--color-ink-tint)', border: 'var(--color-ink-soft)' },
                    ].map((step, i) => (
                      <div key={step.label}>
                        <div
                          className="inline-flex items-center gap-2 px-3 py-2 rounded-xl border font-medium text-[0.75rem]"
                          style={{ background: step.tint, color: step.color, borderColor: step.border }}
                        >
                          <Shield size={13} strokeWidth={2} />
                          <span className="font-semibold">{step.label}</span>
                          <span className="text-[0.7rem] opacity-70">{step.note}</span>
                        </div>
                        {i < 2 && <ChevronDown size={14} className="ml-3 my-0.5 text-[var(--color-text-muted)]" />}
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            </Section>
          </div>
        </div>

        {/* Primary Action */}
        <div className="surface-card p-5">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div>
              <h2 className="text-heading text-[var(--color-text-primary)]">Confirm Authorization Decision</h2>
              <p className="text-body-sm text-[var(--color-text-secondary)] mt-1 max-w-2xl">
                Run the evaluation loop, bind the authorized outcome, and advance the workflow to certification.
              </p>
            </div>
            {decided && (
              <span className="pill border font-medium" style={{ background: '#ECF8F4', color: '#14936B', borderColor: '#D5EFE6' }}>
                Change #184 is authorized
              </span>
            )}
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-2 mt-4">
            {decidePhases.map((phase, i) => {
              const active = isRunning && phaseIndex === i;
              const done = isRunning ? phaseIndex > i : decided;
              return (
                <div
                  key={phase.id}
                  className="flex items-center gap-3 p-3 rounded-xl border transition-all"
                  style={
                    active
                      ? { background: `color-mix(in srgb, ${phase.color} 10%, transparent)`, borderColor: `color-mix(in srgb, ${phase.color} 55%, #FFFFFF)` }
                      : done
                      ? { background: '#EBF9F4', borderColor: '#D4F1E7' }
                      : { background: '#F5F7FB', borderColor: '#E3E8F2' }
                  }
                >
                  <div
                    className="flex items-center justify-center w-8 h-8 rounded-lg flex-shrink-0"
                    style={active ? { background: phase.color, color: 'white' } : done ? { background: '#0E9F6E', color: 'white' } : { background: `color-mix(in srgb, ${phase.color} 15%, transparent)`, color: phase.color }}
                  >
                    {active ? (
                      <div className="w-3.5 h-3.5 border-2 border-white border-t-transparent rounded-full animate-spin" />
                    ) : done ? (
                      <CheckCircle2 size={14} strokeWidth={2} />
                    ) : (
                      <Gavel size={14} strokeWidth={2} />
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
                <span className="font-mono" style={{ color: '#E98C4E' }}>
                  {Math.round(((phaseIndex + 1) / decidePhases.length) * 100)}%
                </span>
              </div>
              <div className="h-2 rounded-full overflow-hidden" style={{ background: '#F8DECF' }}>
                <div
                  className="h-full rounded-full transition-all duration-300"
                  style={{ background: '#E98C4E', width: `${((phaseIndex + 1) / decidePhases.length) * 100}%` }}
                />
              </div>
            </div>
          )}

          {!isRunning && !decided && (
            <button onClick={handleAuthorize} type="button" className="btn btn--primary w-full mt-4" style={{ padding: '0.875rem 1.5rem' }}>
              <Gavel size={18} strokeWidth={2} /> Confirm Authorization Decision
            </button>
          )}

          {decided && (
            <div className="mt-4 p-4 rounded-xl" style={{ background: '#EBF9F4', border: '1px solid #D4F1E7' }}>
              <div className="flex flex-wrap items-center justify-between gap-3">
                <div className="flex items-center gap-3">
                  <div className="flex items-center justify-center w-9 h-9 rounded-xl" style={{ background: '#0E9F6E', color: 'white' }}>
                    <CheckCircle2 size={18} strokeWidth={2} />
                  </div>
                  <div>
                    <p className="text-[0.8rem] font-bold" style={{ color: '#14936B' }}>Authorization Confirmed</p>
                    <p className="text-[0.7rem]" style={{ color: '#14936B' }}>Change {changeId} is authorized — ready for certification</p>
                  </div>
                </div>
                <button onClick={() => setActiveTab('Certify')} type="button" className="btn btn--primary">
                  Continue to Certify <ChevronRight size={16} strokeWidth={2} />
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
    </JourneyPage>
  );
}