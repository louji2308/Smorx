'use client';

import { useState } from 'react';
import { JourneyPage, Section, LoadingState } from '@/components/shell/AppShell';
import { useAppStore } from '@/store/appStore';
import { lucideReact } from '@/lib/lucide-imports';
import { cn, stageColors } from '@/lib/design-tokens';
import type { IntentItem, IntentKind, JourneyTab } from '@/types';

const { ChevronRight, CheckCircle2, Shield, Lock, Layers, FileText, Hash, Plus, RefreshCw, Zap } = lucideReact;

const phases = [
  { id: 'normalize', label: 'Normalizing request', icon: <FileText size={15} strokeWidth={1.75} />, color: '#3D86F4' },
  { id: 'compile', label: 'Compiling intent dimensions', icon: <Layers size={15} strokeWidth={1.75} />, color: '#1EAF8C' },
  { id: 'lock', label: 'Locking intent', icon: <Lock size={15} strokeWidth={1.75} />, color: '#7C5CE0' },
];

const intentKindMeta: Record<IntentKind, { color: string; tint: string; border: string; icon: React.ReactNode }> = {
  PRESERVE: { color: '#0E9F6E', tint: '#EBF9F4', border: '#D4F1E7', icon: <Shield size={16} strokeWidth={1.75} /> },
  REPLACE: { color: '#3D86F4', tint: '#EDF3FE', border: '#D9E6FC', icon: <RefreshCw size={16} strokeWidth={1.75} /> },
  ADD: { color: '#1EAF8C', tint: '#EBF9F4', border: '#D4F1E7', icon: <Plus size={16} strokeWidth={1.75} /> },
  SECURITY: { color: '#D8493C', tint: '#FCEFEE', border: '#F5D5D3', icon: <Lock size={16} strokeWidth={1.75} /> },
  PERFORMANCE: { color: '#C08A17', tint: '#FBF6E8', border: '#F2E7CC', icon: <Zap size={16} strokeWidth={1.75} /> },
};

const priorityMeta: Record<IntentItem['priority'], { color: string; tint: string; border: string }> = {
  CRITICAL: { color: '#D8493C', tint: '#FCEFEE', border: '#F5D5D3' },
  HIGH: { color: '#C08A17', tint: '#FBF6E8', border: '#F2E7CC' },
  NORMAL: { color: '#5B6478', tint: '#EEF1F8', border: '#E3E8F2' },
  LOW: { color: '#8A94A8', tint: '#EEF1F8', border: '#E3E8F2' },
};

const intentStatusMeta: Record<IntentItem['status'], { color: string; tint: string; border: string }> = {
  PENDING: { color: '#D89A24', tint: '#FBF6E8', border: '#F2E7CC' },
  CONFIRMED: { color: '#C08A17', tint: '#FBF6E8', border: '#F2E7CC' },
  LOCKED: { color: '#7C5CE0', tint: '#F2EEFC', border: '#E3DBF6' },
  SUPERSEDED: { color: '#8A94A8', tint: '#EEF1F8', border: '#E3E8F2' },
};

const ledgerStatusMeta = {
  DRAFT: { color: '#8A94A8', tint: '#EEF1F8', border: '#E3E8F2' },
  CONFIRMED: { color: '#C08A17', tint: '#FBF6E8', border: '#F2E7CC' },
  LOCKED: { color: '#7C5CE0', tint: '#F2EEFC', border: '#E3DBF6' },
} as const;

function extractRefs(text: string): string[] {
  const matches = text.match(/\(([A-Z]+-\d+)\)/g) ?? [];
  return matches.map((m) => m.replace(/[()]/g, ''));
}

function splitCriteria(text: string): { id: string | null; text: string } {
  const match = text.match(/^(AC-\d+):\s*(.*)$/);
  return match ? { id: match[1], text: match[2] } : { id: null, text };
}

