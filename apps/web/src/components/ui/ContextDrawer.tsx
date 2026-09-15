'use client';

import { useEffect, type HTMLAttributes } from 'react';
import { cn, getTrustStateClasses } from '@/lib/design-tokens';
import { lucideReact } from '@/lib/lucide-imports';
import { EvidenceItem, type EvidenceData } from './EvidenceItem';
import { Claim, type ClaimData } from './Claim';
import { ProvenanceLink, type ProvenanceLinkData } from './ProvenanceLink';
import { ExecutionEvent, type ExecutionEventData } from './ExecutionEvent';
import { TestResult, type TestResultData } from './TestResult';
import { GraphNode, type GraphNodeData } from './GraphNode';
import { CodeDiff, type CodeDiffData } from './CodeDiff';
import { StateBadge } from './StateBadge';

const { X, FileText, Shield, Search, Terminal, CheckCircle2, Hash, Link: LinkIcon } = lucideReact;

/**
 * ContextDrawer - Sliding panel for contextual inspection of evidence, claims, graph nodes, etc.
 */
export interface ContextDrawerProps extends HTMLAttributes<HTMLDivElement> {
  isOpen: boolean;
  onClose: () => void;
  type: 'evidence' | 'claim' | 'provenance' | 'graph-node' | 'code-diff' | 'execution-trace' | 'certificate' | null;
  title: string;
  data: Record<string, unknown> | null;
  size?: 'sm' | 'md' | 'lg' | 'xl' | 'full';
  children?: React.ReactNode;
}

const sizeClasses = {
  sm: 'max-w-md',
  md: 'max-w-lg',
  lg: 'max-w-xl',
  xl: 'max-w-2xl',
  full: 'max-w-4xl',
};

export function ContextDrawer({ isOpen, onClose, type, title, data, size = 'lg', children, className, ...props }: ContextDrawerProps) {
  useEffect(() => {
    if (isOpen) {
      document.body.style.overflow = 'hidden';
    }
    return () => {
      document.body.style.overflow = '';
    };
  }, [isOpen]);

  if (!isOpen || !type || !data) return null;

  return (
    <div className="fixed inset-0 z-[var(--z-drawer)] glass-backdrop" onClick={onClose} aria-hidden="true">
      <div
        className={cn(
          'fixed inset-y-0 right-0 z-[var(--z-drawer)] glass-drawer w-full border-l border-[var(--color-surface-border)] shadow-[var(--shadow-elevation-4)] transform transition-transform duration-[var(--duration-normal)] ease-[var(--ease-out)]',
          sizeClasses[size],
          'flex flex-col h-full'
        )}
        onClick={(e) => e.stopPropagation()}
        {...props}
      >
        {/* Header */}
        <div className="flex items-center justify-between px-4 py-3 border-b border-[var(--color-surface-border)]">
          <div className="flex items-center gap-3">
            <div className={cn(
              'flex items-center justify-center w-8 h-8 rounded-lg bg-[var(--color-surface)] border border-[var(--color-surface-border)] text-[var(--color-text-muted)]'
            )}>
              {getDrawerIcon(type)}
            </div>
            <div>
              <h2 className="text-heading font-semibold">{title}</h2>
              <p className="text-caption text-[var(--color-text-muted)] capitalize">{type.replace('-', ' ')} inspector</p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-2 rounded-lg text-[var(--color-text-muted)] hover:text-[var(--color-text-primary)] hover:bg-[var(--color-surface-border)] transition-colors"
            aria-label="Close drawer"
          >
            <X size={20} />
          </button>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto p-4">
          {children || renderInspectorContent(type, data)}
        </div>
      </div>
    </div>
  );
}

function getDrawerIcon(type: ContextDrawerProps['type']) {
  if (!type) return <FileText size={16} />;
  const icons: Record<string, React.ReactNode> = {
    evidence: <FileText size={16} />,
    claim: <Shield size={16} />,
    provenance: <LinkIcon size={16} />,
    'graph-node': <Search size={16} />,
    'code-diff': <FileText size={16} />,
    'execution-trace': <Terminal size={16} />,
    certificate: <CheckCircle2 size={16} />,
  };
  return icons[type] || <FileText size={16} />;
}

function renderInspectorContent(type: ContextDrawerProps['type'], data: Record<string, unknown>) {
  switch (type) {
    case 'evidence':
      return <EvidenceItem evidence={data as unknown as EvidenceData} variant="card" />;
    case 'claim':
      return <Claim claim={data as unknown as ClaimData} variant="card" />;
    case 'provenance':
      return <ProvenanceLink link={data as unknown as ProvenanceLinkData} variant="card" />;
    case 'graph-node':
      return <GraphNodeInspector node={data as unknown as GraphNodeData} onClose={() => {}} />;
    case 'code-diff':
      return <CodeDiff diff={data as unknown as CodeDiffData} />;
    case 'execution-trace':
      return <ExecutionEvent event={data as unknown as ExecutionEventData} variant="card" />;
    case 'certificate':
      return <CertificateInspector certificate={data as unknown as CertificateData} />;
    default:
      return <pre className="text-code-sm max-h-[400px] overflow-auto">{JSON.stringify(data, null, 2)}</pre>;
  }
}

interface GraphNodeInspectorProps {
  node: GraphNodeData;
  onClose: () => void;
  onSelectEvidence?: (evidenceId: string) => void;
  onSelectClaim?: (claimId: string) => void;
}

