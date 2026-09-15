'use client';

import { useState } from 'react';
import { JourneyPage, Section, LoadingState } from '@/components/shell/AppShell';
import { useAppStore } from '@/store/appStore';
import { lucideReact } from '@/lib/lucide-imports';
import { cn, stageColors } from '@/lib/design-tokens';
import type { ClaimData } from '@/components/ui/Claim';
import type { ImpactSurface, JourneyTab, VerificationModality } from '@/types';

const { ChevronRight, CheckCircle2, GitBranch, AlertTriangle, Lock, Ghost, FlaskConical, RefreshCw, Braces, Shield, Link: LinkIcon, Hash, FileCode } = lucideReact;

const phases = [
  { id: 'surfaces', label: 'Mapping semantic surfaces', icon: <GitBranch size={15} strokeWidth={1.75} />, color: '#22A7D4' },
  { id: 'zones', label: 'Traversing risk zones', icon: <AlertTriangle size={15} strokeWidth={1.75} />, color: '#D89A24' },
  { id: 'contract', label: 'Locking verification contract', icon: <Lock size={15} strokeWidth={1.75} />, color: '#7C5CE0' },
];

const directionMeta: Record<ImpactSurface['direction'], { color: string; tint: string; border: string }> = {
  REPLACE: { color: '#3D86F4', tint: '#EDF3FE', border: '#D9E6FC' },
  ADD: { color: '#1EAF8C', tint: '#EBF9F4', border: '#D4F1E7' },
  TOUCH: { color: '#D89A24', tint: '#FBF6E8', border: '#F2E7CC' },
  REMOVE: { color: '#D8493C', tint: '#FCEFEE', border: '#F5D5D3' },
  UNTOUCHED: { color: '#8A94A8', tint: '#EEF1F8', border: '#E3E8F2' },
};

const riskMeta: Record<ImpactSurface['risk'], { color: string; tint: string; border: string }> = {
  HIGH: { color: '#D8493C', tint: '#FCEFEE', border: '#F5D5D3' },
  MEDIUM: { color: '#C08A17', tint: '#FBF6E8', border: '#F2E7CC' },
  LOW: { color: '#0E9F6E', tint: '#EBF9F4', border: '#D4F1E7' },
};

const surfaceKindMeta = (kind: ImpactSurface['kind']): { color: string; tint: string; icon: React.ReactNode } => {
  switch (kind) {
    case 'CLAIM':
      return { color: '#7C5CE0', tint: '#F2EEFC', icon: <Shield size={15} strokeWidth={1.75} /> };
    case 'DEPENDENCY':
      return { color: '#C08A17', tint: '#FBF6E8', icon: <GitBranch size={15} strokeWidth={1.75} /> };
    default:
      return { color: '#3D86F4', tint: '#EDF3FE', icon: <FileCode size={15} strokeWidth={1.75} /> };
  }
};

const impactStatusMeta = {
  PENDING: { color: '#D89A24', tint: '#FBF6E8', border: '#F2E7CC' },
  COMPUTED: { color: '#C08A17', tint: '#FBF6E8', border: '#F2E7CC' },
  LOCKED: { color: '#7C5CE0', tint: '#F2EEFC', border: '#E3DBF6' },
} as const;

const planStatusMeta = {
  DRAFT: { color: '#8A94A8', tint: '#EEF1F8', border: '#E3E8F2' },
  LOCKED: { color: '#7C5CE0', tint: '#F2EEFC', border: '#E3DBF6' },
  COMPLETED: { color: '#14936B', tint: '#ECF8F4', border: '#D5EFE6' },
  SUPERSEDED: { color: '#8A94A8', tint: '#EEF1F8', border: '#E3E8F2' },
} as const;

const caseStatusMeta = {
  PENDING: { color: '#D89A24', tint: '#FBF6E8', border: '#F2E7CC' },
  RUNNING: { color: '#3D86F4', tint: '#EDF3FE', border: '#D9E6FC' },
  PASSED: { color: '#0E9F6E', tint: '#EBF9F4', border: '#D4F1E7' },
  FAILED: { color: '#D8493C', tint: '#FCEFEE', border: '#F5D5D3' },
  BLOCKED: { color: '#E98C4E', tint: '#FDF1EA', border: '#F8DECF' },
} as const;

