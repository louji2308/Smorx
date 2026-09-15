'use client';

import { useState } from 'react';
import { useAppStore } from '@/store/appStore';
import { Section } from '@/components/shell/AppShell';
import { StateBadge } from '@/components/ui/StateBadge';
import { lucideReact } from '@/lib/lucide-imports';
import { cn } from '@/lib/design-tokens';
import type { TrustState } from '@/types';

const { Play, Search, Database, GitBranch, Terminal, FlaskConical, AlertTriangle, Clock, CheckCircle2, ChevronRight, Shield, Zap, Ghost, FileText } = lucideReact;

const statColors = [
  { label: 'Behaviors',     color: 'var(--color-ink)', tint: 'var(--color-ink-tint)', border: 'var(--color-ink-soft)' },
  { label: 'Invariants',    color: '#0e9f6e', tint: '#ebf9f4', border: '#d4f1e7' },
  { label: 'Incidents',     color: '#d8493c', tint: '#fcefee', border: '#f5d5d3' },
  { label: 'Dependencies',  color: '#c08a17', tint: '#fbf6e8', border: '#f2e7cc' },
  { label: 'Couplings',     color: '#7c5ce0', tint: '#f2eefc', border: '#e3dbf6' },
  { label: 'Risk Zones',    color: '#e98c4e', tint: '#fdf1ea', border: '#f8decf' },
  { label: 'Ghosts',        color: '#7c5ce0', tint: '#f2eefc', border: '#e3dbf6' },
  { label: 'Evidence Items', color: '#3d86f4', tint: '#edf3fe', border: '#d9e6fc' },
];