function GraphNodeInspector({ node, onClose, onSelectEvidence, onSelectClaim }: GraphNodeInspectorProps) {
  if (!node) return null;
  const { data: obj, type, trustState } = node;
  const trustClasses = getTrustStateClasses(trustState);

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-3">
        <div className={cn('flex items-center justify-center w-10 h-10 rounded-lg bg-[var(--color-surface)] border border-[var(--color-surface-border)]')}>
          {getDrawerIcon('graph-node')}
        </div>
        <div>
          <h3 className="text-heading font-semibold">{obj.name}</h3>
          <div className="flex items-center gap-2 mt-1">
            <StateBadge state={trustState} size="sm" />
            <span className="text-caption text-[var(--color-text-muted)]">{type}</span>
          </div>
        </div>
      </div>

      {obj.description && (
        <div className="pt-3 border-t border-[var(--color-surface-border)]">
          <p className="text-caption text-[var(--color-text-muted)] mb-1">Description</p>
          <p className="text-body-sm">{obj.description}</p>
        </div>
      )}

      <div className="pt-3 border-t border-[var(--color-surface-border)]">
        <p className="text-caption text-[var(--color-text-muted)] mb-2">Metadata</p>
        <dl className="grid grid-cols-2 gap-2 text-body-sm">
          <dt className="text-[var(--color-text-muted)]">Type</dt>
          <dd className="font-mono">{type}</dd>
          <dt className="text-[var(--color-text-muted)]">Status</dt>
          <dd>{obj.status}</dd>
          {obj.confidence !== undefined && (
            <>
              <dt className="text-[var(--color-text-muted)]">Confidence</dt>
              <dd className="font-mono">{Math.round(obj.confidence * 100)}%</dd>
            </>
          )}
          {obj.discoveredAt && (
            <>
              <dt className="text-[var(--color-text-muted)]">Discovered</dt>
              <dd className="font-mono">{new Date(obj.discoveredAt).toLocaleString()}</dd>
            </>
          )}
          <dt className="text-[var(--color-text-muted)]">Repository</dt>
          <dd className="font-mono truncate">{obj.repositoryId}</dd>
        </dl>
      </div>

      {obj.claimIds && obj.claimIds.length > 0 && (
        <div className="pt-3 border-t border-[var(--color-surface-border)]">
          <p className="text-caption text-[var(--color-text-muted)] mb-2">Linked Claims</p>
          <div className="space-y-1">
            {obj.claimIds.map((claimId: string) => (
              <button
                key={claimId}
                onClick={() => onSelectClaim?.(claimId)}
                className="flex items-center gap-2 w-full px-3 py-2 text-left text-body-sm rounded-lg border border-[var(--color-surface-border)] bg-[var(--color-surface)] hover:bg-[var(--color-surface-border)] transition-colors"
              >
                <LinkIcon size={14} className="text-[var(--color-text-muted)]" />
                <span className="font-mono truncate">{claimId}</span>
              </button>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

interface CertificateData {
  id: string;
  certificateId: string;
  changeId: string;
  commit: string;
  status: string;
  issuedAt: string;
  protectedBehaviors: string[];
  evidenceTraversal: string[];
}

function CertificateInspector({ certificate }: { certificate: CertificateData }) {
  return (
    <div className="space-y-4">
      <div className="flex items-center gap-3">
        <div className="flex items-center justify-center w-10 h-10 rounded-lg bg-[var(--color-surface)] border border-[var(--color-surface-border)] text-[var(--color-trust-certified)]">
          <CheckCircle2 size={20} />
        </div>
        <div>
          <h3 className="text-heading font-semibold">Certificate</h3>
          <p className="text-caption text-[var(--color-text-muted)] font-mono">{certificate.certificateId}</p>
        </div>
      </div>

      <div className="grid grid-cols-2 gap-4 pt-3 border-t border-[var(--color-surface-border)]">
        <div>
          <p className="text-caption text-[var(--color-text-muted)] mb-1">Change</p>
          <p className="text-body-sm font-mono truncate">{certificate.changeId}</p>
        </div>
        <div>
          <p className="text-caption text-[var(--color-text-muted)] mb-1">Commit</p>
          <p className="text-body-sm font-mono truncate">{certificate.commit}</p>
        </div>
        <div>
          <p className="text-caption text-[var(--color-text-muted)] mb-1">Status</p>
          <p className="text-body-sm font-medium capitalize">{certificate.status.toLowerCase()}</p>
        </div>
        <div>
          <p className="text-caption text-[var(--color-text-muted)] mb-1">Issued</p>
          <p className="text-body-sm font-mono">{new Date(certificate.issuedAt).toLocaleString()}</p>
        </div>
      </div>

      {certificate.protectedBehaviors.length > 0 && (
        <div className="pt-3 border-t border-[var(--color-surface-border)]">
          <p className="text-caption text-[var(--color-text-muted)] mb-2">Protected Behaviors</p>
          <div className="flex flex-wrap gap-2">
            {certificate.protectedBehaviors.map((behavior, i) => (
              <span key={i} className="px-2 py-1 text-caption bg-[var(--color-surface)] rounded border border-[var(--color-surface-border)] font-mono">{behavior}</span>
            ))}
          </div>
        </div>
      )}

      {certificate.evidenceTraversal.length > 0 && (
        <div className="pt-3 border-t border-[var(--color-surface-border)]">
          <p className="text-caption text-[var(--color-text-muted)] mb-2">Evidence Traversal</p>
          <div className="space-y-1 max-h-[200px] overflow-y-auto">
            {certificate.evidenceTraversal.map((evidence, i) => (
              <div key={i} className="flex items-center gap-2 px-2 py-1 text-caption bg-[var(--color-surface)] rounded border border-[var(--color-surface-border)]">
                <Hash size={12} className="text-[var(--color-text-muted)]" />
                <span className="font-mono truncate">{evidence}</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}