'use client';

import { useAppStore } from '@/store/appStore';
import { cn } from '@/lib/design-tokens';
import { journeyTabs, stageColors, brandColor, type JourneyTabId, isTabAvailable } from '@/lib/design-tokens';
import { lucideReact } from '@/lib/lucide-imports';

const { Search, Shield, Edit, GitBranch, Code, CheckCircle, Gavel, BadgeCheck, ChevronRight, Lock } = lucideReact;

const tabColors: Record<JourneyTabId, { icon: string; active: string; bg: string; completed: string }> = {
  Discover:  { icon: stageColors.Discover.icon,  active: stageColors.Discover.active,  bg: stageColors.Discover.bg,  completed: '#0e9f6e' },
  Govern:    { icon: stageColors.Govern.icon,    active: stageColors.Govern.active,    bg: stageColors.Govern.bg,    completed: '#0e9f6e' },
  Define:    { icon: stageColors.Define.icon,    active: stageColors.Define.active,    bg: stageColors.Define.bg,    completed: '#0e9f6e' },
  Analyze:   { icon: stageColors.Analyze.icon,   active: stageColors.Analyze.active,   bg: stageColors.Analyze.bg,   completed: '#0e9f6e' },
  Develop:   { icon: stageColors.Develop.icon,   active: stageColors.Develop.active,   bg: stageColors.Develop.bg,   completed: '#0e9f6e' },
  Verify:    { icon: stageColors.Verify.icon,    active: stageColors.Verify.active,    bg: stageColors.Verify.bg,    completed: '#0e9f6e' },
  Decide:    { icon: stageColors.Decide.icon,    active: stageColors.Decide.active,    bg: stageColors.Decide.bg,    completed: '#0e9f6e' },
  Certify:   { icon: stageColors.Certify.icon,   active: stageColors.Certify.active,   bg: stageColors.Certify.bg,   completed: '#0e9f6e' },
};

export function Navigation() {
  const { activeTab, setActiveTab, workflow } = useAppStore();
  const { completedStages, lockedStages } = workflow;

  const tabIcons: Record<JourneyTabId, React.ReactNode> = {
    Discover: <Search size={18} strokeWidth={1.75} />,
    Govern: <Shield size={18} strokeWidth={1.75} />,
    Define: <Edit size={18} strokeWidth={1.75} />,
    Analyze: <GitBranch size={18} strokeWidth={1.75} />,
    Develop: <Code size={18} strokeWidth={1.75} />,
    Verify: <CheckCircle size={18} strokeWidth={1.75} />,
    Decide: <Gavel size={18} strokeWidth={1.75} />,
    Certify: <BadgeCheck size={18} strokeWidth={1.75} />,
  };

  return (
    <nav
      className="flex flex-col h-full w-[260px] bg-white border-r border-[var(--color-surface-border)] flex-shrink-0"
      aria-label="Main navigation"
    >
      {/* Logo */}
      <div className="flex items-center gap-3 px-5 py-5 border-b border-[var(--color-surface-border)]">
        <div className="flex items-center justify-center w-9 h-9 rounded-xl text-white" style={{ background: brandColor.base }}>
          <Search size={18} strokeWidth={2} />
        </div>
        <div>
          <h1 className="text-[0.95rem] font-bold text-[var(--color-text-primary)] tracking-tight font-display">Smorx</h1>
          <p className="text-[0.65rem] font-medium text-[var(--color-text-muted)] tracking-wide uppercase">Behavioral OS</p>
        </div>
      </div>

      {/* Journey Tabs */}
      <div className="flex-1 overflow-y-auto px-3 py-3 space-y-0.5">
        <p className="text-[0.65rem] font-semibold text-[var(--color-text-muted)] uppercase tracking-wider px-3 mb-2">Journey</p>
        {journeyTabs.map((tab) => {
          const isActive = activeTab === tab.id;
          const available = isTabAvailable(tab.id, completedStages, lockedStages);
          const completed = completedStages.includes(tab.id);
          const locked = lockedStages.includes(tab.id);
          const colors = tabColors[tab.id];

          return (
            <button
              key={tab.id}
              onClick={() => available && setActiveTab(tab.id)}
              disabled={!available}
              className={cn(
                'nav-item relative group',
                isActive && 'nav-item--active',
                !available && 'nav-item--disabled',
              )}
              style={isActive ? { background: colors.bg, color: colors.active } : undefined}
              title={!available ? `${tab.label} requires previous stages to complete` : tab.description}
              aria-current={isActive ? 'page' : undefined}
              aria-disabled={!available}
            >
              <span
                className="flex-shrink-0 transition-colors"
                style={{ color: isActive ? colors.active : completed ? colors.completed : undefined }}
              >
                {tabIcons[tab.id]}
              </span>
              <span className="flex-1 text-left truncate text-[0.8125rem]">{tab.label}</span>
              {completed && !isActive && (
                <CheckCircle size={14} className="flex-shrink-0" style={{ color: colors.completed }} />
              )}
              {locked && !completed && (
                <Lock size={14} className="text-[var(--color-text-muted)]/60 flex-shrink-0" />
              )}
              {!available && !locked && !completed && (
                <Lock size={14} className="text-[var(--color-text-muted)]/30 flex-shrink-0" />
              )}
            </button>
          );
        })}
      </div>

      {/* Workflow Progress */}
      <div className="px-3 py-4 border-t border-[var(--color-surface-border)]">
        <p className="text-[0.65rem] font-semibold text-[var(--color-text-muted)] uppercase tracking-wider px-3 mb-3">Workflow Progress</p>
        <div className="space-y-1.5">
          {journeyTabs.map((tab, index) => {
            const completed = completedStages.includes(tab.id);
            const current = activeTab === tab.id;
            const isLast = index === journeyTabs.length - 1;
            const colors = tabColors[tab.id];

            return (
              <div key={tab.id} className="relative">
                <div className="flex items-center gap-2.5">
                  <div
                    className="flex-shrink-0 w-5 h-5 rounded-full border-2 flex items-center justify-center transition-all"
                    style={
                      completed
                        ? { background: colors.completed, borderColor: colors.completed }
                        : current
                        ? { background: 'white', borderColor: colors.active, boxShadow: `0 0 0 3px ${colors.bg}` }
                        : { background: '#eef1f8', borderColor: '#e3e8f2' }
                    }
                  >
                    {completed && <CheckCircle size={10} className="text-white" strokeWidth={3} />}
                    {current && !completed && <span className="w-1.5 h-1.5 rounded-full" style={{ background: colors.active }} />}
                  </div>
                  <span
                    className="text-[0.7rem] font-medium truncate"
                    style={
                      completed
                        ? { color: colors.completed }
                        : current
                        ? { color: colors.active }
                        : { color: '#8a94a8' }
                    }
                  >
                    {tab.label}
                  </span>
                </div>
                {!isLast && (
                  <div
                    className="absolute left-[9px] top-5 bottom-0 w-[1.5px]"
                    style={{ background: completed ? colors.completed : '#c2cdde' }}
                  />
                )}
              </div>
            );
          })}
        </div>
      </div>
    </nav>
  );
}


