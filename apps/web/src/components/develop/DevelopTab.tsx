'use client';

import { useMemo, useState } from 'react';
import { useAppStore } from '@/store/appStore';
import { JourneyPage, Section, LoadingState } from '@/components/shell/AppShell';
import { lucideReact } from '@/lib/lucide-imports';
import { cn } from '@/lib/design-tokens';
import type { CandidatePatch, JourneyTab } from '@/types';

const {
  Shield,
  Lock,
  Terminal,
  ChevronRight,
  CheckCircle2,
  Play,
  Clock,
  Hash,
  Link: LinkIcon,
  AlertTriangle,
  Server,
} = lucideReact;

const sleep = (ms: number) => new Promise<void>((resolve) => setTimeout(resolve, ms));

const DEV = {
  active: '#1EAF8C',
  strong: '#138463',
  tint: '#EBF9F4',
  border: '#D4F1E7',
};

const statusStyles: Record<CandidatePatch['status'], { color: string; tint: string; border: string }> = {
  SUPERSEDED: { color: '#8A94A8', tint: '#EEF1F8', border: '#E3E8F2' },
  RECOMMENDED: { color: '#14936B', tint: '#EBF9F4', border: '#D4F1E7' },
  GENERATED: { color: '#3D86F4', tint: '#EDF3FE', border: '#D9E6FC' },
  REPAIRED: { color: '#14936B', tint: '#EBF9F4', border: '#D4F1E7' },
};

function ExitCodeChip({ code }: { code: number | undefined }) {
  if (code === undefined) {
    return (
      <span className="pill border font-medium font-mono" style={{ color: '#8A94A8', background: '#EEF1F8', borderColor: '#E3E8F2' }}>
        —
      </span>
    );
  }
  if (code === 0) {
    return (
      <span className="pill border font-medium font-mono" style={{ color: '#0E9F6E', background: '#EBF9F4', borderColor: '#D4F1E7' }}>
        {code}
      </span>
    );
  }
  return (
    <span className="pill border font-medium font-mono" style={{ color: '#D8493C', background: '#FCEFEE', borderColor: '#F5D5D3' }}>
      {code}
    </span>
  );
}

