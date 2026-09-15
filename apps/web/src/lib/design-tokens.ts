/**
 * Design token utilities and helper functions
 * Centralized access to semantic design tokens
 */

import { clsx, type ClassValue } from 'clsx';
import { twMerge } from 'tailwind-merge';

/**
 * Merge Tailwind classes with proper precedence
 */
export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

/**
 * Trust state color mapping
 */
export const trustStateColors = {
  OBSERVED: {
    bg: 'bg-[color-mix(in_srgb,_var(--color-trust-observed)_15%,_transparent)]',
    text: 'text-[var(--color-trust-observed)]',
    border: 'border-[color-mix(in_srgb,_var(--color-trust-observed)_30%,_transparent)]',
    shadow: 'shadow-[var(--shadow-trust-observed)]',
    icon: 'text-[var(--color-trust-observed)]',
  },
  PROTECTED: {
    bg: 'bg-[color-mix(in_srgb,_var(--color-trust-protected)_15%,_transparent)]',
    text: 'text-[var(--color-trust-protected)]',
    border: 'border-[color-mix(in_srgb,_var(--color-trust-protected)_30%,_transparent)]',
    shadow: 'shadow-[var(--shadow-trust-protected)]',
    icon: 'text-[var(--color-trust-protected)]',
  },
  LOCKED: {
    bg: 'bg-[color-mix(in_srgb,_var(--color-trust-locked)_15%,_transparent)]',
    text: 'text-[var(--color-trust-locked)]',
    border: 'border-[color-mix(in_srgb,_var(--color-trust-locked)_30%,_transparent)]',
    shadow: 'shadow-[var(--shadow-trust-locked)]',
    icon: 'text-[var(--color-trust-locked)]',
  },
  UNVERIFIED: {
    bg: 'bg-[color-mix(in_srgb,_var(--color-trust-unverified)_15%,_transparent)]',
    text: 'text-[var(--color-trust-unverified)]',
    border: 'border-[color-mix(in_srgb,_var(--color-trust-unverified)_30%,_transparent)]',
    shadow: 'shadow-[var(--shadow-elevation-1)]',
    icon: 'text-[var(--color-trust-unverified)]',
  },
  VIOLATED: {
    bg: 'bg-[color-mix(in_srgb,_var(--color-trust-violated)_15%,_transparent)]',
    text: 'text-[var(--color-trust-violated)]',
    border: 'border-[color-mix(in_srgb,_var(--color-trust-violated)_30%,_transparent)]',
    shadow: 'shadow-[var(--shadow-trust-violated)]',
    icon: 'text-[var(--color-trust-violated)]',
  },
  REPAIR_REQUIRED: {
    bg: 'bg-[color-mix(in_srgb,_var(--color-trust-repair)_15%,_transparent)]',
    text: 'text-[var(--color-trust-repair)]',
    border: 'border-[color-mix(in_srgb,_var(--color-trust-repair)_30%,_transparent)]',
    shadow: 'shadow-[var(--shadow-elevation-1)]',
    icon: 'text-[var(--color-trust-repair)]',
  },
  CERTIFIED: {
    bg: 'bg-[color-mix(in_srgb,_var(--color-trust-certified)_15%,_transparent)]',
    text: 'text-[var(--color-trust-certified)]',
    border: 'border-[color-mix(in_srgb,_var(--color-trust-certified)_30%,_transparent)]',
    shadow: 'shadow-[var(--shadow-trust-certified)]',
    icon: 'text-[var(--color-trust-certified)]',
  },
  HISTORICAL: {
    bg: 'bg-[color-mix(in_srgb,_var(--color-trust-historical)_15%,_transparent)]',
    text: 'text-[var(--color-trust-historical)]',
    border: 'border-[color-mix(in_srgb,_var(--color-trust-historical)_30%,_transparent)]',
    shadow: 'shadow-[var(--shadow-elevation-1)]',
    icon: 'text-[var(--color-trust-historical)]',
  },
} as const;

export type TrustState = keyof typeof trustStateColors;

/**
 * Get trust state color classes
 */