export function ArchaeologyLaunch() {
  const { project, repository, change, constitution, setWorkflowState, setActiveTab, completeStage } = useAppStore();
  const [isRunning, setIsRunning] = useState(false);
  const [progress, setProgress] = useState(0);
  const [currentStep, setCurrentStep] = useState('');
  const [results, setResults] = useState<ArchaeologyResults | null>(null);

  const steps = [
    { id: 'source', label: 'Source Analysis', icon: <Search size={15} strokeWidth={1.75} />, color: 'var(--color-ink)' },
    { id: 'git', label: 'Git History', icon: <GitBranch size={15} strokeWidth={1.75} />, color: '#7c5ce0' },
    { id: 'tests', label: 'Test Analysis', icon: <FlaskConical size={15} strokeWidth={1.75} />, color: '#0e9f6e' },
    { id: 'deps', label: 'Dependencies', icon: <Database size={15} strokeWidth={1.75} />, color: '#c08a17' },
    { id: 'runtime', label: 'Runtime', icon: <Terminal size={15} strokeWidth={1.75} />, color: '#3d86f4' },
    { id: 'incidents', label: 'Incidents', icon: <AlertTriangle size={15} strokeWidth={1.75} />, color: '#d8493c' },
  ];

  const handleRunArchaeology = async () => {
    setIsRunning(true);
    setProgress(0);
    setResults(null);
    for (let i = 0; i < steps.length; i++) {
      setCurrentStep(steps[i].id);
      setProgress(((i + 1) / steps.length) * 100);
      await new Promise(resolve => setTimeout(resolve, 800));
    }
    const mockResults: ArchaeologyResults = {
      behaviors: 24, invariants: 18, incidents: 7, dependencies: 42, couplings: 15, riskZones: 8, ghosts: 3, evidence: 156,
    };
    setResults(mockResults);
    setIsRunning(false);
    setCurrentStep('');
    setWorkflowState({ currentStage: 'Discover', trustStatus: 'OBSERVED' });
    completeStage('Discover');
    setTimeout(() => setActiveTab('Discover'), 1500);
  };

  if (results) {
    return (
      <div className="space-y-5">
        <Section title="Archaeology Complete" description="Evidence collected and behavioral findings generated.">
          <div className="flex justify-end">
            <button onClick={() => setResults(null)} className="btn btn--secondary btn-sm">Run Again</button>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-3">
            {statColors.map((s, i) => {
              const val = Object.values(results)[i];
              return (
                <div key={i} className="rounded-xl border p-4 transition-all hover:shadow-sm" style={{ borderColor: s.border, background: s.tint }}>
                  <p className="text-[0.65rem] font-semibold uppercase tracking-wider" style={{ color: s.color + 'aa' }}>{s.label}</p>
                  <p className="text-[1.75rem] font-semibold mt-1 font-mono" style={{ color: s.color }}>{val}</p>
                </div>
              );
            })}
          </div>
          <div className="mt-5 flex gap-3">
            <button onClick={() => setActiveTab('Discover')} className="btn btn--primary flex-1">
              <ChevronRight size={16} strokeWidth={2} /> Explore Evidence
            </button>
            <button onClick={() => setActiveTab('Discover')} className="btn btn--secondary flex-1">
              View Knowledge Graph
            </button>
          </div>
        </Section>
      </div>
    );
  }

  return (
    <div className="space-y-5">
      <Section title="Software Archaeology" description="Reconstruct behavioral memory from source, history, tests, dependencies, runtime observations, and incidents.">
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-5">
          <div className="lg:col-span-2 space-y-5">
            {/* Project Context */}
            <div className="surface-card p-5">
              <header className="flex items-center justify-between mb-4">
                <h2 className="text-[0.9rem] font-bold text-[var(--color-text-primary)]">Project Context</h2>
                <StateBadge state={constitution?.status as TrustState || 'HISTORICAL'} size="sm" />
              </header>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                {[
                  { label: 'Project', value: project?.name || 'Not connected', color: '#5b66e8' },
                  { label: 'Repository', value: repository?.name || 'Not connected', color: '#7c5ce0', mono: true },
                  { label: 'Change', value: change?.externalId || change?.title || 'Not defined', color: '#3d86f4' },
                  { label: 'Constitution', value: constitution?.title || 'Not activated', color: '#0e9f6e' },
                ].map((item, i) => (
                  <div key={i} className="flex items-start gap-3 p-3 rounded-xl">
                    <div className="w-1 h-8 rounded-full mt-0.5" style={{ background: item.color }} />
                    <div>
                      <p className="text-[0.65rem] font-semibold text-[var(--color-text-muted)] uppercase tracking-wider">{item.label}</p>
                      <p className={`text-[0.8rem] font-semibold text-[var(--color-text-primary)] ${item.mono ? 'font-mono' : ''} truncate max-w-[200px]`}>{item.value}</p>
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {/* Readiness */}
            <div className="surface-card p-5">
              <h2 className="text-[0.9rem] font-bold text-[var(--color-text-primary)] mb-3">Archaeology Readiness</h2>
              <div className="space-y-2">
                {[
                  { label: 'Repository Connected', status: 'ready', detail: repository?.url, color: '#0e9f6e' },
                  { label: 'Git History Available', status: 'ready', detail: 'Full history accessible', color: '#0e9f6e' },
                  { label: 'Test Suite Detected', status: 'ready', detail: 'Jest/Pytest found', color: '#0e9f6e' },
                  { label: 'Dependencies Resolved', status: 'ready', detail: 'package.json / requirements.txt', color: '#0e9f6e' },
                  { label: 'Runtime Instrumentation', status: 'pending', detail: 'Requires sandbox', color: '#d89a24' },
                  { label: 'Incident Database', status: 'partial', detail: '7 historical incidents', color: '#8a94a8' },
                ].map((check, i) => (
                  <div key={i} className="flex items-center justify-between p-3 rounded-xl">
                    <div className="flex items-center gap-3">
                      <div className="flex items-center justify-center w-7 h-7 rounded-lg" style={{ background: check.color + '15', color: check.color }}>
                        {check.status === 'ready' ? <CheckCircle2 size={14} strokeWidth={2} /> : check.status === 'pending' ? <Clock size={14} strokeWidth={2} /> : <Search size={14} strokeWidth={2} />}
                      </div>
                      <span className="text-[0.8rem] font-semibold text-[var(--color-text-primary)]">{check.label}</span>
                    </div>
                    <span className="text-[0.7rem] text-[var(--color-text-muted)]">{check.detail}</span>
                  </div>
                ))}
              </div>
            </div>
          </div>

          {/* Right Column */}
          <div className="space-y-5">
            {/* Investigation Scope */}
            <div className="surface-card p-5">
              <h2 className="text-[0.9rem] font-bold text-[var(--color-text-primary)] mb-3">Investigation Scope</h2>
              <p className="text-[0.8rem] text-[var(--color-text-secondary)] mb-4 leading-relaxed">
                Six independent investigation streams producing evidence-backed behavioral findings.
              </p>
              <div className="space-y-2">
                {steps.map((step) => (
                  <div
                    key={step.id}
                    className={cn(
                      'flex items-center gap-3 p-3 rounded-xl border transition-all',
                      isRunning && currentStep === step.id
                        ? 'border-[var(--color-accent-soft)] bg-[var(--color-accent-tint)]'
                        : results
                        ? 'border-[#d4f1e7] bg-[#ebf9f4]'
                        : 'border-transparent',
                    )}
                  >
                    <div
                      className="flex items-center justify-center w-8 h-8 rounded-lg flex-shrink-0"
                      style={
                        isRunning && currentStep === step.id
                          ? { background: step.color, color: 'white' }
                          : results
                          ? { background: '#0e9f6e', color: 'white' }
                          : { background: step.color + '15', color: step.color }
                      }
                    >
                      {isRunning && currentStep === step.id ? (
                        <div className="w-3.5 h-3.5 border-2 border-white border-t-transparent rounded-full animate-spin" />
                      ) : results ? (
                        <CheckCircle2 size={14} strokeWidth={2} />
                      ) : (
                        step.icon
                      )}
                    </div>
                    <span className="text-[0.8rem] font-semibold text-[var(--color-text-primary)]">{step.label}</span>
                    {isRunning && currentStep === step.id && (
                      <span className="text-[0.65rem] font-mono text-[var(--color-text-muted)] ml-auto">Running...</span>
                    )}
                    {results && (
                      <span className="text-[0.65rem] font-mono text-[#0e9f6e] ml-auto">Done</span>
                    )}
                  </div>
                ))}
              </div>

              {/* Progress Bar */}
              {isRunning && (
                <div className="mt-4">
                  <div className="flex items-center justify-between text-[0.7rem] font-medium mb-1.5">
                    <span className="text-[var(--color-text-secondary)]">Progress</span>
                    <span className="font-mono text-[var(--color-ink)]">{Math.round(progress)}%</span>
                  </div>
                  <div className="h-2 bg-[var(--color-accent-soft)] rounded-full overflow-hidden">
                    <div className="h-full bg-[var(--color-ink)] rounded-full transition-all duration-300" style={{ width: `${progress}%` }} />
                  </div>
                </div>
              )}

              {/* Run Button */}
              {!isRunning && !results && (
                <button onClick={handleRunArchaeology} className="btn btn--primary w-full mt-4" style={{ padding: '0.875rem 1.5rem' }}>
                  <Play size={18} strokeWidth={2} /> Run Software Archaeology
                </button>
              )}

              {/* Success Banner */}
              {results && (
                <div className="mt-4 p-4 rounded-xl bg-[#ebf9f4] border border-[#d4f1e7]">
                  <div className="flex items-center gap-3">
                    <div className="flex items-center justify-center w-9 h-9 rounded-xl bg-[#0e9f6e] text-white">
                      <CheckCircle2 size={18} strokeWidth={2} />
                    </div>
                    <div>
                      <p className="text-[0.8rem] font-bold text-[#14936b]">Archaeology Complete</p>
                      <p className="text-[0.7rem] text-[#14936b]">Evidence collected and behavioral findings generated</p>
                    </div>
                  </div>
                </div>
              )}
            </div>

            {/* What Will Be Investigated */}
            <div className="surface-card p-5">
              <h2 className="text-[0.9rem] font-bold text-[var(--color-text-primary)] mb-3">What Will Be Investigated</h2>
              <div className="grid grid-cols-1 gap-2">
                {[
                  { text: 'Source code structure and patterns', color: '#5b66e8' },
                  { text: 'Git commit history and evolution', color: '#7c5ce0' },
                  { text: 'Test coverage and behavior specs', color: '#0e9f6e' },
                  { text: 'Dependency graph and version risks', color: '#c08a17' },
                  { text: 'Runtime behavior and performance', color: '#3d86f4' },
                  { text: 'Historical incidents and failures', color: '#d8493c' },
                ].map((item, i) => (
                  <div key={i} className="flex items-center gap-2.5 p-2.5 rounded-lg">
                    <div className="w-1.5 h-1.5 rounded-full flex-shrink-0" style={{ background: item.color }} />
                    <span className="text-[0.75rem] font-medium text-[var(--color-text-secondary)]">{item.text}</span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      </Section>
    </div>
  );
}

interface ArchaeologyResults {
  behaviors: number;
  invariants: number;
  incidents: number;
  dependencies: number;
  couplings: number;
  riskZones: number;
  ghosts: number;
  evidence: number;
}
