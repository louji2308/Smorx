'use client';

import { useMemo, useState, type ReactNode } from 'react';
import { useAppStore } from '@/store/appStore';
import { JourneyPage, Section, LoadingState } from '@/components/shell/AppShell';
import { lucideReact } from '@/lib/lucide-imports';
import { cn } from '@/lib/design-tokens';
import type { JourneyTab, VerificationModality, VerificationRun } from '@/types';

const {
  Shield,
  Lock,
  Hash,
  Terminal,
  ChevronRight,
  CheckCircle2,
  XCircle,
  Play,
  Clock,
  FileText,
  GitBranch,
  Ghost,
  RefreshCw,
  AlertTriangle,
  FlaskConical,
  Eye,
} = lucideReact;

const sleep = (ms: number) => new Promise<void>((resolve) => setTimeout(resolve, ms));

const VER = {
  active: '#D89A24',
  strong: '#A9761B',
  tint: '#FBF6E8',
  border: '#F2E7CC',
};

const modalityMeta: Record<VerificationModality, { label: string; color: string; icon: ReactNode }> = {
  STATIC_ANALYSIS: { label: 'Static Analysis', color: '#5B66E8', icon: <FileText size={14} strokeWidth={1.75} /> },
  DIFFERENTIAL_EXECUTION: { label: 'Differential Execution', color: '#7C5CE0', icon: <GitBranch size={14} strokeWidth={1.75} /> },
  HISTORICAL_GHOST_REPLAY: { label: 'Ghost Replay', color: '#14936B', icon: <Ghost size={14} strokeWidth={1.75} /> },
  METAMORPHIC_CHECK: { label: 'Metamorphic Check', color: '#3D86F4', icon: <RefreshCw size={14} strokeWidth={1.75} /> },
  ADVERSARIAL_SCENARIO: { label: 'Adversarial Scenario', color: '#D8493C', icon: <AlertTriangle size={14} strokeWidth={1.75} /> },
  MUTATION_TEST: { label: 'Mutation Test', color: '#E98C4E', icon: <FlaskConical size={14} strokeWidth={1.75} /> },
};

const formatDuration = (startedAt: string, finishedAt?: string) => {
  if (!finishedAt) return '—';
  const ms = Math.max(0, new Date(finishedAt).getTime() - new Date(startedAt).getTime());
  return ms >= 1000 ? `${(ms / 1000).toFixed(1)}s` : `${ms}ms`;
};

