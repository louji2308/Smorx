'use client';

import { forwardRef, type HTMLAttributes, type ReactNode } from 'react';
import { cn } from '@/lib/design-tokens';

/**
 * StateBadge - Semantic trust state indicator
 * Used throughout the system to display trust states with proper semantic meaning
 */
export interface StateBadgeProps extends HTMLAttributes<HTMLSpanElement> {
  state: TrustState;
  size?: 'sm' | 'md' | 'lg';
  showIcon?: boolean;
  showLabel?: boolean;
  variant?: 'badge' | 'dot' | 'pill';
}

export type TrustState =
  | 'OBSERVED'
  | 'PROTECTED'
  | 'LOCKED'
  | 'UNVERIFIED'
  | 'VIOLATED'
  | 'REPAIR_REQUIRED'
  | 'CERTIFIED'
  | 'HISTORICAL';

const iconMap: Record<TrustState, string> = {
  OBSERVED: 'eye',
  PROTECTED: 'shield',
  LOCKED: 'lock',
  UNVERIFIED: 'alert-circle',
  VIOLATED: 'alert-triangle',
  REPAIR_REQUIRED: 'wrench',
  CERTIFIED: 'check-circle-2',
  HISTORICAL: 'clock',
};

const labelMap: Record<TrustState, string> = {
  OBSERVED: 'OBSERVED',
  PROTECTED: 'PROTECTED',
  LOCKED: 'LOCKED',
  UNVERIFIED: 'UNVERIFIED',
  VIOLATED: 'VIOLATED',
  REPAIR_REQUIRED: 'REPAIR REQUIRED',
  CERTIFIED: 'CERTIFIED',
  HISTORICAL: 'HISTORICAL',
};

const sizeClasses = {
  sm: 'px-2 py-0.5 text-[0.625rem] gap-1',
  md: 'px-2.5 py-0.5 text-caption gap-1.5',
  lg: 'px-3 py-1 text-body-sm gap-2',
};

const stateClasses: Record<TrustState, string> = {
  OBSERVED: 'bg-[color-mix(in_srgb,_var(--color-trust-observed)_15%,_transparent)] text-[var(--color-trust-observed)] border border-[color-mix(in_srgb,_var(--color-trust-observed)_30%,_transparent)]',
  PROTECTED: 'bg-[color-mix(in_srgb,_var(--color-trust-protected)_15%,_transparent)] text-[var(--color-trust-protected)] border border-[color-mix(in_srgb,_var(--color-trust-protected)_30%,_transparent)]',
  LOCKED: 'bg-[color-mix(in_srgb,_var(--color-trust-locked)_15%,_transparent)] text-[var(--color-trust-locked)] border border-[color-mix(in_srgb,_var(--color-trust-locked)_30%,_transparent)]',
  UNVERIFIED: 'bg-[color-mix(in_srgb,_var(--color-trust-unverified)_15%,_transparent)] text-[var(--color-trust-unverified)] border border-[color-mix(in_srgb,_var(--color-trust-unverified)_30%,_transparent)]',
  VIOLATED: 'bg-[color-mix(in_srgb,_var(--color-trust-violated)_15%,_transparent)] text-[var(--color-trust-violated)] border border-[color-mix(in_srgb,_var(--color-trust-violated)_30%,_transparent)]',
  REPAIR_REQUIRED: 'bg-[color-mix(in_srgb,_var(--color-trust-repair)_15%,_transparent)] text-[var(--color-trust-repair)] border border-[color-mix(in_srgb,_var(--color-trust-repair)_30%,_transparent)]',
  CERTIFIED: 'bg-[color-mix(in_srgb,_var(--color-trust-certified)_15%,_transparent)] text-[var(--color-trust-certified)] border border-[color-mix(in_srgb,_var(--color-trust-certified)_30%,_transparent)]',
  HISTORICAL: 'bg-[color-mix(in_srgb,_var(--color-trust-historical)_15%,_transparent)] text-[var(--color-trust-historical)] border border-[color-mix(in_srgb,_var(--color-trust-historical)_30%,_transparent)]',
};

const dotClasses: Record<TrustState, string> = {
  OBSERVED: 'bg-[var(--color-trust-observed)]',
  PROTECTED: 'bg-[var(--color-trust-protected)]',
  LOCKED: 'bg-[var(--color-trust-locked)]',
  UNVERIFIED: 'bg-[var(--color-trust-unverified)]',
  VIOLATED: 'bg-[var(--color-trust-violated)]',
  REPAIR_REQUIRED: 'bg-[var(--color-trust-repair)]',
  CERTIFIED: 'bg-[var(--color-trust-certified)]',
  HISTORICAL: 'bg-[var(--color-trust-historical)]',
};

function Icon({ name, size = 12 }: { name: string; size?: number }) {
  const icons: Record<string, ReactNode> = {
    eye: <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/><circle cx="12" cy="12" r="3"/></svg>,
    shield: <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/></svg>,
    lock: <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><rect x="3" y="11" width="18" height="11" rx="2" ry="2"/><path d="M7 11V7a5 5 0 0 1 10 0v4"/></svg>,
    'alert-circle': <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/></svg>,
    'alert-triangle': <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M10.29 3.86 1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>,
    wrench: <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M14.7 6.3a1 1 0 0 0 0 1.4l1.6 1.6a1 1 0 0 0 1.4 0l3.77-3.77a6 6 0 0 1-7.94 7.94l-6.91 6.91a2.12 2.12 0 0 1-3-3l6.91-6.91a6 6 0 0 1 7.94-7.94l-3.76 3.76z"/></svg>,
    'check-circle-2': <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><circle cx="12" cy="12" r="10"/><path d="M9 12l2 2 4-4"/></svg>,
    clock: <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg>,
  };
  return icons[name] || icons.eye;
}

export const StateBadge = forwardRef<HTMLSpanElement, StateBadgeProps>(
  ({ state, size = 'md', showIcon = true, showLabel = true, variant = 'badge', className, children, ...props }, ref) => {
    if (variant === 'dot') {
      return (
        <span
          ref={ref}
          className={cn(
            'inline-flex items-center gap-1.5',
            'w-2 h-2 rounded-full',
            dotClasses[state],
            className
          )}
          {...props}
        />
      );
    }

    if (variant === 'pill') {
      return (
        <span
          ref={ref}
          className={cn(
            'inline-flex items-center gap-1.5 rounded-full border font-medium',
            sizeClasses[size],
            stateClasses[state],
            className
          )}
          {...props}
        >
          {showIcon && <Icon name={iconMap[state]} size={size === 'sm' ? 10 : size === 'md' ? 12 : 14} />}
          {showLabel && <span>{labelMap[state]}</span>}
          {children}
        </span>
      );
    }

    return (
      <span
        ref={ref}
        className={cn(
          'inline-flex items-center gap-1.5 rounded-full border font-medium',
          sizeClasses[size],
          stateClasses[state],
          className
        )}
        {...props}
      >
        {showIcon && <Icon name={iconMap[state]} size={size === 'sm' ? 10 : size === 'md' ? 12 : 14} />}
        {showLabel && <span>{labelMap[state]}</span>}
        {children}
      </span>
    );
  }
);

StateBadge.displayName = 'StateBadge';

/**
 * Dot-only variant for compact inline use
 */
export function StateDot({ state, size = 8, className }: { state: TrustState; size?: number; className?: string }) {
  return (
    <span
      className={cn('inline-block rounded-full', dotClasses[state], className)}
      style={{ width: size, height: size }}
      aria-label={labelMap[state]}
    />
  );
}