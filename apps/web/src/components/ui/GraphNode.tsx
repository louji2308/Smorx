'use client';

import { forwardRef, type HTMLAttributes } from 'react';
import { Handle, Position, type NodeProps } from '@xyflow/react';
import { cn, getBehavioralObjectColor, getTrustStateClasses } from '@/lib/design-tokens';
import { StateBadge } from './StateBadge';
import { lucideReact } from '@/lib/lucide-imports';
import type { GraphNodeData, BehavioralObject, BehavioralObjectType, TrustState } from '@/types';

const { Search, Shield, AlertTriangle, GitBranch, Zap, Ghost, ChevronRight, FileText, Link: LinkIcon } = lucideReact;

/**
 * GraphNode - React Flow node component for behavioral knowledge graph
 * Displays behavioral objects with trust state and type indicators
 */
export type { GraphNodeData, BehavioralObject };

const typeIcons: Record<BehavioralObjectType, React.ReactNode> = {
  BEHAVIOR: <Search size={16} />,
  INVARIANT: <Shield size={16} />,
  INCIDENT: <AlertTriangle size={16} />,
  DEPENDENCY: <GitBranch size={16} />,
  RISK_ZONE: <Zap size={16} />,
  GHOST: <Ghost size={16} />,
} as const;

const typeLabels: Record<BehavioralObjectType, string> = {
  BEHAVIOR: 'Behavior',
  INVARIANT: 'Invariant',
  INCIDENT: 'Incident',
  DEPENDENCY: 'Dependency',
  RISK_ZONE: 'Risk Zone',
  GHOST: 'Ghost',
} as const;

interface GraphNodeProps extends NodeProps {}

export const GraphNode = forwardRef<HTMLDivElement, GraphNodeProps>(
  ({ data, selected }, ref) => {
    const nodeData = data as unknown as GraphNodeData;
    const { type, label, trustState, data: obj } = nodeData;
    const Icon = typeIcons[type] || <Search size={16} />;
    const typeLabel = typeLabels[type] || type;
    const trustClasses = getTrustStateClasses(trustState);
    const typeColor = getBehavioralObjectColor(type);

    return (
      <div
        ref={ref}
        className={cn(
          'rf-node flex flex-col gap-2 min-w-[180px] max-w-[280px]',
          'bg-[var(--color-surface-elevated)] border border-[var(--color-surface-border)] rounded-[var(--radius-md)] px-3 py-2',
          selected && 'border-[var(--color-accent-primary)] shadow-[var(--shadow-focus)]',
        )}
      >
        {/* Top bar with type icon and trust badge */}
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <span className={cn('flex-shrink-0', typeColor)}>
              {Icon}
            </span>
            <span className="text-body font-medium truncate max-w-[200px]">{label}</span>
          </div>
          <StateBadge state={trustState} size="sm" variant="pill" showIcon={false} />
        </div>

        {/* Description */}
        {obj.description && (
          <p className="text-body-sm text-[var(--color-text-secondary)] truncate line-clamp-2">{obj.description}</p>
        )}

        {/* Metadata row */}
        <div className="flex items-center gap-3 text-caption text-[var(--color-text-muted)]">
          {obj.confidence !== undefined && (
            <span className="flex items-center gap-1">
              <span className="w-2 h-2 rounded-full" style={{ backgroundColor: obj.confidence >= 0.8 ? 'var(--color-trust-certified)' : obj.confidence >= 0.5 ? 'var(--color-trust-unverified)' : 'var(--color-trust-violated)' }} />
              {Math.round(obj.confidence * 100)}%
            </span>
          )}
          {obj.protected && (
            <span className="flex items-center gap-1 text-[var(--color-trust-protected)]">
              <Shield size={10} />
              PROTECTED
            </span>
          )}
          {obj.claimIds && obj.claimIds.length > 0 && (
            <span className="flex items-center gap-1">
              <LinkIcon size={10} />
              {obj.claimIds.length} claims
            </span>
          )}
        </div>

        {/* Connection handles */}
        <div className="flex items-center justify-between pt-1">
          <Handle type="target" position={Position.Left} className="w-2 h-2 bg-[var(--color-surface-border)] rounded-full hover:bg-[var(--color-accent-primary)] transition-colors" />
          <Handle type="source" position={Position.Right} className="w-2 h-2 bg-[var(--color-surface-border)] rounded-full hover:bg-[var(--color-accent-primary)] transition-colors" />
        </div>
      </div>
    );
  }
);

GraphNode.displayName = 'GraphNode';

/**
 * Mini graph node for compact display in lists/inspectors
 */
export interface MiniGraphNodeProps extends Omit<HTMLAttributes<HTMLButtonElement>, 'onSelect'> {
  node: GraphNodeData;
  onClick?: () => void;
}

export const MiniGraphNode = forwardRef<HTMLButtonElement, MiniGraphNodeProps>(
  ({ node, onClick, className, ...props }, ref) => {
    const { type, label, trustState, data: obj } = node;
    const Icon = typeIcons[type] || <Search size={14} />;
    const trustClasses = getTrustStateClasses(trustState);
    const typeColor = getBehavioralObjectColor(type);

    return (
      <button
        ref={ref}
        onClick={onClick}
        className={cn(
          'flex items-center gap-2 px-3 py-2 rounded-lg border transition-all',
          'bg-[var(--color-surface-elevated)] border-[var(--color-surface-border)]',
          'hover:border-[var(--color-surface-border-strong)] hover:bg-[var(--color-surface-border)]',
          className
        )}
        {...props}
      >
        <span className={cn('flex-shrink-0', typeColor)}>
          {Icon}
        </span>
        <div className="flex-1 min-w-0">
          <p className="text-body-sm font-medium truncate">{label}</p>
          <p className="text-caption text-[var(--color-text-muted)] truncate">{typeLabels[type] || type}</p>
        </div>
        <StateBadge state={trustState} size="sm" variant="dot" />
        <ChevronRight className="text-[var(--color-text-muted)] flex-shrink-0" size={14} />
      </button>
    );
  }
);

MiniGraphNode.displayName = 'MiniGraphNode';

/**
 * Graph node type for the inspector
 */
export interface GraphNodeInspectorProps {
  node: GraphNodeData | null;
  onClose: () => void;
  onSelectEvidence?: (evidenceId: string) => void;
  onSelectClaim?: (claimId: string) => void;
}