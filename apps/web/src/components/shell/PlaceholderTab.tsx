'use client';

import { JourneyPage } from './AppShell';
import { lucideReact } from '@/lib/lucide-imports';
import { stageColors } from '@/lib/design-tokens';

interface PlaceholderTabProps {
  tab: string;
  description: string;
  icon: React.ReactNode;
}

const tabColorMap: Record<string, { border: string; text: string; bg: string }> = {
  Define:   { border: stageColors.Define.border,  text: stageColors.Define.active,  bg: stageColors.Define.tint },
  Analyze:  { border: stageColors.Analyze.border, text: stageColors.Analyze.active, bg: stageColors.Analyze.tint },
  Develop:  { border: stageColors.Develop.border, text: stageColors.Develop.active, bg: stageColors.Develop.tint },
  Verify:   { border: stageColors.Verify.border,  text: stageColors.Verify.active,  bg: stageColors.Verify.tint },
  Decide:   { border: stageColors.Decide.border,  text: stageColors.Decide.active,  bg: stageColors.Decide.tint },
  Certify:  { border: stageColors.Certify.border, text: stageColors.Certify.active, bg: stageColors.Certify.tint },
};

const phaseDescriptions: Record<string, { phase: string; detail: string }> = {
  Define:   { phase: 'Phase 7', detail: 'Normalize human requests into objective/constraints/acceptance criteria and compile intent across five dimensions.' },
  Analyze:  { phase: 'Phase 8', detail: 'Map proposed changes against the behavioral graph to identify semantic impact surfaces and risk zones.' },
  Develop:  { phase: 'Phase 9', detail: 'Generate candidate patches within the sandbox, evidence-backed and constitution-aware.' },
  Verify:   { phase: 'Phase 10', detail: 'Run independent verification modules — static analysis, differential execution, ghost replay, adversarial tests.' },
  Decide:   { phase: 'Phase 11', detail: 'Evaluate behavioral deltas, verify intent alignment, and drive the repair loop when required.' },
  Certify:  { phase: 'Phase 12', detail: 'Bind evidence to the certificate, seal the immutable trust record, and close the behavioral memory loop.' },
};

export function PlaceholderTab({ tab, description, icon }: PlaceholderTabProps) {
  const colors = tabColorMap[tab] || tabColorMap.Define;
  const phase = phaseDescriptions[tab];

  return (
    <JourneyPage title={tab} description={description}>
      {/* Hero Section — flat, structured, professional */}
      <div className="rounded-2xl border bg-white overflow-hidden shadow-sm" style={{ borderColor: colors.border }}>
        {/* Thin colored leader line */}
        <div className="h-1 w-full" style={{ background: colors.bg }} />

        <div className="px-10 py-10 text-center">
          {/* Icon */}
          <div
            className="inline-flex items-center justify-center w-16 h-16 rounded-2xl mb-6"
            style={{ background: colors.bg, color: colors.text }}
          >
            {icon}
          </div>

          {/* Title */}
          <h2 className="text-[1.5rem] font-bold text-[var(--color-text-primary)] tracking-tight font-display">
            {tab} — Coming Soon
          </h2>

          {/* Description */}
          <p className="text-[0.875rem] text-[var(--color-text-secondary)] mt-2 max-w-lg mx-auto leading-relaxed">
            This journey tab will be implemented in a future phase. The navigation architecture is ready for extension.
          </p>

          {/* Phase detail */}
          {phase && (
            <div className="flex items-center justify-center gap-2 mt-5">
              <span
                className="pill border font-medium"
                style={{ background: colors.bg, color: colors.text, borderColor: colors.border }}
              >
                {phase.phase}
              </span>
              <span className="text-[0.75rem] text-[var(--color-text-muted)] max-w-md text-left">
                {phase.detail}
              </span>
            </div>
          )}
        </div>

        {/* Status bar */}
        <div className="flex items-center justify-center gap-2 border-t border-[var(--color-surface-border)] bg-[var(--color-surface-subtle)] px-6 py-3">
          <span className="pill bg-white text-[var(--color-text-muted)] border border-[var(--color-surface-border)]">
            <span className="w-1.5 h-1.5 rounded-full bg-[var(--color-state-pending)]" />
            Pending
          </span>
          <span className="pill bg-white text-[var(--color-text-muted)] border border-[var(--color-surface-border)]">
            Navigation Architecture Ready
          </span>
        </div>
      </div>

      {/* Feature cards preview */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {[
          { label: 'Constitution-Aware', desc: 'All changes respect the behavioral constitution', color: '#7c5ce0', bg: '#f2eefc', border: '#e3dbf6' },
          { label: 'Evidence-Backed', desc: 'Every claim bound to real execution traces', color: '#0e9f6e', bg: '#ebf9f4', border: '#d4f1e7' },
          { label: 'Independently Verified', desc: 'Multi-module verification with fused evidence', color: '#3d86f4', bg: '#edf3fe', border: '#d9e6fc' },
        ].map((feat, i) => (
          <div
            key={i}
            className="rounded-xl border p-4 text-center"
            style={{ borderColor: feat.border, background: feat.bg }}
          >
            <p className="text-[0.8rem] font-bold" style={{ color: feat.color }}>{feat.label}</p>
            <p className="text-[0.75rem] text-[var(--color-text-muted)] mt-1">{feat.desc}</p>
          </div>
        ))}
      </div>
    </JourneyPage>
  );
}