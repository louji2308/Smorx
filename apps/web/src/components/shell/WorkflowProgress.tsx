'use client';

import { useAppStore } from '@/store/appStore';
import { journeyTabs, stageColors, type JourneyTabId, isTabAvailable } from '@/lib/design-tokens';
import { lucideReact } from '@/lib/lucide-imports';
import { cn } from '@/lib/design-tokens';

const { Search, Shield, Edit, GitBranch, Code, CheckCircle, Gavel, BadgeCheck } = lucideReact;

const tabIcons: Record<JourneyTabId, React.ReactNode> = {
  Discover: <Search size={14} strokeWidth={2} />,
  Govern: <Shield size={14} strokeWidth={2} />,
  Define: <Edit size={14} strokeWidth={2} />,
  Analyze: <GitBranch size={14} strokeWidth={2} />,
  Develop: <Code size={14} strokeWidth={2} />,
  Verify: <CheckCircle size={14} strokeWidth={2} />,
  Decide: <Gavel size={14} strokeWidth={2} />,
  Certify: <BadgeCheck size={14} strokeWidth={2} />,
};

export function WorkflowProgress() {
  const { activeTab, setActiveTab, workflow } = useAppStore();
  const { completedStages, lockedStages } = workflow;

  return (
    <div className="w-full bg-white border-b border-[var(--color-surface-border)] px-6 py-4">
      <div className="flex items-center gap-0 max-w-5xl mx-auto">
        {journeyTabs.map((tab, index) => {
          const completed = completedStages.includes(tab.id);
          const current = activeTab === tab.id;
          const available = isTabAvailable(tab.id, completedStages, lockedStages);
          const isLast = index === journeyTabs.length - 1;
          const colors = stageColors[tab.id];

          return (
            <div key={tab.id} className="flex items-center flex-1 last:flex-none">
              {/* Pill step */}
              <button
                onClick={() => available && setActiveTab(tab.id)}
                disabled={!available}
                className={cn(
                  'relative flex items-center gap-2 px-3 py-1.5 rounded-full border transition-all duration-300 flex-shrink-0',
                  completed && 'border-[#0e9f6e] bg-[#0e9f6e]',
                  current && !completed && 'bg-white',
                  !completed && !current && 'border-[#e3e8f2] bg-[#f5f7fb]',
                  !available && 'opacity-40 cursor-not-allowed',
                )}
                style={
                  current && !completed
                    ? { borderColor: colors.active, boxShadow: `0 0 0 2px ${colors.bg}` }
                    : undefined
                }
              >
                <span
                  className={cn(
                    'transition-colors',
                    completed ? 'text-white' : current ? '' : 'text-[#8a94a8]',
                  )}
                  style={current && !completed ? { color: colors.active } : undefined}
                >
                  {tabIcons[tab.id]}
                </span>
                <span
                  className={cn(
                    'text-[0.7rem] font-medium whitespace-nowrap',
                    completed ? 'text-white' : current ? 'text-[var(--color-text-primary)]' : 'text-[#8a94a8]',
                  )}
                  style={current && !completed ? { color: colors.active } : undefined}
                >
                  {tab.label}
                </span>
              </button>

              {/* Connecting line */}
              {!isLast && (
                <div className="flex-1 h-[2px] mx-1 bg-[#e3e8f2] relative overflow-hidden">
                  <div
                    className={cn(
                      'absolute inset-0 origin-left transition-transform duration-700 ease-out',
                      completed && 'scale-x-100',
                      !completed && 'scale-x-0',
                    )}
                    style={{
                      background: `linear-gradient(90deg, ${colors.completed || '#0e9f6e'}, ${stageColors[journeyTabs[index + 1]?.id]?.completed || '#14936b'})`,
                    }}
                  />
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