export function VerifyTab() {
  const domain = useAppStore((s) => s.domain);
  const updateDomain = useAppStore((s) => s.updateDomain);
  const completeStage = useAppStore((s) => s.completeStage);
  const setActiveTab = useAppStore((s) => s.setActiveTab);
  const setWorkflowState = useAppStore((s) => s.setWorkflowState);

  const [runState, setRunState] = useState<'idle' | 'running' | 'done'>('idle');
  const [activeStep, setActiveStep] = useState(-1);

  const { verificationContract: contract, verificationRuns } = domain;

  const fusion = useMemo(() => {
    let passed = 0;
    let failed = 0;
    let skipped = 0;
    for (const run of verificationRuns) {
      for (const c of run.cases) {
        passed += c.result?.passed ?? 0;
        failed += c.result?.failed ?? 0;
        skipped += c.result?.skipped ?? 0;
      }
    }
    return { passed, failed, skipped };
  }, [verificationRuns]);

  const finish = (stage: JourneyTab) => {
    completeStage(stage);
    setActiveTab(stage);
  };

  const handleRunSuite = async () => {
    if (!contract || runState === 'running') return;
    setRunState('running');
    setActiveStep(0);
    for (let i = 0; i < contract.modalities.length; i++) {
      setActiveStep(i);
      await sleep(650);
    }
    const now = new Date().toISOString();
    const run3: VerificationRun = {
      id: 'VER-184-R3',
      planId: contract.id,
      label: 'Final verification run after Develop',
      status: 'COMPLETED',
      startedAt: now,
      finishedAt: now,
      cases: contract.cases.map((c, i) => ({
        ...c,
        status: 'PASSED' as const,
        evidenceIds: [`EV-50${i + 1}`],
        result: c.result ?? { passed: 0, failed: 0, skipped: 0, durationMs: 0 },
      })),
    };
    updateDomain({ verificationRuns: [...verificationRuns, run3] });
    setWorkflowState({ currentStage: 'Verify', trustStatus: 'UNVERIFIED' });
    setActiveStep(-1);
    setRunState('done');
    finish('Verify');
  };

  if (!contract || !verificationRuns.length) {
    return <LoadingState message="Loading verification lab…" />;
  }

  const suiteSteps = contract.modalities.map((m) => modalityMeta[m]);

  return (
    <JourneyPage
      title="Verify"
      description="Run and inspect independent verification modules — static analysis, differential execution, ghost replay, metamorphic, adversarial, mutation."
    >
      <div className="space-y-5">
        {/* Lead card — Verification Contract */}
        <div className="rounded-2xl border bg-white overflow-hidden shadow-sm" style={{ borderColor: VER.border }}>
          <div className="h-1 w-full" style={{ background: VER.active }} />
          <div className="px-6 py-6 space-y-5">
            <div className="flex items-start justify-between gap-4">
              <div>
                <h2 className="text-heading text-[var(--color-text-primary)]">
                  Verification Contract <span className="font-mono">VP-184</span>
                </h2>
                <p className="text-body-sm text-[var(--color-text-muted)] mt-0.5">
                  Locked contract governing independent verification for Change #184.
                </p>
              </div>
              <span className="pill border font-medium" style={{ color: '#7C5CE0', background: '#F2EEFC', borderColor: '#E3DBF6' }}>
                <Lock size={12} strokeWidth={2} />
                LOCKED
              </span>
            </div>
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
              <div>
                <p className="text-caption font-semibold text-[var(--color-text-muted)] uppercase tracking-wider mb-2">
                  Protected Claims ({contract.claimIds.length})
                </p>
                <div className="flex flex-wrap gap-2">
                  {contract.claimIds.map((claimId) => (
                    <span
                      key={claimId}
                      className="pill border font-medium font-mono"
                      style={{ color: '#7C5CE0', background: '#F2EEFC', borderColor: '#E3DBF6' }}
                    >
                      <Shield size={12} strokeWidth={2} />
                      {claimId}
                    </span>
                  ))}
                </div>
              </div>
              <div>
                <p className="text-caption font-semibold text-[var(--color-text-muted)] uppercase tracking-wider mb-2">
                  Modalities ({contract.modalities.length})
                </p>
                <div className="flex flex-wrap gap-2">
                  {contract.modalities.map((m) => {
                    const meta = modalityMeta[m];
                    return (
                      <span
                        key={m}
                        className="pill border font-medium"
                        style={{ color: meta.color, background: `${meta.color}15`, borderColor: `${meta.color}40` }}
                      >
                        {meta.icon}
                        {meta.label}
                      </span>
                    );
                  })}
                </div>
              </div>
            </div>
          </div>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-5">
          {/* Execution History */}
          <div className="lg:col-span-2 space-y-5">
            <Section title="Execution History" description="Independent verification runs with case-level evidence.">
              <div className="space-y-5">
                {verificationRuns.map((run) => {
                  const failedCount = run.cases.filter((c) => c.status === 'FAILED').length;
                  const passedCount = run.cases.reduce((a, c) => a + (c.result?.passed ?? 0), 0);
                  const failedTotal = run.cases.reduce((a, c) => a + (c.result?.failed ?? 0), 0);
                  return (
                     <div key={run.id} className="surface-card p-5 space-y-3">
                      <div className="flex flex-wrap items-start justify-between gap-3">
                        <div>
                          <p className="font-mono text-code-sm text-[var(--color-text-muted)]">{run.id}</p>
                          <p className="text-subheading text-[var(--color-text-primary)] mt-0.5">{run.label}</p>
                        </div>
                        <div className="flex items-center gap-2">
                          {failedCount > 0 ? (
                            <span className="pill border font-medium" style={{ color: '#D8493C', background: '#FCEFEE', borderColor: '#F5D5D3' }}>
                              <XCircle size={12} strokeWidth={2} />
                              {failedCount} CASE FAILED
                            </span>
                          ) : (
                            <span className="pill border font-medium" style={{ color: '#0E9F6E', background: '#EBF9F4', borderColor: '#D4F1E7' }}>
                              <CheckCircle2 size={12} strokeWidth={2} />
                              ALL PASSED
                            </span>
                          )}
                        </div>
                      </div>
                      <div className="flex items-center gap-4 text-caption text-[var(--color-text-muted)]">
                        <span className="flex items-center gap-1.5">
                          <Clock size={12} strokeWidth={2} />
                          {run.finishedAt ? new Date(run.finishedAt).toLocaleString() : '—'}
                        </span>
                        <span className="flex items-center gap-1.5 font-mono">
                          <Terminal size={12} strokeWidth={2} />
                          {formatDuration(run.startedAt, run.finishedAt)}
                        </span>
                        <span className="ml-auto font-mono">
                          {passedCount} passed · {failedTotal} failed
                        </span>
                      </div>
                      <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                        {run.cases.map((c) => {
                          const meta = modalityMeta[c.kind];
                          const result = c.result;
                          return (
                            <div key={c.id} className="rounded-xl border p-4 bg-white border-[var(--color-surface-border)]">
                              <div className="flex items-start justify-between gap-2">
                                <div className="flex items-center gap-2 min-w-0">
                                  <span
                                    className="flex items-center justify-center w-8 h-8 rounded-lg flex-shrink-0"
                                    style={{ background: `${meta.color}15`, color: meta.color }}
                                  >
                                    {meta.icon}
                                  </span>
                                  <span className="text-body-sm font-semibold text-[var(--color-text-primary)] truncate">
                                    {c.name}
                                  </span>
                                </div>
                                {c.status === 'FAILED' ? (
                                  <span className="pill border font-medium flex-shrink-0" style={{ color: '#D8493C', background: '#FCEFEE', borderColor: '#F5D5D3' }}>
                                    <XCircle size={12} strokeWidth={2} />
                                    FAILED
                                  </span>
                                ) : (
                                  <span className="pill border font-medium flex-shrink-0" style={{ color: '#0E9F6E', background: '#EBF9F4', borderColor: '#D4F1E7' }}>
                                    <CheckCircle2 size={12} strokeWidth={2} />
                                    PASSED
                                  </span>
                                )}
                              </div>
                              <p className="text-caption text-[var(--color-text-muted)] mt-2">{c.expected}</p>
                              <div className="flex flex-wrap items-center gap-3 mt-3">
                                <span className="font-mono text-code-sm font-semibold" style={{ color: '#0E9F6E' }}>
                                  ✓ {result?.passed ?? 0}
                                </span>
                                <span className="font-mono text-code-sm font-semibold" style={{ color: '#D8493C' }}>
                                  ✕ {result?.failed ?? 0}
                                </span>
                                <span className="font-mono text-code-sm text-[var(--color-text-muted)]">
                                  skipped {result?.skipped ?? 0}
                                </span>
                                <span className="font-mono text-code-sm text-[var(--color-text-muted)]">
                                  {result?.durationMs ?? 0}ms
                                </span>
                                {c.independent && (
                                  <span className="pill border font-medium" style={{ color: '#0E9F6E', background: '#EBF9F4', borderColor: '#D4F1E7' }}>
                                    independent
                                  </span>
                                )}
                              </div>
                              <div className="flex flex-wrap gap-1.5 mt-3 pt-3 border-t border-[var(--color-surface-border)]">
                                <span className="font-mono text-caption text-[var(--color-text-muted)]">{c.id}</span>
                                {c.evidenceIds.map((eid) => (
                                  <span
                                    key={eid}
                                    className="pill border font-medium font-mono"
                                    style={{ color: '#8A94A8', background: '#EEF1F8', borderColor: '#E3E8F2' }}
                                  >
                                    <Hash size={11} strokeWidth={2} />
                                    {eid}
                                  </span>
                                ))}
                              </div>
                            </div>
                          );
                        })}
                      </div>
                    </div>
                  );
                })}
              </div>
            </Section>

            {/* Evidence Fusion */}
            <Section title="Evidence Fusion" description="Normalized evidence across the verification family — claim-level.">
              <div className="surface-card p-5">
                <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                  <div className="p-4 rounded-xl bg-[#EBF9F4] border border-[#D4F1E7]">
                    <p className="text-caption font-semibold text-[var(--color-text-muted)] uppercase tracking-wider">Total Passed</p>
                    <p className="font-mono text-display font-semibold text-[#0E9F6E]">{fusion.passed}</p>
                  </div>
                  <div className="p-4 rounded-xl bg-[#FCEFEE] border border-[#F5D5D3]">
                    <p className="text-caption font-semibold text-[var(--color-text-muted)] uppercase tracking-wider">Total Failed</p>
                    <p className="font-mono text-display font-semibold text-[#D8493C]">{fusion.failed}</p>
                  </div>
                  <div className="p-4 rounded-xl">
                    <p className="text-caption font-semibold text-[var(--color-text-muted)] uppercase tracking-wider">Total Skipped</p>
                    <p className="font-mono text-display font-semibold text-[var(--color-text-secondary)]">{fusion.skipped}</p>
                  </div>
                </div>
                <div className="flex flex-wrap items-center gap-2 mt-4">
                  <span className="pill border font-medium" style={{ color: VER.strong, background: VER.tint, borderColor: VER.border }}>
                    <Eye size={12} strokeWidth={2} />
                    Fused claims
                  </span>
                  {verificationRuns.map((run) => {
                    const passed = run.cases.reduce((a, c) => a + (c.result?.passed ?? 0), 0);
                    const failed = run.cases.reduce((a, c) => a + (c.result?.failed ?? 0), 0);
                    return (
                      <span key={run.id} className="pill border font-medium font-mono" style={{ color: '#46536B', background: '#F5F7FB', borderColor: '#E3E8F2' }}>
                        {run.id} — {passed} passed · {failed} failed
                      </span>
                    );
                  })}
                </div>
                <div className="mt-4 p-4 rounded-xl border border-[#F5D5D3] bg-white">
                  <div className="flex items-start gap-3">
                    <div className="flex items-center justify-center w-8 h-8 rounded-lg bg-[#D8493C] text-white flex-shrink-0">
                      <AlertTriangle size={15} strokeWidth={2} />
                    </div>
                    <p className="text-body-sm text-[var(--color-text-secondary)] leading-relaxed">
                      0 unauthorized behavior crossed the barrier — 1 survivor intercepted and repaired (F-183).
                      The session-validation mutation gap was closed and re-verified in VER-184-R2.
                    </p>
                  </div>
                </div>
              </div>
            </Section>
          </div>

          {/* Right column — Execute Verification Suite */}
          <div className="lg:col-span-1 space-y-5">
            <div
              className="rounded-2xl border bg-white overflow-hidden shadow-sm"
              style={{ borderColor: runState === 'done' ? '#D4F1E7' : 'var(--color-surface-border)' }}
            >
              <div className="h-1 w-full" style={{ background: VER.active }} />
               <div className="p-5 space-y-3">
                <div>
                  <h2 className="text-heading text-[var(--color-text-primary)]">Execute Verification Suite</h2>
                  <p className="text-body-sm text-[var(--color-text-muted)] mt-0.5">
                    Six independent modules run against the recommended candidate.
                  </p>
                </div>

                <div className="space-y-1">
                  {suiteSteps.map((mod, index) => {
                    const state =
                      runState === 'running' && index === activeStep
                        ? 'running'
                        : runState === 'done' || (runState === 'running' && index < activeStep)
                        ? 'done'
                        : 'pending';
                    return (
                      <div
                        key={index}
                        className={cn(
                          'flex items-center gap-3 p-2.5 rounded-xl border transition-all',
                          state === 'running' ? 'bg-[#FBF6E8] border-[#F2E7CC]' : 'bg-white border-[var(--color-surface-border)]',
                        )}
                      >
                        <div
                          className="flex items-center justify-center w-8 h-8 rounded-lg flex-shrink-0"
                          style={
                            state === 'running'
                              ? { background: VER.active, color: '#FFFFFF' }
                              : state === 'done'
                              ? { background: '#0E9F6E', color: '#FFFFFF' }
                              : { background: `${mod.color}15`, color: mod.color }
                          }
                        >
                          {state === 'running' ? (
                            <div className="w-3.5 h-3.5 border-2 border-white border-t-transparent rounded-full animate-spin" />
                          ) : state === 'done' ? (
                            <CheckCircle2 size={14} strokeWidth={2} />
                          ) : (
                            mod.icon
                          )}
                        </div>
                        <span className="flex-1 text-body-sm font-medium text-[var(--color-text-primary)]">{mod.label}</span>
                        {state === 'running' ? (
                          <span className="text-caption font-mono font-semibold text-[#A9761B] flex-shrink-0">Running…</span>
                        ) : state === 'done' ? (
                          <span className="pill border font-medium flex-shrink-0" style={{ color: '#0E9F6E', background: '#EBF9F4', borderColor: '#D4F1E7' }}>
                            PASSED
                          </span>
                        ) : (
                          <span className="font-mono text-caption text-[var(--color-text-muted)] flex-shrink-0">Pending</span>
                        )}
                      </div>
                    );
                  })}
                </div>

                {runState !== 'done' && (
                  <button
                    onClick={handleRunSuite}
                    disabled={runState === 'running'}
                    className="btn btn--primary w-full"
                    style={{ padding: '0.75rem 1.5rem' }}
                  >
                    <Play size={16} strokeWidth={2} /> Execute Verification Suite
                  </button>
                )}

                {runState === 'done' && (
                  <div>
                    <div className="p-4 rounded-xl bg-[#EBF9F4] border border-[#D4F1E7]">
                      <div className="flex items-center gap-3">
                        <div className="flex items-center justify-center w-9 h-9 rounded-xl bg-[#0E9F6E] text-white">
                          <CheckCircle2 size={18} strokeWidth={2} />
                        </div>
                        <div>
                          <p className="text-body-sm font-bold text-[#14936B]">Verification Suite Complete</p>
                          <p className="text-caption text-[#14936B]">
                            VER-184-R3 recorded — all 6 modules passed, EV-501…EV-506 bound
                          </p>
                        </div>
                      </div>
                    </div>
                    <button className="btn btn--primary w-full mt-3" onClick={() => setActiveTab('Decide')}>
                      Continue to Decide <ChevronRight size={16} strokeWidth={2} />
                    </button>
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>
      </div>
    </JourneyPage>
  );
}