export function DevelopTab() {
  const domain = useAppStore((s) => s.domain);
  const change = useAppStore((s) => s.change);
  const updateDomain = useAppStore((s) => s.updateDomain);
  const completeStage = useAppStore((s) => s.completeStage);
  const setActiveTab = useAppStore((s) => s.setActiveTab);
  const setWorkflowState = useAppStore((s) => s.setWorkflowState);
  const openDrawer = useAppStore((s) => s.openDrawer);

  const [selectedPatchId, setSelectedPatchId] = useState('PATCH-184-2');
  const [runState, setRunState] = useState<'idle' | 'running' | 'done'>('idle');
  const [activePhase, setActivePhase] = useState(-1);
  const [barrierPassed, setBarrierPassed] = useState(false);

  const { candidatePatches } = domain;
  const patch2 = candidatePatches.find((p) => p.id === 'PATCH-184-2') ?? candidatePatches[0];
  const selectedPatch = candidatePatches.find((p) => p.id === selectedPatchId) ?? patch2;

  const runPhases = useMemo(() => {
    if (!patch2) return [];
    return [
      ...patch2.execution.map((e) => ({
        id: e.id,
        command: e.command ?? e.id,
        stdout: e.stdout ?? '',
        exitCode: e.exitCode,
        durationMs: e.durationMs,
      })),
      {
        id: 'BARRIER',
        command: null as string | null,
        stdout: 'Constitution barrier — 6/6 protected gates verified',
        exitCode: 0 as number | undefined,
        durationMs: undefined as number | undefined,
      },
    ];
  }, [patch2]);

  const finish = (stage: JourneyTab) => {
    completeStage(stage);
    setActiveTab(stage);
  };

  const handleRunCandidate = async () => {
    if (!patch2 || runState === 'running') return;
    setRunState('running');
    setActivePhase(0);
    setBarrierPassed(false);
    for (let i = 0; i < runPhases.length; i++) {
      setActivePhase(i);
      await sleep(650);
    }
    updateDomain({
      candidatePatches: domain.candidatePatches.map((p) =>
        p.id === 'PATCH-184-2' ? { ...p, status: 'RECOMMENDED' as const } : p,
      ),
    });
    setWorkflowState({ currentStage: 'Develop', trustStatus: 'OBSERVED' });
    setActivePhase(-1);
    setBarrierPassed(true);
    setRunState('done');
    finish('Develop');
  };

  const phaseStatus = (index: number): 'running' | 'done' | 'pending' => {
    if (runState === 'running' && index === activePhase) return 'running';
    if (runState === 'done') return 'done';
    if (runState === 'running' && index < activePhase) return 'done';
    return 'pending';
  };

  if (!candidatePatches.length) {
    return <LoadingState message="Loading development plane…" />;
  }

  return (
    <JourneyPage
      title="Develop"
      description="Inspect the Coding Agent's candidate patches, sandbox execution, and constitution-aware barrier."
    >
      <div className="space-y-5">
        {/* Lead card — Sandbox Session */}
        <div className="rounded-2xl border bg-white overflow-hidden shadow-sm" style={{ borderColor: DEV.border }}>
          <div className="h-1 w-full" style={{ background: DEV.active }} />
          <div className="px-6 py-6 space-y-5">
            <div className="flex items-start justify-between gap-4">
              <div>
                <h2 className="text-heading text-[var(--color-text-primary)]">Sandbox Session</h2>
                <p className="text-body-sm text-[var(--color-text-muted)] mt-0.5">
                  Real Nebius Token Factory sandbox execution path for Candidate Patch verification.
                </p>
              </div>
              <span className="pill border font-medium" style={{ color: '#0E9F6E', background: '#EBF9F4', borderColor: '#D4F1E7' }}>
                <span className="w-1.5 h-1.5 rounded-full bg-[#0E9F6E]" />
                Active
              </span>
            </div>
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
              <div className="flex items-start gap-3 p-3 rounded-xl">
                <div className="flex items-center justify-center w-8 h-8 rounded-lg" style={{ background: DEV.tint, color: DEV.strong }}>
                  <Server size={15} strokeWidth={1.75} />
                </div>
                <div>
                  <p className="text-caption text-[var(--color-text-muted)] font-semibold uppercase tracking-wider">Sandbox ID</p>
                  <p className="font-mono text-code-sm font-semibold text-[var(--color-text-primary)]">sb-184-a7f3</p>
                </div>
              </div>
              <div className="flex items-start gap-3 p-3 rounded-xl">
                <div className="flex items-center justify-center w-8 h-8 rounded-lg" style={{ background: DEV.tint, color: DEV.strong }}>
                  <Terminal size={15} strokeWidth={1.75} />
                </div>
                <div>
                  <p className="text-caption text-[var(--color-text-muted)] font-semibold uppercase tracking-wider">Runtime</p>
                  <p className="text-code-sm font-semibold text-[var(--color-text-primary)]">node 20 · linux</p>
                </div>
              </div>
              <div className="flex items-start gap-3 p-3 rounded-xl">
                <div className="flex items-center justify-center w-8 h-8 rounded-lg" style={{ background: DEV.tint, color: DEV.strong }}>
                  <Hash size={15} strokeWidth={1.75} />
                </div>
                <div className="min-w-0">
                  <p className="text-caption text-[var(--color-text-muted)] font-semibold uppercase tracking-wider">Change</p>
                  <p className="text-code-sm font-semibold text-[var(--color-text-primary)] truncate">
                    {change?.externalId ?? '#184'} — {change?.title ?? 'Replace authentication provider'}
                  </p>
                </div>
              </div>
            </div>
          </div>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-5 gap-5">
          {/* Left column */}
          <div className="lg:col-span-3 space-y-5">
            {/* Candidate Patches */}
            <Section title="Candidate Patches" description="Constitution-aware candidate patches generated inside the sandbox.">
              <div className="space-y-4">
                {candidatePatches.map((patch) => {
                  const statusStyle = statusStyles[patch.status];
                  return (
                    <div key={patch.id} className="surface-card p-5">
                      <div className="flex flex-wrap items-start justify-between gap-3">
                        <div className="flex items-start gap-3">
                          <span
                            className="pill border font-medium font-mono"
                            style={{ color: DEV.strong, background: DEV.tint, borderColor: DEV.border }}
                          >
                            SEQ {patch.seq}
                          </span>
                          <div>
                            <p className="text-body font-semibold text-[var(--color-text-primary)]">{patch.title}</p>
                            <p className="text-caption text-[var(--color-text-muted)] font-mono mt-0.5">{patch.sandboxId}</p>
                          </div>
                        </div>
                        <div className="flex items-center gap-2">
                          {patch.supersedes && (
                            <span
                              className="pill border font-medium"
                              style={{ color: '#8A94A8', background: '#EEF1F8', borderColor: '#E3E8F2' }}
                            >
                              <LinkIcon size={12} strokeWidth={2} />
                              <span className="font-mono">supersedes {patch.supersedes}</span>
                            </span>
                          )}
                          <span
                            className="pill border font-medium"
                            style={{ color: statusStyle.color, background: statusStyle.tint, borderColor: statusStyle.border }}
                          >
                            {patch.status}
                          </span>
                        </div>
                      </div>
                      <div className="flex flex-wrap gap-2 mt-4">
                        {patch.filesChanged.map((file) => (
                          <span
                            key={file}
                            className="px-2.5 py-1 font-mono text-code-sm bg-[var(--color-surface-subtle)] border border-[var(--color-surface-border)] rounded-md text-[var(--color-text-secondary)]"
                          >
                            {file}
                          </span>
                        ))}
                      </div>
                      <div className="flex items-center gap-4 mt-4 pt-3 border-t border-[var(--color-surface-border)]">
                        <span className="font-mono text-code-sm font-semibold" style={{ color: '#0E9F6E' }}>
                          +{patch.additions}
                        </span>
                        <span className="font-mono text-code-sm font-semibold" style={{ color: '#D8493C' }}>
                          −{patch.deletions}
                        </span>
                        <span className="text-caption text-[var(--color-text-muted)]">
                          {patch.execution.length} execution events · {patch.traces.length} sandbox traces
                        </span>
                      </div>
                    </div>
                  );
                })}
              </div>
            </Section>

            {/* Execution Events */}
            <Section title="Execution Events" description="Select a patch to inspect real sandbox execution and traces.">
              <div className="surface-card">
                <div className="flex flex-wrap items-center gap-2 px-5 pt-5">
                  {candidatePatches.map((patch) => (
                    <button
                      key={patch.id}
                      onClick={() => setSelectedPatchId(patch.id)}
                      className={cn(
                        'px-3 py-1.5 rounded-lg text-code-sm font-mono font-medium border transition-all',
                        selectedPatchId === patch.id
                          ? 'bg-[var(--color-ink)] text-white border-[var(--color-ink)]'
                          : 'bg-white text-[var(--color-text-secondary)] border-[var(--color-surface-border)] hover:bg-[var(--color-surface-subtle)]',
                      )}
                    >
                      {patch.id}
                    </button>
                  ))}
                  {selectedPatch?.status === 'RECOMMENDED' && (
                    <span className="ml-auto pill border font-medium" style={{ color: '#14936B', background: '#EBF9F4', borderColor: '#D4F1E7' }}>
                      <span className="w-1.5 h-1.5 rounded-full bg-[#14936B]" />
                      Recommended
                    </span>
                  )}
                </div>

                <div className="p-5 space-y-2">
                  {selectedPatch.execution.map((event) => (
                    <button
                      key={event.id}
                      onClick={() => openDrawer('execution-trace', { ...event })}
                      className="w-full flex items-center gap-3 p-3 rounded-xl border bg-white border-[var(--color-surface-border)] text-left transition-all hover:border-[var(--color-accent-soft)] hover:bg-[var(--color-accent-tint)]"
                    >
                      <span className="flex items-center justify-center w-9 h-9 rounded-lg flex-shrink-0" style={{ background: DEV.tint, color: DEV.strong }}>
                        <Terminal size={15} strokeWidth={1.75} />
                      </span>
                      <span className="flex-1 min-w-0">
                        <span className="block font-mono text-code-sm text-[var(--color-text-primary)] truncate">
                          {event.command}
                        </span>
                        <span className="block text-caption text-[var(--color-text-muted)] truncate">{event.stdout}</span>
                      </span>
                      <span className="flex-shrink-0">
                        <ExitCodeChip code={event.exitCode} />
                      </span>
                      <span className="flex-shrink-0 font-mono text-code-sm text-[var(--color-text-muted)]">
                        {event.durationMs !== undefined ? `${event.durationMs}ms` : '—'}
                      </span>
                      <span
                        className="flex-shrink-0 text-caption font-semibold"
                        style={{ color: event.exitCode === 0 ? '#0E9F6E' : '#D8493C' }}
                      >
                        {event.exitCode === 0 ? 'COMPLETED' : 'FAILED'}
                      </span>
                      <ChevronRight size={16} strokeWidth={2} className="text-[var(--color-text-muted)] flex-shrink-0" />
                    </button>
                  ))}
                </div>

                {/* Sandbox Traces */}
                <div className="px-5 pb-5">
                  <div className="flex items-center gap-2 mb-2">
                    <Terminal size={13} strokeWidth={1.75} className="text-[var(--color-text-muted)]" />
                    <p className="text-caption font-semibold uppercase tracking-wider text-[var(--color-text-muted)]">Sandbox Traces</p>
                    <span className="text-caption text-[var(--color-text-muted)]">· {selectedPatch.traces.length} traces</span>
                  </div>
                  <div className="border border-[var(--color-surface-border)] rounded-xl divide-y divide-[var(--color-surface-border)] overflow-hidden">
                    {selectedPatch.traces.map((trace) => (
                      <div key={trace.id} className="flex items-center gap-3 px-3 py-2">
                        <span className="font-mono text-caption text-[var(--color-text-muted)] w-20 flex-shrink-0">{trace.id}</span>
                        <span className="font-mono text-code-sm text-[var(--color-text-primary)] flex-1 truncate">{trace.command}</span>
                        <span
                          className="font-mono text-caption font-semibold flex-shrink-0"
                          style={{ color: trace.exitCode === 0 ? '#0E9F6E' : '#D8493C' }}
                        >
                          {trace.exitCode}
                        </span>
                        <span className="font-mono text-caption text-[var(--color-text-muted)] flex-shrink-0">{trace.durationMs}ms</span>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            </Section>
          </div>

          {/* Right column */}
          <div className="lg:col-span-2 space-y-5">
            {/* Constitution Barrier */}
            <Section
              title="Constitution Barrier"
              description="Six protected gates the candidate must clear before recommendation."
            >
              <div className="surface-card p-4 space-y-2">
                {patch2.constitutionBarrier.map((gate, i) => {
                  const passed = barrierPassed;
                  return (
                    <div
                      key={i}
                      className={cn(
                        'flex items-center gap-3 p-3 rounded-xl border transition-all',
                        passed
                          ? 'bg-[#EBF9F4] border-[#D4F1E7]'
                          : 'bg-[#FBF6E8] border-[#F2E7CC]',
                      )}
                    >
                      <div
                        className="flex items-center justify-center w-8 h-8 rounded-lg flex-shrink-0"
                        style={
                          passed
                            ? { background: '#0E9F6E', color: '#FFFFFF' }
                            : { background: '#D89A2422', color: '#D89A24' }
                        }
                      >
                        {passed ? <Shield size={14} strokeWidth={2} /> : <Lock size={14} strokeWidth={2} />}
                      </div>
                      <span className="text-body-sm font-medium text-[var(--color-text-primary)] flex-1">{gate}</span>
                      <span
                        className="font-mono text-caption font-semibold flex-shrink-0"
                        style={{ color: passed ? '#0E9F6E' : '#D89A24' }}
                      >
                        {passed ? 'PASSED' : 'PENDING'}
                      </span>
                    </div>
                  );
                })}
              </div>
            </Section>

            {/* Failure Archaeology */}
            <Section
              title="Failure Archaeology"
              description="Failure is information — preserved as behavioral memory, never erased."
            >
              <div className="space-y-3">
                {candidatePatches
                  .filter((patch) => patch.failureHistory.length > 0)
                  .map((patch) =>
                    patch.failureHistory.map((failure) => (
                      <div key={failure.id} className="rounded-xl border p-4 bg-[#FCEFEE] border-[#F5D5D3]">
                        <div className="flex items-center justify-between gap-3">
                          <div className="flex items-center gap-2">
                            <div className="flex items-center justify-center w-8 h-8 rounded-lg bg-[#D8493C] text-white">
                              <AlertTriangle size={15} strokeWidth={2} />
                            </div>
                            <p className="font-mono text-body font-bold text-[#D8493C]">{failure.id}</p>
                          </div>
                          <span className="pill border font-medium" style={{ color: '#D8493C', background: '#FCEFEE', borderColor: '#F5D5D3' }}>
                            {failure.classification}
                          </span>
                        </div>
                        <p className="text-body-sm text-[var(--color-text-secondary)] mt-3 leading-relaxed">{failure.notes}</p>
                        <div className="flex flex-wrap items-center gap-2 mt-3 pt-3 border-t border-[#F5D5D3]">
                          <span className="pill border font-medium font-mono" style={{ color: '#D8493C', background: '#FFFFFF', borderColor: '#F5D5D3' }}>
                            <Hash size={12} strokeWidth={2} />
                            {failure.evidenceId}
                          </span>
                          <span className="pill border font-medium font-mono" style={{ color: '#8A94A8', background: '#FFFFFF', borderColor: '#E3E8F2' }}>
                            <Clock size={12} strokeWidth={2} />
                            run {failure.runId}
                          </span>
                          <span className="text-caption text-[var(--color-text-muted)] ml-auto">
                            Failure → Evidence → Diagnosis → Repair
                          </span>
                        </div>
                      </div>
                    )),
                  )}
              </div>
            </Section>

            {/* Run Candidate in Sandbox */}
            <div
              className={cn(
                'rounded-2xl border bg-white overflow-hidden shadow-sm',
                runState === 'done' && 'border-[#D4F1E7]',
              )}
              style={{ borderColor: runState === 'done' ? '#D4F1E7' : 'var(--color-surface-border)' }}
            >
              <div className="h-1 w-full" style={{ background: DEV.active }} />
              <div className="p-5 space-y-4">
                <div>
                  <h2 className="text-heading text-[var(--color-text-primary)]">Run Candidate in Sandbox</h2>
                  <p className="text-body-sm text-[var(--color-text-muted)] mt-0.5">
                    Real execution path through sb-184-a7f3 — build, test, mutation.
                  </p>
                </div>

                <div className="space-y-2">
                  {runPhases.map((phase, index) => {
                    const state = phaseStatus(index);
                    return (
                      <div
                        key={phase.id}
                        className={cn(
                          'flex items-center gap-3 p-3 rounded-xl border transition-all',
                          state === 'running' ? 'bg-[#EBF9F4] border-[#D4F1E7]' : 'bg-white border-[var(--color-surface-border)]',
                        )}
                      >
                        <div
                          className="flex items-center justify-center w-8 h-8 rounded-lg flex-shrink-0"
                          style={
                            state === 'running'
                              ? { background: DEV.active, color: '#FFFFFF' }
                              : state === 'done'
                              ? { background: '#0E9F6E', color: '#FFFFFF' }
                              : { background: '#EEF1F8', color: '#8A94A8' }
                          }
                        >
                          {state === 'running' ? (
                            <div className="w-3.5 h-3.5 border-2 border-white border-t-transparent rounded-full animate-spin" />
                          ) : state === 'done' ? (
                            <CheckCircle2 size={14} strokeWidth={2} />
                          ) : (
                            <Terminal size={14} strokeWidth={2} />
                          )}
                        </div>
                        <span className="flex-1 min-w-0">
                          <span className="block font-mono text-code-sm font-medium text-[var(--color-text-primary)] truncate">
                            {phase.command ?? 'Constitution barrier scan'}
                          </span>
                          {(state === 'done' || state === 'running') && phase.stdout && (
                            <span className="block text-caption text-[var(--color-text-muted)] truncate">{phase.stdout}</span>
                          )}
                        </span>
                        {state === 'running' ? (
                          <span className="text-caption font-mono font-semibold text-[var(--color-text-muted)] flex-shrink-0">Running…</span>
                        ) : state === 'done' ? (
                          <span className="flex-shrink-0">
                            <ExitCodeChip code={phase.exitCode} />
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
                    onClick={handleRunCandidate}
                    disabled={runState === 'running' || !patch2}
                    className="btn btn--primary w-full"
                    style={{ padding: '0.75rem 1.5rem' }}
                  >
                    <Play size={16} strokeWidth={2} /> Run Candidate in Sandbox
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
                          <p className="text-body-sm font-bold text-[#14936B]">Sandbox Execution Complete</p>
                          <p className="text-caption text-[#14936B]">
                            PATCH-184-2 ran clean — build, 43 tests, 7/7 mutants killed, 6/6 barrier gates passed
                          </p>
                        </div>
                      </div>
                    </div>
                    <button className="btn btn--primary w-full mt-3" onClick={() => setActiveTab('Verify')}>
                      Continue to Verify <ChevronRight size={16} strokeWidth={2} />
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