export default function DefineTab() {
  const domain = useAppStore((s) => s.domain);
  const updateDomain = useAppStore((s) => s.updateDomain);
  const completeStage = useAppStore((s) => s.completeStage);
  const setActiveTab = useAppStore((s) => s.setActiveTab);
  const setWorkflowState = useAppStore((s) => s.setWorkflowState);
  const change = useAppStore((s) => s.change);

  const [isRunning, setIsRunning] = useState(false);
  const [phaseIndex, setPhaseIndex] = useState(-1);
  const [progress, setProgress] = useState(0);

  const ledger = domain.intentLedger;

  if (!ledger || !domain.impact) {
    return <LoadingState message="Loading change definition…" />;
  }

  const isLocked = ledger.status === 'LOCKED';
  const status = ledgerStatusMeta[ledger.status];

  const finish = (stage: JourneyTab, stayLabel: JourneyTab) => {
    completeStage(stage);
    setActiveTab(stayLabel);
  };

  const handleLockIntentLedger = async () => {
    setIsRunning(true);
    setProgress(0);
    for (let i = 0; i < phases.length; i++) {
      setPhaseIndex(i);
      setProgress(((i + 1) / phases.length) * 100);
      await new Promise((resolve) => setTimeout(resolve, 650));
    }
    updateDomain({
      intentLedger: { ...ledger, status: 'LOCKED', lockedAt: new Date().toISOString() },
      intents: domain.intents.map((i) => ({ ...i, status: 'LOCKED' })),
    });
    setWorkflowState({ currentStage: 'Define', trustStatus: 'PROTECTED' });
    finish('Define', 'Define');
    setIsRunning(false);
    setPhaseIndex(-1);
  };

  return (
    <JourneyPage
      title="Define"
      description="Normalize human requests into objective, constraints, and acceptance criteria; compile intent across five dimensions."
    >
      <div className="space-y-5">
        {/* Lead card — Intent Ledger */}
        <div className="rounded-2xl border bg-white overflow-hidden shadow-sm" style={{ borderColor: stageColors.Define.border }}>
          <div className="h-1 w-full" style={{ background: stageColors.Define.active }} />
          <div className="px-6 py-6 space-y-5">
            <div className="flex items-start justify-between gap-4 flex-wrap">
              <div className="flex items-center gap-4">
                <div className="flex items-center justify-center w-12 h-12 rounded-xl" style={{ background: stageColors.Define.tint, color: stageColors.Define.active }}>
                  <FileText size={24} strokeWidth={1.75} />
                </div>
                <div>
                  <div className="flex items-center gap-2 flex-wrap">
                    <h2 className="text-heading font-semibold">Intent Ledger</h2>
                    <span className="pill border font-medium font-mono" style={{ background: stageColors.Define.tint, color: stageColors.Define.strong, borderColor: stageColors.Define.border }}>
                      {ledger.id}
                    </span>
                  </div>
                  <p className="text-body-sm text-[var(--color-text-muted)] mt-0.5">{ledger.title}</p>
                  <div className="flex flex-wrap items-center gap-2 mt-2">
                    <span className="pill border font-medium" style={{ background: '#EEF1F8', color: '#46536B', borderColor: '#E3E8F2' }}>
                      Change {change?.externalId ?? '#184'}
                    </span>
                    <span className="pill border font-medium font-mono" style={{ background: '#EEF1F8', color: '#46536B', borderColor: '#E3E8F2' }}>
                      <Hash size={12} /> commit {change?.commitSha ?? 'e8d1a91c'}
                    </span>
                  </div>
                </div>
              </div>
              <span className="pill border font-medium flex-shrink-0" style={{ background: status.tint, color: status.color, borderColor: status.border }}>
                {ledger.status}
              </span>
            </div>

            <div className="flex flex-wrap items-center gap-2 p-3 rounded-xl">
              <span className="pill border font-medium font-mono" style={{ background: stageColors.Define.tint, color: stageColors.Define.strong, borderColor: stageColors.Define.border }}>
                <Hash size={12} /> {ledger.authorizationId}
              </span>
              <span className="text-body-sm text-[var(--color-text-secondary)]">
                Authorized by {ledger.authorizedBy}
              </span>
            </div>

            <p className="text-body text-[var(--color-text-secondary)] leading-relaxed">{ledger.background}</p>
          </div>
        </div>

        {/* Objectives */}
        <Section title="Objectives" description="The explicit outcomes this change is meant to deliver.">
          <div className="space-y-3">
            {ledger.objectives.map((objective, i) => (
              <div key={i} className="flex items-center gap-3 p-3 rounded-xl border" style={{ background: '#EBF9F4', borderColor: '#D4F1E7' }}>
                <div className="flex items-center justify-center w-8 h-8 rounded-lg flex-shrink-0" style={{ background: '#EBF9F4', color: '#1EAF8C' }}>
                  <CheckCircle2 size={16} strokeWidth={2} />
                </div>
                <p className="text-body font-medium text-[var(--color-text-primary)]">{objective}</p>
              </div>
            ))}
          </div>
        </Section>

        {/* Constraints */}
        <Section title="Constraints" description="Constitutional boundaries the change may not cross.">
          <div className="space-y-3">
            {ledger.constraints.map((constraint, i) => {
              const refs = extractRefs(constraint);
              return (
                <div key={i} className="flex items-start gap-3 p-3 rounded-xl border" style={{ background: '#EBF9F4', borderColor: '#D4F1E7' }}>
                  <div className="flex items-center justify-center w-8 h-8 rounded-lg flex-shrink-0" style={{ background: '#EBF9F4', color: '#0E9F6E' }}>
                    <Shield size={16} strokeWidth={2} />
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="text-body-sm font-medium text-[var(--color-text-primary)]">{constraint}</p>
                    {refs.length > 0 && (
                      <div className="flex flex-wrap gap-1.5 mt-2">
                        {refs.map((ref) => (
                          <span key={ref} className="pill border font-medium font-mono" style={{ background: '#EBF9F4', color: '#0E9F6E', borderColor: '#D4F1E7' }}>
                            {ref}
                          </span>
                        ))}
                      </div>
                    )}
                  </div>
                  <span className="pill border font-medium flex-shrink-0" style={{ background: '#EBF9F4', color: '#0E9F6E', borderColor: '#D4F1E7' }}>
                    protected
                  </span>
                </div>
              );
            })}
          </div>
        </Section>

        {/* Acceptance Criteria */}
        <Section title="Acceptance Criteria" description="Objective measures that define what 'done' means for this change.">
          <div className="space-y-3">
            {ledger.acceptanceCriteria.map((criteria, i) => {
              const { id, text } = splitCriteria(criteria);
              return (
                <div key={i} className="flex items-start gap-3 p-3 rounded-xl">
                  <CheckCircle2 size={16} strokeWidth={2} className="mt-0.5 flex-shrink-0" style={{ color: '#0E9F6E' }} />
                  {id && (
                    <span className="pill border font-medium font-mono" style={{ background: '#EBF9F4', color: '#0E9F6E', borderColor: '#D4F1E7' }}>
                      {id}
                    </span>
                  )}
                  <p className="text-body-sm text-[var(--color-text-primary)]">{text}</p>
                </div>
              );
            })}
          </div>
        </Section>

        {/* Intent Dimensions */}
        <Section title="Intent Dimensions" description="Five intent dimensions compiled from the human request.">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-3">
            {domain.intents.map((intent) => {
              const kind = intentKindMeta[intent.kind];
              const priority = priorityMeta[intent.priority];
              const intentStatus = intentStatusMeta[intent.status];
              return (
                <div key={intent.id} className="surface-card p-5">
                  <div className="flex items-start justify-between gap-3">
                    <div className="flex items-center gap-3">
                      <div className="flex items-center justify-center w-9 h-9 rounded-lg flex-shrink-0" style={{ background: kind.tint, color: kind.color }}>
                        {kind.icon}
                      </div>
                      <div>
                        <p className="text-code-sm font-bold font-mono" style={{ color: kind.color }}>{intent.kind}</p>
                        <p className="text-caption font-mono text-[var(--color-text-muted)]">{intent.id}</p>
                      </div>
                    </div>
                    <span className="pill border font-medium flex-shrink-0" style={{ background: intentStatus.tint, color: intentStatus.color, borderColor: intentStatus.border }}>
                      {intent.status}
                    </span>
                  </div>
                  <p className="text-body mt-3 leading-relaxed text-[var(--color-text-primary)]">{intent.statement}</p>
                  <div className="flex flex-wrap items-center gap-2 mt-4">
                    <span className="pill border font-medium" style={{ background: priority.tint, color: priority.color, borderColor: priority.border }}>
                      {intent.priority}
                    </span>
                    {intent.sourceRef && (
                      <span className="pill border font-medium font-mono" style={{ background: '#EEF1F8', color: '#46536B', borderColor: '#E3E8F2' }}>
                        <Hash size={12} /> {intent.sourceRef}
                      </span>
                    )}
                    {intent.authorized && (
                      <span className="pill border font-medium" style={{ background: '#EBF9F4', color: '#0E9F6E', borderColor: '#D4F1E7' }}>
                        <CheckCircle2 size={12} /> Authorized
                      </span>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        </Section>

        {/* Primary action — Lock Intent Ledger */}
        <Section title="Compile & Lock" description="Normalize the request and lock the intent ledger as immutable governing context.">
          <div className="surface-card p-5">
            {isLocked ? (
              <div className="p-4 rounded-xl bg-[#ebf9f4] border border-[#d4f1e7]">
                <div className="flex items-center gap-3">
                  <div className="flex items-center justify-center w-9 h-9 rounded-xl bg-[#0e9f6e] text-white">
                    <CheckCircle2 size={18} strokeWidth={2} />
                  </div>
                  <div>
                    <p className="text-[0.8rem] font-bold text-[#14936b]">Intent Ledger Locked</p>
                    <p className="text-[0.7rem] text-[#14936b]">Change definition compiled and bound to Change {change?.externalId ?? '#184'}</p>
                  </div>
                </div>
                {ledger.lockedAt && (
                  <div className="flex items-center gap-2 mt-3">
                    <Lock size={12} className="text-[#14936b]" />
                    <p className="text-[0.7rem] font-mono text-[#14936b]">Locked {new Date(ledger.lockedAt).toLocaleString()}</p>
                  </div>
                )}
                <button onClick={() => setActiveTab('Analyze')} className="btn btn--primary mt-4">
                  Continue to Analyze <ChevronRight size={16} strokeWidth={2} />
                </button>
              </div>
            ) : (
              <div className="space-y-4">
                {phases.map((phase, i) => (
                  <div
                    key={phase.id}
                    className={cn(
                      'flex items-center gap-3 p-3 rounded-xl border transition-all',
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
                      <span className="font-mono text-[#3d86f4]">{Math.round(progress)}%</span>
                    </div>
                    <div className="h-2 bg-[var(--color-accent-soft)] rounded-full overflow-hidden">
                      <div className="h-full bg-[#3d86f4] rounded-full transition-all duration-300" style={{ width: `${progress}%` }} />
                    </div>
                  </div>
                )}

                {!isRunning && (
                  <button onClick={handleLockIntentLedger} className="btn btn--primary w-full" style={{ padding: '0.875rem 1.5rem' }}>
                    <Lock size={18} strokeWidth={2} /> Lock Intent Ledger
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