const modalityMeta: Record<VerificationModality, { label: string; color: string; tint: string; border: string; icon: React.ReactNode }> = {
  STATIC_ANALYSIS: { label: 'STATIC ANALYSIS', color: '#5B66E8', tint: '#EEF0FD', border: '#DCE0FA', icon: <Braces size={16} strokeWidth={1.75} /> },
  DIFFERENTIAL_EXECUTION: { label: 'DIFFERENTIAL EXECUTION', color: '#7C5CE0', tint: '#F2EEFC', border: '#E3DBF6', icon: <GitBranch size={16} strokeWidth={1.75} /> },
  HISTORICAL_GHOST_REPLAY: { label: 'HISTORICAL GHOST REPLAY', color: '#14936B', tint: '#ECF8F4', border: '#D5EFE6', icon: <Ghost size={16} strokeWidth={1.75} /> },
  METAMORPHIC_CHECK: { label: 'METAMORPHIC CHECK', color: '#3D86F4', tint: '#EDF3FE', border: '#D9E6FC', icon: <RefreshCw size={16} strokeWidth={1.75} /> },
  ADVERSARIAL_SCENARIO: { label: 'ADVERSARIAL SCENARIO', color: '#D8493C', tint: '#FCEFEE', border: '#F5D5D3', icon: <AlertTriangle size={16} strokeWidth={1.75} /> },
  MUTATION_TEST: { label: 'MUTATION TEST', color: '#E98C4E', tint: '#FDF1EA', border: '#F8DECF', icon: <FlaskConical size={16} strokeWidth={1.75} /> },
};

function buildClaimDrawerData(claimId: string, reasoning: string, risk: ImpactSurface['risk']): ClaimData {
  return {
    id: claimId,
    claimId,
    statement: reasoning,
    authority: risk,
    confidence: 0.5,
    status: 'PROTECTED',
    locked: true,
    createdAt: new Date().toISOString(),
    evidenceIds: [],
  };
}