export function getTrustStateClasses(state: TrustState) {
  return trustStateColors[state] || trustStateColors.OBSERVED;
}

/**
 * Trust state label mapping
 */
export const trustStateLabels: Record<TrustState, string> = {
  OBSERVED: 'OBSERVED',
  PROTECTED: 'PROTECTED',
  LOCKED: 'LOCKED',
  UNVERIFIED: 'UNVERIFIED',
  VIOLATED: 'VIOLATED',
  REPAIR_REQUIRED: 'REPAIR REQUIRED',
  CERTIFIED: 'CERTIFIED',
  HISTORICAL: 'HISTORICAL',
};

/**
 * Trust state icon mapping (Lucide icon names)
 */
export const trustStateIcons: Record<TrustState, string> = {
  OBSERVED: 'eye',
  PROTECTED: 'shield',
  LOCKED: 'lock',
  UNVERIFIED: 'alert-circle',
  VIOLATED: 'alert-triangle',
  REPAIR_REQUIRED: 'wrench',
  CERTIFIED: 'check-circle-2',
  HISTORICAL: 'clock',
};

/**
 * Trust state descriptions
 */
export const trustStateDescriptions: Record<TrustState, string> = {
  OBSERVED: 'Known to occur but not governed',
  PROTECTED: 'Governed requirement, actively enforced',
  LOCKED: 'Immutable governing context',
  UNVERIFIED: 'Proposed but not independently verified',
  VIOLATED: 'Critical behavioral contract violated',
  REPAIR_REQUIRED: 'Unauthorized change requires evidence-driven repair',
  CERTIFIED: 'Independently verified and evidence-bound',
  HISTORICAL: 'Historical memory, not current intent',
};

/**
 * Behavioral object type colors
 */
export const behavioralObjectColors = {
  BEHAVIOR: 'text-[#4A6CF7]',
  INVARIANT: 'text-[#0E9F6E]',
  INCIDENT: 'text-[#D8493C]',
  DEPENDENCY: 'text-[#C08A17]',
  RISK_ZONE: 'text-[#E98C4E]',
  GHOST: 'text-[#7C5CE0]',
} as const;

export type BehavioralObjectType = keyof typeof behavioralObjectColors;

/**
 * Get behavioral object type color
 */
export function getBehavioralObjectColor(type: BehavioralObjectType) {
  return behavioralObjectColors[type] || behavioralObjectColors.BEHAVIOR;
}

/**
 * Brand accent — single bespoke action color (not generic UI-blue)
 */
export const brandColor = {
  base: '#4A6CF7',
  strong: '#3A56D6',
  tint: '#EDF1FE',
  soft: '#DCE4FD',
} as const;

/**
 * Journey stage hues — designed soft ramps, used only as wayfinding accents
 * (active tab, workflow dots, tiny tinted surfaces). Never as full-page color.
 */
export const stageColors: Record<JourneyTabId, { icon: string; active: string; strong: string; bg: string; tint: string; border: string }> = {
  Discover: { icon: '#5B66E8', active: '#5B66E8', strong: '#4A54C4', bg: 'rgb(91 102 232 / 0.08)', tint: '#EEF0FD', border: '#DCE0FA' },
  Govern:   { icon: '#7C5CE0', active: '#7C5CE0', strong: '#5B44B8', bg: 'rgb(124 92 224 / 0.08)',  tint: '#F2EEFC', border: '#E3DBF6' },
  Define:   { icon: '#3D86F4', active: '#3D86F4', strong: '#2F6BD0', bg: 'rgb(61 134 244 / 0.08)',  tint: '#EDF3FE', border: '#D9E6FC' },
  Analyze:  { icon: '#22A7D4', active: '#22A7D4', strong: '#177F9E', bg: 'rgb(34 167 212 / 0.08)',  tint: '#EBF7FB', border: '#D4EDF5' },
  Develop:  { icon: '#1EAF8C', active: '#1EAF8C', strong: '#138463', bg: 'rgb(30 175 140 / 0.08)',  tint: '#EBF9F4', border: '#D4F1E7' },
  Verify:   { icon: '#D89A24', active: '#D89A24', strong: '#A9761B', bg: 'rgb(216 154 36 / 0.08)',  tint: '#FBF6E8', border: '#F2E7CC' },
  Decide:   { icon: '#E98C4E', active: '#E98C4E', strong: '#C96A2E', bg: 'rgb(233 140 78 / 0.08)',  tint: '#FDF1EA', border: '#F8DECF' },
  Certify:  { icon: '#DB5F9C', active: '#DB5F9C', strong: '#B33D78', bg: 'rgb(219 95 156 / 0.08)',  tint: '#FCEEF5', border: '#F5D9E6' },
} as const;

