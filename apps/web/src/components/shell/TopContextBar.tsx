'use client';

import { useAppStore } from '@/store/appStore';
import { cn, formatRelativeTime } from '@/lib/design-tokens';
import { stageColors, type JourneyTabId } from '@/lib/design-tokens';
import { StateBadge, type TrustState } from '@/components/ui/StateBadge';
import { lucideReact } from '@/lib/lucide-imports';

const { FolderGit2, GitBranch, FileCode, Shield, Zap, Eye, Lock, AlertCircle, AlertTriangle, Wrench, CheckCircle2, Clock, Settings } = lucideReact;

const trustColors: Record<string, string> = {
  OBSERVED: '#5b6478',
  PROTECTED: '#0e9f6e',
  LOCKED: '#7c5ce0',
  UNVERIFIED: '#c08a17',
  VIOLATED: '#d8493c',
  REPAIR_REQUIRED: '#e07b4a',
  CERTIFIED: '#14936b',
  HISTORICAL: '#8a94a8',
};

const trustBgs: Record<string, string> = {
  OBSERVED: '#f5f7fb',
  PROTECTED: '#ebf9f4',
  LOCKED: '#f2eefc',
  UNVERIFIED: '#fbf6e8',
  VIOLATED: '#fcefee',
  REPAIR_REQUIRED: '#fdf1ea',
  CERTIFIED: '#ecf8f4',
  HISTORICAL: '#eef1f8',
};

export function TopContextBar() {
  const { project, repository, change, constitution, workflow, setActiveTab } = useAppStore();
  const { trustStatus, currentStage } = workflow;
  const stageId: JourneyTabId = currentStage in stageColors ? (currentStage as JourneyTabId) : 'Govern';

  const trustStateLabels: Record<TrustState, string> = {
    OBSERVED: 'OBSERVED',
    PROTECTED: 'PROTECTED',
    LOCKED: 'LOCKED',
    UNVERIFIED: 'UNVERIFIED',
    VIOLATED: 'VIOLATED',
    REPAIR_REQUIRED: 'REPAIR REQUIRED',
    CERTIFIED: 'CERTIFIED',
    HISTORICAL: 'HISTORICAL',
  };

  const trustStateIcons: Record<TrustState, React.ReactNode> = {
    OBSERVED: <Eye size={13} strokeWidth={2} />,
    PROTECTED: <Shield size={13} strokeWidth={2} />,
    LOCKED: <Lock size={13} strokeWidth={2} />,
    UNVERIFIED: <AlertCircle size={13} strokeWidth={2} />,
    VIOLATED: <AlertTriangle size={13} strokeWidth={2} />,
    REPAIR_REQUIRED: <Wrench size={13} strokeWidth={2} />,
    CERTIFIED: <CheckCircle2 size={13} strokeWidth={2} />,
    HISTORICAL: <Clock size={13} strokeWidth={2} />,
  };

  return (
    <header className="h-[60px] sticky top-0 z-30 glass-header border-b border-[var(--color-surface-border)] flex-shrink-0">
      <div className="flex items-center justify-between h-full px-5 gap-3">
        {/* Left: empty — project context now lives in sidebar */}
        <div className="flex items-center gap-2 flex-1 min-w-0" />

        {/* Center: Constitution */}
        {constitution && (
          <div
            className="hidden lg:flex items-center gap-2.5 px-3.5 py-1.5 rounded-full border"
            style={{ background: stageColors.Govern.tint, borderColor: stageColors.Govern.border }}
          >
            <Shield size={15} style={{ color: stageColors.Govern.strong }} className="flex-shrink-0" strokeWidth={2} />
            <div className="leading-tight">
              <div className="flex items-center justify-center gap-1.5">
                <span className="text-[0.72rem] font-semibold" style={{ color: stageColors.Govern.strong }}>{constitution.title}</span>
                <StateBadge state={constitution.status as TrustState} size="sm" variant="pill" />
              </div>
              <p className="text-[0.6rem] mt-0.5" style={{ color: stageColors.Govern.active }}>
                {constitution.protectedCount} protected / {constitution.claimCount} claims
              </p>
            </div>
          </div>
        )}

        {/* Right: Trust + Stage + Settings */}
        <div className="flex items-center gap-2">
          {/* Trust Status Pill */}
          <div
            className="flex items-center gap-2 px-3 py-1.5 rounded-full border"
            style={{
              background: trustBgs[trustStatus] || '#eef1f8',
              borderColor: (trustColors[trustStatus] || '#e3e8f2') + '40',
            }}
          >
            <span style={{ color: trustColors[trustStatus] || '#5b6478' }}>
              {trustStateIcons[trustStatus]}
            </span>
            <div className="hidden sm:block">
              <p className="text-[0.6rem] font-medium text-[var(--color-text-muted)] uppercase tracking-wider">Trust</p>
              <p className="text-[0.75rem] font-bold" style={{ color: trustColors[trustStatus] || '#5b6478' }}>
                {trustStateLabels[trustStatus]}
              </p>
            </div>
          </div>

          {/* Stage Pill — tinted with the current journey stage hue */}
          <div
            className="hidden xl:flex items-center gap-2 px-3 py-1.5 rounded-full border"
            style={{
              background: stageColors[stageId].tint,
              borderColor: stageColors[stageId].border,
            }}
          >
            <Zap size={13} strokeWidth={2} style={{ color: stageColors[stageId].active }} />
            <div>
              <p className="text-[0.6rem] font-medium uppercase tracking-wider" style={{ color: stageColors.Govern.icon }}>Stage</p>
              <p className="text-[0.75rem] font-bold" style={{ color: stageColors[stageId].active }}>{currentStage}</p>
            </div>
          </div>

          {/* Settings */}
          <button
            className="p-2 rounded-full text-[var(--color-text-muted)] hover:text-[var(--color-text-primary)] hover:bg-[var(--color-surface-subtle)] transition-all"
            aria-label="Settings"
          >
            <Settings size={18} strokeWidth={1.75} />
          </button>
        </div>
      </div>
    </header>
  );
}
