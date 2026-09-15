'use client';

import { useState } from 'react';
import { JourneyPage } from '@/components/shell/AppShell';
import { ConstitutionWorkspace } from './ConstitutionWorkspace';
import { ConstitutionActivation } from './ConstitutionActivation';
import { lucideReact } from '@/lib/lucide-imports';
import { cn } from '@/lib/design-tokens';

const { Shield, Lock } = lucideReact;

const screens = [
  { id: 'workspace', label: 'Constitution Workspace', icon: <Shield size={16} /> },
  { id: 'activation', label: 'Activation & Ratification', icon: <Lock size={16} /> },
] as const;

type GovernScreen = (typeof screens)[number]['id'];

/**
 * GovernTab - Main Govern journey tab with two screens
 * 1. Constitution Workspace
 * 2. Activation & Ratification
 */
export function GovernTab() {
  const [currentScreen, setCurrentScreen] = useState<GovernScreen>('workspace');

  return (
    <JourneyPage
      title="Govern"
      description="What behavior should remain protected? Ratify the Behavioral Constitution."
      actions={
        <div className="flex items-center gap-1 p-1 rounded-lg bg-[var(--color-surface)] border border-[var(--color-surface-border)]">
          {screens.map((screen) => (
            <button
              key={screen.id}
              onClick={() => setCurrentScreen(screen.id)}
              className={cn(
                'flex items-center gap-2 px-3 py-1.5 rounded-lg text-[0.8rem] font-medium transition-all',
                currentScreen === screen.id
                  ? 'bg-[color-mix(in_srgb,_var(--color-accent-primary)_10%,_transparent)] text-[var(--color-accent-primary)] border border-[color-mix(in_srgb,_var(--color-accent-primary)_30%,_transparent)]'
                  : 'text-[var(--color-text-secondary)] hover:bg-[var(--color-surface)] hover:text-[var(--color-text-primary)]',
              )}
            >
              {screen.icon}
              {screen.label}
            </button>
          ))}
        </div>
      }
    >
      <div className="space-y-6">
        {currentScreen === 'workspace' && (
          <ConstitutionWorkspace onActivate={() => setCurrentScreen('activation')} />
        )}
        {currentScreen === 'activation' && <ConstitutionActivation />}
      </div>
    </JourneyPage>
  );
}