'use client';

import { useState, type ReactNode } from 'react';
import { JourneyPage } from '@/components/shell/AppShell';
import { ArchaeologyLaunch } from './ArchaeologyLaunch';
import { ArchaeologyEvidenceWorkspace } from './ArchaeologyEvidenceWorkspace';
import { BehavioralKnowledgeGraph } from './BehavioralKnowledgeGraph';
import { lucideReact } from '@/lib/lucide-imports';
import { cn } from '@/lib/design-tokens';

const { Search, Eye, Layers, ChevronRight, ChevronLeft } = lucideReact;

type DiscoverScreen = 'launch' | 'evidence' | 'graph';

const screens: { id: DiscoverScreen; label: string; icon: ReactNode }[] = [
  { id: 'launch', label: 'Start Archaeology', icon: <Search size={15} strokeWidth={1.75} /> },
  { id: 'evidence', label: 'Evidence Workspace', icon: <Eye size={15} strokeWidth={1.75} /> },
  { id: 'graph', label: 'Knowledge Graph', icon: <Layers size={15} strokeWidth={1.75} /> },
];

const stepColors = ['#5b66e8', '#7c5ce0', '#3d86f4'];

export function DiscoverTab() {
  const [currentScreen, setCurrentScreen] = useState<DiscoverScreen>('launch');
  const currentIndex = screens.findIndex((screen) => screen.id === currentScreen);
  const goTo = (screen: DiscoverScreen) => setCurrentScreen(screen);
  const goBack = () => { if (currentIndex > 0) setCurrentScreen(screens[currentIndex - 1].id); };
  const goNext = () => { if (currentIndex < screens.length - 1) setCurrentScreen(screens[currentIndex + 1].id); };

  return (
    <JourneyPage title="Discover" description="What does the software actually do? Reconstruct behavioral memory from evidence.">
      <div className="space-y-5">
        {/* Segmented Step Switcher */}
        <div className="flex flex-col sm:flex-row gap-1 p-1 bg-white border border-[var(--color-surface-border)] rounded-2xl shadow-sm">
          {screens.map((screen, i) => (
            <button
              key={screen.id}
              onClick={() => goTo(screen.id)}
              className={cn(
                'flex items-center gap-2 flex-1 px-4 py-2.5 rounded-xl text-[0.8rem] font-semibold transition-all',
                currentScreen === screen.id
                  ? 'bg-accent-primary text-white shadow-sm'
                  : 'text-[var(--color-text-secondary)] hover:bg-[var(--color-surface-subtle)] hover:text-[var(--color-text-primary)]',
              )}
            >
              <span className="flex-shrink-0">{screen.icon}</span>
              <span>{screen.label}</span>
            </button>
          ))}
        </div>

        {/* Step Dots */}
        <div className="flex items-center gap-4">
          {screens.map((screen, index) => (
            <div key={screen.id} className="flex items-center">
              <button
                onClick={() => goTo(screen.id)}
                aria-label={`Go to ${screen.label}`}
                className="flex items-center justify-center w-8 h-8 rounded-full border-2 text-[0.7rem] font-bold transition-all"
                style={
                  index <= currentIndex
                    ? { background: stepColors[index], borderColor: stepColors[index], color: 'white' }
                    : { background: '#eef1f8', borderColor: '#e3e8f2', color: '#8a94a8' }
                }
              >
                {index + 1}
              </button>
              {index < screens.length - 1 && (
                <div
                  className="w-14 h-[2px] mx-2 rounded-full transition-colors"
                  style={{ background: index < currentIndex ? stepColors[index] : '#e3e8f2' }}
                />
              )}
            </div>
          ))}
        </div>

        {/* Active Screen */}
        {currentScreen === 'launch' && <ArchaeologyLaunch />}
        {currentScreen === 'evidence' && <ArchaeologyEvidenceWorkspace />}
        {currentScreen === 'graph' && <BehavioralKnowledgeGraph />}

        {/* Back / Next */}
        <div className="flex items-center justify-between pt-4 border-t border-[var(--color-surface-border)]">
          <button onClick={goBack} disabled={currentIndex === 0} className="btn btn--secondary">
            <ChevronLeft size={16} strokeWidth={2} /> Back
          </button>
          <span className="text-[0.75rem] font-medium text-[var(--color-text-muted)]">
            Step {currentIndex + 1} of {screens.length}
          </span>
          <button onClick={goNext} disabled={currentIndex === screens.length - 1} className="btn btn--primary">
            Next <ChevronRight size={16} strokeWidth={2} />
          </button>
        </div>
      </div>
    </JourneyPage>
  );
}