/**
 * Journey tab configuration
 */
export const journeyTabs = [
  { id: 'Discover', label: 'Discover', icon: 'search', description: 'What does the software actually do?' },
  { id: 'Govern', label: 'Govern', icon: 'shield', description: 'What behavior should remain protected?' },
  { id: 'Define', label: 'Define', icon: 'edit', description: 'What does the human want changed?' },
  { id: 'Analyze', label: 'Analyze', icon: 'git-branch', description: 'What could this change affect?' },
  { id: 'Develop', label: 'Develop', icon: 'code', description: 'What did the Coding Agent propose?' },
  { id: 'Verify', label: 'Verify', icon: 'check-circle', description: 'What does independent investigation establish?' },
  { id: 'Decide', label: 'Decide', icon: 'gavel', description: 'Is the observed change authorized?' },
  { id: 'Certify', label: 'Certify', icon: 'badge-check', description: 'Can the repaired result become trusted?' },
] as const;

export type JourneyTabId = (typeof journeyTabs)[number]['id'];

/**
 * Workflow stage progression
 */
export const workflowStages = journeyTabs.map(t => t.id);

/**
 * Check if a tab is available based on workflow state
 */
export function isTabAvailable(tabId: JourneyTabId, completedStages: JourneyTabId[], lockedStages: JourneyTabId[]): boolean {
  const tabIndex = workflowStages.indexOf(tabId);
  if (tabIndex === 0) return true; // Discover is always available

  const previousTab = workflowStages[tabIndex - 1];
  return completedStages.includes(previousTab) && !lockedStages.includes(tabId);
}

/**
 * Animation durations
 */
export const durations = {
  fast: 100,
  normal: 200,
  slow: 300,
} as const;

/**
 * Z-index layers
 */
export const zIndex = {
  base: 0,
  dropdown: 100,
  drawer: 200,
  modal: 300,
  popover: 400,
  tooltip: 500,
  toast: 600,
} as const;

/**
 * Breakpoints
 */
export const breakpoints = {
  xs: 480,
  sm: 640,
  md: 768,
  lg: 1024,
  xl: 1280,
  '2xl': 1536,
} as const;

/**
 * Format timestamp for display
 */
export function formatTimestamp(timestamp: string): string {
  const date = new Date(timestamp);
  return date.toLocaleString(undefined, {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
  });
}

/**
 * Format relative time
 */
export function formatRelativeTime(timestamp: string): string {
  const date = new Date(timestamp);
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffSecs = Math.floor(diffMs / 1000);
  const diffMins = Math.floor(diffSecs / 60);
  const diffHours = Math.floor(diffMins / 60);
  const diffDays = Math.floor(diffHours / 24);

  if (diffSecs < 60) return 'just now';
  if (diffMins < 60) return `${diffMins}m ago`;
  if (diffHours < 24) return `${diffHours}h ago`;
  if (diffDays < 7) return `${diffDays}d ago`;
  return formatTimestamp(timestamp);
}

/**
 * Truncate text with ellipsis
 */
export function truncate(text: string, maxLength: number): string {
  if (text.length <= maxLength) return text;
  return text.slice(0, maxLength - 3) + '...';
}

/**
 * Generate unique ID
 */
export function generateId(prefix: string = ''): string {
  return `${prefix}${Date.now().toString(36)}${Math.random().toString(36).slice(2, 9)}`;
}