export default function AnalyzeTab() {
  const domain = useAppStore((s) => s.domain);
  const updateDomain = useAppStore((s) => s.updateDomain);
  const completeStage = useAppStore((s) => s.completeStage);
  const setActiveTab = useAppStore((s) => s.setActiveTab);
  const setWorkflowState = useAppStore((s) => s.setWorkflowState);
  const openDrawer = useAppStore((s) => s.openDrawer);
  const change = useAppStore((s) => s.change);

  const [isRunning, setIsRunning] = useState(false);
  const [phaseIndex, setPhaseIndex] = useState(-1);
  const [progress, setProgress] = useState(0);

  const impact = domain.impact;
  const contract = domain.verificationContract;

  if (!impact || !contract) {
    return <LoadingState message="Loading change definition…" />;
  }

  const isLocked = impact.status === 'LOCKED';
  const impactStatus = impactStatusMeta[impact.status];
  const planStatus = planStatusMeta[contract.status];

  const finish = (stage: JourneyTab, stayLabel: JourneyTab) => {
    completeStage(stage);
    setActiveTab(stayLabel);
  };

  const handleLockImpactMap = async () => {
    setIsRunning(true);
    setProgress(0);
    for (let i = 0; i < phases.length; i++) {
      setPhaseIndex(i);
      setProgress(((i + 1) / phases.length) * 100);
      await new Promise((resolve) => setTimeout(resolve, 650));
    }
    updateDomain({ impact: { ...impact, status: 'LOCKED' } });
    setWorkflowState({ currentStage: 'Analyze', trustStatus: 'PROTECTED' });
    finish('Analyze', 'Analyze');
    setIsRunning(false);
    setPhaseIndex(-1);
  };

  return (
    <JourneyPage
      title="Analyze"
      description="Map the proposed change against the behavioral graph to reveal semantic impact surfaces and risk zones."
    >
      <div className="space-y-5">
        {/* Lead card — Semantic Impact Map */}
        <div className="rounded-2xl border bg-white overflow-hidden shadow-sm" style={{ borderColor: stageColors.Analyze.border }}>
          <div className="h-1 w-full" style={{ background: stageColors.Analyze.active }} />
          <div className="px-6 py-6 space-y-5">
            <div className="flex items-start justify-between gap-4 flex-wrap">
              <div className="flex items-center gap-4">
                <div className="flex items-center justify-center w-12 h-12 rounded-xl" style={{ background: stageColors.Analyze.tint, color: stageColors.Analyze.active }}>
                  <GitBranch size={24} strokeWidth={1.75} />
                </div>
                <div>
                  <div className="flex items-center gap-2 flex-wrap">
                    <h2 className="text-heading font-semibold">Semantic Impact Map</h2>
                    <span className="pill border font-medium font-mono" style={{ background: stageColors.Analyze.tint, color: stageColors.Analyze.strong, borderColor: stageColors.Analyze.border }}>
                      {impact.id}
                    </span>
                  </div>
                  <p className="text-body-sm text-[var(--color-text-muted)] mt-0.5">{change?.title ?? 'Replace authentication provider and add passkey login'}</p>
                  <div className="flex flex-wrap items-center gap-2 mt-2">
                    <span className="pill border font-medium" style={{ background: '#EEF1F8', color: '#46536B', borderColor: '#E3E8F2' }}>
                      Change {change?.externalId ?? '#184'}
                    </span>
                    <span className="pill border font-medium font-mono" style={{ background: '#EEF1F8', color: '#46536B', borderColor: '#E3E8F2' }}>
                      <Hash size={12} /> commit {change?.commitSha ?? 'e8d1a91c'}
                    </span>
                    <span className="pill border font-medium font-mono" style={{ background: stageColors.Analyze.tint, color: stageColors.Analyze.strong, borderColor: stageColors.Analyze.border }}>
                      <FlaskConical size={12} /> {contract.id}
                    </span>
                  </div>
                </div>
              </div>
              <span className="pill border font-medium flex-shrink-0" style={{ background: impactStatus.tint, color: impactStatus.color, borderColor: impactStatus.border }}>
                {impact.status}
              </span>
            </div>

            <p className="text-body text-[var(--color-text-secondary)] leading-relaxed">{impact.summary}</p>
          </div>
        </div>

        {/* Impact Surfaces */}
        <Section title="Impact Surfaces" description="Semantic surfaces the proposed change replaces, adds, touches, or intentionally leaves alone.">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-3">
            {impact.surfaces.map((surf) => {
              const dir = directionMeta[surf.direction];
              const risk = riskMeta[surf.risk];
              const kind = surfaceKindMeta(surf.kind);
              return (
                <div key={surf.id} className="surface-card p-5">
                  <div className="flex items-center justify-between gap-3">
                    <span className="pill border font-medium" style={{ background: dir.tint, color: dir.color, borderColor: dir.border }}>
                      {surf.direction}
                    </span>
                    <span className="pill border font-medium" style={{ background: risk.tint, color: risk.color, borderColor: risk.border }}>
                      {surf.risk} RISK
                    </span>
                  </div>
                  <div className="mt-3 flex items-center gap-3">
                    <div className="flex items-center justify-center w-8 h-8 rounded-lg flex-shrink-0" style={{ background: kind.tint, color: kind.color }}>
                      {kind.icon}
                    </div>
                    <div className="flex-1 min-w-0">
                      <p className="text-body font-semibold text-[var(--color-text-primary)]">{surf.label}</p>
                      <p className="text-code-sm font-mono text-[var(--color-text-muted)] truncate">{surf.ref}</p>
                    </div>
                  </div>
                  <p className="text-body-sm text-[var(--color-text-secondary)] mt-3 leading-relaxed">{surf.reasoning}</p>
                  {surf.claimId && (
                    <div className="flex justify-end mt-3">
                      <button
                        type="button"
                        onClick={() => openDrawer('claim', { ...buildClaimDrawerData(surf.claimId as string, surf.reasoning, surf.risk) })}
                        className="pill border font-medium font-mono transition-all hover:shadow-sm"
                        style={{ background: 'var(--color-ink-tint)', color: 'var(--color-ink)', borderColor: 'var(--color-ink-soft)' }}
                      >
                        <LinkIcon size={12} /> {surf.claimId}
                      </button>
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        </Section>

        {/* Risk Zones */}
        <Section title="Risk Zones" description="Concentrated areas where the change could violate protected behavior.">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            {impact.riskZones.map((zone) => {
              const risk = riskMeta[zone.risk];
              return (
                <div key={zone.id} className="surface-card p-5" style={{ borderLeftWidth: 4, borderLeftStyle: 'solid', borderLeftColor: risk.color }}>
                  <div className="flex items-center justify-between gap-3">
                    <p className="text-body font-semibold text-[var(--color-text-primary)]">{zone.name}</p>
                    <span className="pill border font-medium flex-shrink-0" style={{ background: risk.tint, color: risk.color, borderColor: risk.border }}>
                      {zone.risk} RISK
                    </span>
                  </div>
                  <div className="flex flex-wrap items-center gap-2 mt-3">
                    {zone.claimIds.map((claimId) => (
                      <button
                        key={claimId}
                        type="button"
                        onClick={() => openDrawer('claim', { ...buildClaimDrawerData(claimId, zone.reasoning, zone.risk) })}
                        className="pill border font-medium font-mono transition-all hover:shadow-sm"
                        style={{ background: 'var(--color-ink-tint)', color: 'var(--color-ink)', borderColor: 'var(--color-ink-soft)' }}
                      >
                        <LinkIcon size={12} /> {claimId}
                      </button>
                    ))}
                    <span className="pill border font-medium font-mono" style={{ background: '#EEF1F8', color: '#46536B', borderColor: '#E3E8F2' }}>
                      <Hash size={12} /> {zone.id}
                    </span>
                  </div>
                  <p className="text-body-sm text-[var(--color-text-secondary)] mt-3 leading-relaxed">{zone.reasoning}</p>
                </div>
              );
            })}
          </div>
        </Section>

        {/* Verification Contract */}
        <Section title="Verification Contract" description={`Independent verification modalities bound to the impact map for Change ${change?.externalId ?? '#184'}.`}>
          <div className="surface-card p-5 mb-3">
            <div className="flex items-center justify-between gap-3 flex-wrap">
              <div className="flex items-center gap-3">
                <div className="flex items-center justify-center w-10 h-10 rounded-lg flex-shrink-0" style={{ background: '#F2EEFC', color: '#7C5CE0' }}>
                  <FlaskConical size={20} strokeWidth={1.75} />
                </div>
                <div>
                  <p className="text-body font-semibold text-[var(--color-text-primary)]">{contract.title}</p>
                  <p className="text-caption font-mono text-[var(--color-text-muted)] mt-0.5">
                    {contract.id} · {contract.claimIds.length} protected claims · {contract.cases.length} cases
                  </p>
                </div>
              </div>
              <span className="pill border font-medium flex-shrink-0" style={{ background: planStatus.tint, color: planStatus.color, borderColor: planStatus.border }}>
                {contract.status}
              </span>
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-3">
            {contract.cases.map((c) => {
              const meta = modalityMeta[c.kind];
              const cstatus = caseStatusMeta[c.status];
              return (
                <div key={c.id} className="surface-card p-5">
                  <div className="flex items-start justify-between gap-3">
                    <div className="flex items-center gap-3">
                      <div className="flex items-center justify-center w-9 h-9 rounded-lg flex-shrink-0" style={{ background: meta.tint, color: meta.color }}>
                        {meta.icon}
                      </div>
                      <div>
                        <p className="text-code-sm font-bold font-mono text-[var(--color-text-primary)]">{meta.label}</p>
                        <p className="text-caption font-mono text-[var(--color-text-muted)]">{c.id}</p>
                      </div>
                    </div>
                    <span className="pill border font-medium flex-shrink-0" style={{ background: cstatus.tint, color: cstatus.color, borderColor: cstatus.border }}>
                      {c.status}
                    </span>
                  </div>
                  <p className="text-body-sm font-medium text-[var(--color-text-primary)] mt-3 leading-relaxed">{c.name}</p>
                  <div className="mt-2">
                    <p className="text-caption text-[var(--color-text-muted)]">Expected</p>
                    <p className="text-code-sm font-mono text-[var(--color-text-secondary)]">{c.expected ?? '—'}</p>
                  </div>
                  <div className="flex flex-wrap items-center gap-2 mt-3">
                    {c.independent && (
                      <span className="pill border font-medium" style={{ background: '#F2EEFC', color: '#46536B', borderColor: '#E3DBF6' }}>
                        <Shield size={12} /> Independent
                      </span>
                    )}
                    {c.result && (
                      <>
                        <span className="pill border font-medium font-mono" style={{ background: '#EBF9F4', color: '#46536B', borderColor: '#D4F1E7' }}>
                          {c.result.passed} passed
                        </span>
                        {c.result.failed > 0 && (
                          <span className="pill border font-medium font-mono" style={{ background: '#FCEFEE', color: '#46536B', borderColor: '#F5D5D3' }}>
                            {c.result.failed} failed
                          </span>
                        )}
                        {c.result.skipped > 0 && (
                          <span className="pill border font-medium font-mono" style={{ background: '#EEF1F8', color: '#8A94A8', borderColor: '#E3E8F2' }}>
                            {c.result.skipped} skipped
                          </span>
                        )}
                      </>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        </Section>

        {/* Primary action — Lock Impact Map & Contract */}
        <Section title="Lock Impact Map & Contract" description="Freeze the semantic impact surfaces, risk zones, and verification contract as governing context for the change.">
          <div className="surface-card p-5">
            {isLocked ? (
              <div className="p-4 rounded-xl bg-[#ebf9f4] border border-[#d4f1e7]">
                <div className="flex items-center gap-3">
                  <div className="flex items-center justify-center w-9 h-9 rounded-xl bg-[#0e9f6e] text-white">
                    <CheckCircle2 size={18} strokeWidth={2} />
                  </div>
                  <div>
                    <p className="text-[0.8rem] font-bold text-[#14936b]">Impact Map & Contract Locked</p>
                    <p className="text-[0.7rem] text-[#14936b]">Semantic surfaces, risk zones, and verification modalities bound to Change {change?.externalId ?? '#184'}</p>
                  </div>
                </div>
                <button onClick={() => setActiveTab('Develop')} className="btn btn--primary mt-4">
                  Continue to Develop <ChevronRight size={16} strokeWidth={2} />
                </button>
              </div>
            ) : (
               <div className="space-y-3">
                {phases.map((phase, i) => (
                  <div
                    key={phase.id}
                    className={cn(
                      'flex items-center gap-3 p-2.5 rounded-xl border transition-all',
                      isRunning && phaseIndex === i
                        ? 'border-[var(--color-accent-soft)] bg-[var(--color-accent-tint)]'
                        : isRunning && phaseIndex > i
                        ? 'border-[#d4f1e7] bg-[#ebf9f4]'
                        : 'border-transparent',
                    )}
                  >
                    <div
                      className="flex items-center justify-center w-8 h-8 rounded-lg flex-shrink-0"
                      style={
                        isRunning && phaseIndex === i
                          ? { background: phase.color, color: 'white' }
                          : isRunning && phaseIndex > i
                          ? { background: '#0e9f6e', color: 'white' }
                          : { background: phase.color + '15', color: phase.color }
                      }
                    >
                      {isRunning && phaseIndex === i ? (
                        <div className="w-3.5 h-3.5 border-2 border-white border-t-transparent rounded-full animate-spin" />
                      ) : isRunning && phaseIndex > i ? (
                        <CheckCircle2 size={14} strokeWidth={2} />
                      ) : (
                        phase.icon
                      )}
                    </div>
                    <span className="text-[0.8rem] font-semibold text-[var(--color-text-primary)]">{phase.label}</span>
                    {isRunning && phaseIndex === i && (
                      <span className="text-[0.65rem] font-mono text-[var(--color-text-muted)] ml-auto">Running...</span>
                    )}
                    {isRunning && phaseIndex > i && (
                      <span className="text-[0.65rem] font-mono text-[#0e9f6e] ml-auto">Done</span>
                    )}
                  </div>
                ))}

                {isRunning && (
                  <div>
                    <div className="flex items-center justify-between text-[0.7rem] font-medium mb-1.5">
                      <span className="text-[var(--color-text-secondary)]">Progress</span>
                      <span className="font-mono text-[#22a7d4]">{Math.round(progress)}%</span>
                    </div>
                    <div className="h-2 bg-[var(--color-accent-soft)] rounded-full overflow-hidden">
                      <div className="h-full bg-[#22a7d4] rounded-full transition-all duration-300" style={{ width: `${progress}%` }} />
                    </div>
                  </div>
                )}

                {!isRunning && (
                  <button onClick={handleLockImpactMap} className="btn btn--primary w-full" style={{ padding: '0.875rem 1.5rem' }}>
                    <Lock size={18} strokeWidth={2} /> Lock Impact Map & Contract
                  </button>
                )}
              </div>
            )}
          </div>
        </Section>
      </div>
    </JourneyPage>
  );
}