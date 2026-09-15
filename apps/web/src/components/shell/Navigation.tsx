'use client';

import { useAppStore } from '@/store/appStore';
import { cn } from '@/lib/design-tokens';
import { journeyTabs, stageColors, brandColor, type JourneyTabId, isTabAvailable } from '@/lib/design-tokens';
import { lucideReact } from '@/lib/lucide-imports';

const { Search, Shield, Edit, GitBranch, Code, CheckCircle, Gavel, BadgeCheck, ChevronRight, Lock, FolderGit2, FileCode, Settings } = lucideReact;

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
  const { activeTab, setActiveTab, workflow, project, repository, change, constitution } = useAppStore();
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
          <h1 className="text-[1.05rem] font-medium text-[var(--color-text-primary)] tracking-wide font-brand">Smorx</h1>
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
              style={isActive ? { background: 'rgb(31 36 48 / 0.07)', color: '#1F2430' } : undefined}
              title={!available ? `${tab.label} requires previous stages to complete` : tab.description}
              aria-current={isActive ? 'page' : undefined}
              aria-disabled={!available}
            >
              <span
                className="flex-shrink-0 transition-colors"
                style={{ color: isActive ? colors.icon : completed ? colors.completed : undefined }}
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

      {/* Context */}
      <div className="px-3 border-t border-[var(--color-surface-border)]">
        <p className="text-[0.65rem] font-semibold text-[var(--color-text-muted)] uppercase tracking-wider px-3 pt-3 pb-2">Context</p>
        <div className="space-y-2 px-1 pb-3">
          {project && (
            <div className="flex items-center gap-2 min-w-0">
              <FolderGit2 size={12} className="text-[#5b66e8] flex-shrink-0" strokeWidth={2} />
              <div className="min-w-0">
                <p className="text-[0.6rem] font-medium text-[var(--color-text-muted)] uppercase tracking-wider leading-none">Project</p>
                <p className="text-[0.7rem] font-semibold text-[var(--color-text-primary)] truncate leading-tight">{project.name}</p>
              </div>
            </div>
          )}
          {repository && (
            <div className="flex items-center gap-2 min-w-0">
              <GitBranch size={12} className="text-[#7c5ce0] flex-shrink-0" strokeWidth={2} />
              <div className="min-w-0">
                <p className="text-[0.6rem] font-medium text-[var(--color-text-muted)] uppercase tracking-wider leading-none">Repository</p>
                <p className="text-[0.7rem] font-semibold text-[var(--color-text-primary)] truncate leading-tight">{repository.name}</p>
              </div>
            </div>
          )}
          {change && (
            <div className="flex items-center gap-2 min-w-0">
              <FileCode size={12} className="text-[#3d86f4] flex-shrink-0" strokeWidth={2} />
              <div className="min-w-0">
                <p className="text-[0.6rem] font-medium text-[var(--color-text-muted)] uppercase tracking-wider leading-none">Change</p>
                <p className="text-[0.7rem] font-semibold text-[var(--color-text-primary)] truncate leading-tight">{change.externalId || change.title}</p>
              </div>
            </div>
          )}
          {constitution && (
            <div className="flex items-center gap-2 min-w-0">
              <Shield size={12} className="text-[var(--color-trust-protected)] flex-shrink-0" strokeWidth={2} />
              <div className="min-w-0">
                <p className="text-[0.6rem] font-medium text-[var(--color-text-muted)] uppercase tracking-wider leading-none">Constitution</p>
                <p className="text-[0.7rem] font-semibold text-[var(--color-text-primary)] truncate leading-tight">{constitution.title}</p>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Footer: Loujan + Settings */}
      <div className="flex items-center justify-between px-4 py-3 border-t border-[var(--color-surface-border)]">
        <div className="flex items-center gap-2">
          <div className="flex items-center justify-center w-7 h-7 rounded-lg bg-[var(--color-accent-tint)] border border-[var(--color-accent-soft)]">
            <span className="text-[0.7rem] font-bold text-[var(--color-accent-primary)]">L</span>
          </div>
          <span className="text-[0.75rem] font-medium text-[var(--color-text-primary)]">Loujan</span>
        </div>
        <button
          className="p-1.5 rounded-full text-[var(--color-text-muted)] hover:text-[var(--color-text-primary)] hover:bg-[var(--color-surface-subtle)] transition-all"
          aria-label="Settings"
        >
          <Settings size={16} strokeWidth={1.75} />
        </button>
      </div>
    </nav>
  );
}
