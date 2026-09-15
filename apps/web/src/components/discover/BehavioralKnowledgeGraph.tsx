'use client';

import { useCallback, useState, type MouseEvent as ReactMouseEvent, type ReactNode } from 'react';
import {
  ReactFlow,
  Background,
  Controls,
  MiniMap,
  BaseEdge,
  EdgeLabelRenderer,
  getSmoothStepPath,
  MarkerType,
  addEdge,
  applyNodeChanges,
  applyEdgeChanges,
  getIncomers,
  getOutgoers,
  type Node,
  type Edge,
  type NodeTypes,
  type EdgeTypes,
  type EdgeProps,
  type OnNodesChange,
  type OnEdgesChange,
  type Connection,
} from '@xyflow/react';
import '@xyflow/react/dist/style.css';

import { useAppStore } from '@/store/appStore';
import { Section } from '@/components/shell/AppShell';
import { StateBadge } from '@/components/ui/StateBadge';
import { GraphNode } from '@/components/ui/GraphNode';
import { lucideReact } from '@/lib/lucide-imports';
import { cn } from '@/lib/design-tokens';
import type { GraphNodeData, BehavioralObject, TrustState } from '@/types';

const { Search, Shield, AlertTriangle, Database, Zap, Ghost, Eye, X } = lucideReact;

type GraphFlowNode = Node<GraphNodeData & Record<string, unknown>>;

const nodeTypes: NodeTypes = {
  BEHAVIOR: GraphNode,
  INVARIANT: GraphNode,
  INCIDENT: GraphNode,
  DEPENDENCY: GraphNode,
  RISK_ZONE: GraphNode,
  GHOST: GraphNode,
};

const trustStateDotColors: Record<string, string> = {
  OBSERVED: '#5b66e8',
  PROTECTED: '#0e9f6e',
  LOCKED: '#7c5ce0',
  VIOLATED: '#d8493c',
  UNVERIFIED: '#c08a17',
};

const nodeTypeTextColor = (type: string) => {
  const colors: Record<string, string> = {
    BEHAVIOR: 'text-[#4a6cf7]',
    INVARIANT: 'text-[#0e9f6e]',
    INCIDENT: 'text-[#d8493c]',
    DEPENDENCY: 'text-[#c08a17]',
    RISK_ZONE: 'text-[#e98c4e]',
    GHOST: 'text-[#7c5ce0]',
  };
  return colors[type] ?? 'text-[var(--color-text-muted)]';
};

const initialNodes: GraphFlowNode[] = [
  {
    id: 'auth',
    type: 'BEHAVIOR',
    position: { x: 100, y: 60 },
    data: {
      id: 'auth',
      type: 'BEHAVIOR',
      label: 'Authentication',
      position: { x: 100, y: 60 },
      trustState: 'PROTECTED',
      data: {
        id: 'auth',
        objectType: 'BEHAVIOR',
        name: 'Authentication',
        description: 'User authentication and session establishment',
        status: 'ACTIVE',
        confidence: 0.95,
        protected: true,
        repositoryId: 'repo-1',
        claimIds: ['claim-1'],
      } satisfies BehavioralObject,
    },
  },
  {
    id: 'session',
    type: 'BEHAVIOR',
    position: { x: 350, y: 60 },
    data: {
      id: 'session',
      type: 'BEHAVIOR',
      label: 'Session Management',
      position: { x: 350, y: 60 },
      trustState: 'PROTECTED',
      data: {
        id: 'session',
        objectType: 'BEHAVIOR',
        name: 'Session Management',
        description: 'Session creation, validation, and refresh',
        status: 'ACTIVE',
        confidence: 0.93,
        protected: true,
        repositoryId: 'repo-1',
        claimIds: ['claim-2'],
      } satisfies BehavioralObject,
    },
  },
  {
    id: 'tenant',
    type: 'BEHAVIOR',
    position: { x: 600, y: 60 },
    data: {
      id: 'tenant',
      type: 'BEHAVIOR',
      label: 'Tenant Isolation',
      position: { x: 600, y: 60 },
      trustState: 'LOCKED',
      data: {
        id: 'tenant',
        objectType: 'BEHAVIOR',
        name: 'Tenant Isolation',
        description: 'Prevents cross-tenant data access',
        status: 'ACTIVE',
        confidence: 0.99,
        protected: true,
        repositoryId: 'repo-1',
        claimIds: ['claim-3', 'claim-4'],
      } satisfies BehavioralObject,
    },
  },
  {
    id: 'audit',
    type: 'BEHAVIOR',
    position: { x: 850, y: 60 },
    data: {
      id: 'audit',
      type: 'BEHAVIOR',
      label: 'Audit Logging',
      position: { x: 850, y: 60 },
      trustState: 'PROTECTED',
      data: {
        id: 'audit',
        objectType: 'BEHAVIOR',
        name: 'Audit Logging',
        description: 'Immutable audit trail for all operations',
        status: 'ACTIVE',
        confidence: 0.96,
        protected: true,
        repositoryId: 'repo-1',
      } satisfies BehavioralObject,
    },
  },
  {
    id: 'inv-auth',
    type: 'INVARIANT',
    position: { x: 100, y: 300 },
    data: {
      id: 'inv-auth',
      type: 'INVARIANT',
      label: 'Auth Contract',
      position: { x: 100, y: 300 },
      trustState: 'LOCKED',
      data: {
        id: 'inv-auth',
        objectType: 'INVARIANT',
        name: 'Auth Contract',
        description: 'Authentication must validate credentials before session creation',
        status: 'LOCKED',
        confidence: 0.98,
        protected: true,
        repositoryId: 'repo-1',
        metadata: { severity: 'CRITICAL' },
      } satisfies BehavioralObject,
    },
  },
  {
    id: 'inc-61',
    type: 'INCIDENT',
    position: { x: 350, y: 300 },
    data: {
      id: 'inc-61',
      type: 'INCIDENT',
      label: 'Incident #61',
      position: { x: 350, y: 300 },
      trustState: 'VIOLATED',
      data: {
        id: 'inc-61',
        objectType: 'INCIDENT',
        name: 'Incident #61',
        description: 'Session refresh bypassed tenant authorization',
        status: 'RESOLVED',
        discoveredAt: '2024-03-15',
        repositoryId: 'repo-1',
        claimIds: ['claim-7'],
      } satisfies BehavioralObject,
    },
  },
  {
    id: 'inv-tenant',
    type: 'INVARIANT',
    position: { x: 600, y: 300 },
    data: {
      id: 'inv-tenant',
      type: 'INVARIANT',
      label: 'Tenant Isolation Invariant',
      position: { x: 600, y: 300 },
      trustState: 'LOCKED',
      data: {
        id: 'inv-tenant',
        objectType: 'INVARIANT',
        name: 'Tenant Isolation Invariant',
        description: 'Cross-tenant data access MUST return 403',
        status: 'LOCKED',
        confidence: 0.99,
        protected: true,
        repositoryId: 'repo-1',
        metadata: { severity: 'CRITICAL' },
      } satisfies BehavioralObject,
    },
  },
  {
    id: 'ghost-221',
    type: 'GHOST',
    position: { x: 850, y: 300 },
    data: {
      id: 'ghost-221',
      type: 'GHOST',
      label: 'Ghost #221',
      position: { x: 850, y: 300 },
      trustState: 'UNVERIFIED',
      data: {
        id: 'ghost-221',
        objectType: 'GHOST',
        name: 'Ghost #221',
        description: 'Historical replay of auth provider migration showing 403→200 regression',
        status: 'CANDIDATE',
        confidence: 0.91,
        repositoryId: 'repo-1',
      } satisfies BehavioralObject,
    },
  },
  {
    id: 'payment',
    type: 'BEHAVIOR',
    position: { x: 100, y: 540 },
    data: {
      id: 'payment',
      type: 'BEHAVIOR',
      label: 'Payment Processing',
      position: { x: 100, y: 540 },
      trustState: 'OBSERVED',
      data: {
        id: 'payment',
        objectType: 'BEHAVIOR',
        name: 'Payment Processing',
        description: 'Payment request handling with idempotency protection',
        status: 'ACTIVE',
        confidence: 0.92,
        protected: true,
        repositoryId: 'repo-1',
      } satisfies BehavioralObject,
    },
  },
  {
    id: 'retry',
    type: 'BEHAVIOR',
    position: { x: 350, y: 540 },
    data: {
      id: 'retry',
      type: 'BEHAVIOR',
      label: 'Retry Logic',
      position: { x: 350, y: 540 },
      trustState: 'PROTECTED',
      data: {
        id: 'retry',
        objectType: 'BEHAVIOR',
        name: 'Retry Logic',
        description: 'Exponential backoff on payment gateway timeouts',
        status: 'ACTIVE',
        confidence: 0.94,
        protected: true,
        repositoryId: 'repo-1',
      } satisfies BehavioralObject,
    },
  },
  {
    id: 'gateway',
    type: 'DEPENDENCY',
    position: { x: 600, y: 540 },
    data: {
      id: 'gateway',
      type: 'DEPENDENCY',
      label: 'Payment Gateway',
      position: { x: 600, y: 540 },
      trustState: 'OBSERVED',
      data: {
        id: 'gateway',
        objectType: 'DEPENDENCY',
        name: 'Payment Gateway',
        description: 'External payment provider integration',
        status: 'ACTIVE',
        confidence: 0.88,
        protected: false,
        repositoryId: 'repo-1',
      } satisfies BehavioralObject,
    },
  },
  {
    id: 'ghost-184',
    type: 'GHOST',
    position: { x: 850, y: 540 },
    data: {
      id: 'ghost-184',
      type: 'GHOST',
      label: 'Ghost #184',
      position: { x: 850, y: 540 },
      trustState: 'OBSERVED',
      data: {
        id: 'ghost-184',
        objectType: 'GHOST',
        name: 'Ghost #184',
        description: 'Retry logic caused cascade failure under load',
        status: 'CONFIRMED',
        confidence: 0.87,
        repositoryId: 'repo-1',
      } satisfies BehavioralObject,
    },
  },
  {
    id: 'risk-zone',
    type: 'RISK_ZONE',
    position: { x: 350, y: 780 },
    data: {
      id: 'risk-zone',
      type: 'RISK_ZONE',
      label: 'Payment Retry Storm',
      position: { x: 350, y: 780 },
      trustState: 'OBSERVED',
      data: {
        id: 'risk-zone',
        objectType: 'RISK_ZONE',
        name: 'Payment Retry Storm',
        description: 'Concentrated retry amplification around gateway failures',
        status: 'ACTIVE',
        confidence: 0.7,
        repositoryId: 'repo-1',
      } satisfies BehavioralObject,
    },
  },
];

const initialEdges: Edge[] = [
  { id: 'e-auth-session', type: 'animated', source: 'auth', target: 'session', label: 'creates', animated: true, markerEnd: MarkerType.ArrowClosed },
  { id: 'e-session-tenant', type: 'animated', source: 'session', target: 'tenant', label: 'enforces', animated: true, markerEnd: MarkerType.ArrowClosed },
  { id: 'e-tenant-audit', type: 'animated', source: 'tenant', target: 'audit', label: 'logs', animated: true, markerEnd: MarkerType.ArrowClosed },
  { id: 'e-inv-auth-auth', type: 'animated', source: 'inv-auth', target: 'auth', label: 'governs', animated: true, markerEnd: MarkerType.ArrowClosed },
  { id: 'e-inv-tenant-tenant', type: 'animated', source: 'inv-tenant', target: 'tenant', label: 'governs', animated: true, markerEnd: MarkerType.ArrowClosed },
  { id: 'e-inc-session', type: 'animated', source: 'inc-61', target: 'session', label: 'violated', animated: true, markerEnd: MarkerType.ArrowClosed },
  { id: 'e-inc-tenant', type: 'animated', source: 'inc-61', target: 'tenant', label: 'bypassed', animated: true, markerEnd: MarkerType.ArrowClosed },
  { id: 'e-ghost-inc', type: 'animated', source: 'ghost-221', target: 'inc-61', label: 'replays', animated: true, markerEnd: MarkerType.ArrowClosed },
  { id: 'e-ghost-inv', type: 'animated', source: 'ghost-221', target: 'inv-tenant', label: 'exposes', animated: true, markerEnd: MarkerType.ArrowClosed },
  { id: 'e-payment-retry', type: 'animated', source: 'payment', target: 'retry', label: 'uses', animated: true, markerEnd: MarkerType.ArrowClosed },
  { id: 'e-retry-gateway', type: 'animated', source: 'retry', target: 'gateway', label: 'calls', animated: true, markerEnd: MarkerType.ArrowClosed },
  { id: 'e-retry-risk', type: 'animated', source: 'retry', target: 'risk-zone', label: 'amplifies', animated: true, markerEnd: MarkerType.ArrowClosed },
  { id: 'e-ghost184-retry', type: 'animated', source: 'ghost-184', target: 'retry', label: 'replays', animated: true, markerEnd: MarkerType.ArrowClosed },
  { id: 'e-ghost184-gateway', type: 'animated', source: 'ghost-184', target: 'gateway', label: 'overloaded', animated: true, markerEnd: MarkerType.ArrowClosed },
];

const legendNodeTypes: { label: string; color: string; icon: ReactNode }[] = [
  { label: 'Behavior', color: 'text-[#4a6cf7]', icon: <Search size={12} /> },
  { label: 'Invariant', color: 'text-[#0e9f6e]', icon: <Shield size={12} /> },
  { label: 'Incident', color: 'text-[#d8493c]', icon: <AlertTriangle size={12} /> },
  { label: 'Dependency', color: 'text-[#c08a17]', icon: <Database size={12} /> },
  { label: 'Risk Zone', color: 'text-[#e98c4e]', icon: <Zap size={12} /> },
  { label: 'Ghost', color: 'text-[#7c5ce0]', icon: <Ghost size={12} /> },
];

const legendTrustStates: { label: string; state: TrustState }[] = [
  { label: 'Observed', state: 'OBSERVED' },
  { label: 'Protected', state: 'PROTECTED' },
  { label: 'Locked', state: 'LOCKED' },
  { label: 'Violated', state: 'VIOLATED' },
  { label: 'Unverified', state: 'UNVERIFIED' },
];

function AnimatedEdge({ id, sourceX, sourceY, sourcePosition, targetX, targetY, targetPosition, label, markerEnd }: EdgeProps) {
  const [edgePath, labelX, labelY] = getSmoothStepPath({
    sourceX,
    sourceY,
    sourcePosition,
    targetX,
    targetY,
    targetPosition,
  });

  return (
    <>
      <BaseEdge
        id={id}
        path={edgePath}
        markerEnd={markerEnd}
        style={{
          stroke: 'var(--color-surface-border-strong)',
          strokeWidth: 1,
          strokeDasharray: '6 4',
        }}
      />
      {label && (
        <EdgeLabelRenderer>
          <div
            className="nodrag nopan px-1.5 py-0.5 rounded-md border border-[var(--color-surface-border)] bg-[var(--color-surface-elevated)] text-code-sm text-[var(--color-text-muted)]"
            style={{
              position: 'absolute',
              transform: `translate(-50%, -50%) translate(${labelX}px, ${labelY}px)`,
              pointerEvents: 'none',
            }}
          >
            {label}
          </div>
        </EdgeLabelRenderer>
      )}
    </>
  );
}

const edgeTypes: EdgeTypes = {
  animated: AnimatedEdge,
};

function RelationshipPanel({ title, nodes, onSelect }: { title: string; nodes: GraphFlowNode[]; onSelect: (node: GraphFlowNode) => void }) {
  return (
    <section className="surface-card p-4">
      <h4 className="text-subheading font-semibold mb-3">{title}</h4>
      {nodes.length === 0 ? (
        <p className="text-caption text-[var(--color-text-muted)]">No nodes</p>
      ) : (
        <div className="space-y-2">
          {nodes.map((node) => (
            <button
              key={node.id}
              onClick={() => onSelect(node)}
              className="w-full flex items-center gap-3 p-3 rounded-lg border-transparent text-left hover:border-[var(--color-accent-primary)]/40 transition-colors"
            >
              <span className={cn('font-mono text-caption flex-shrink-0', nodeTypeTextColor(node.data.type))}>
                {node.data.type}
              </span>
              <span className="flex-1 min-w-0">
                <p className="text-body-sm font-medium truncate">{node.data.label}</p>
                <p className="text-caption text-[var(--color-text-muted)]">{node.id}</p>
              </span>
              <StateBadge state={node.data.trustState} size="sm" variant="dot" />
            </button>
          ))}
        </div>
      )}
    </section>
  );
}

export function BehavioralKnowledgeGraph() {
  const { selectedGraphNode, setSelectedGraphNode, openDrawer } = useAppStore();
  const [nodes, setNodes] = useState<GraphFlowNode[]>(initialNodes);
  const [edges, setEdges] = useState<Edge[]>(initialEdges);
  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(null);

  const onNodesChange: OnNodesChange<GraphFlowNode> = useCallback((changes) => {
    setNodes((nds) => applyNodeChanges(changes, nds));
  }, []);

  const onEdgesChange: OnEdgesChange = useCallback((changes) => {
    setEdges((eds) => applyEdgeChanges(changes, eds));
  }, []);

  const onConnect = useCallback((params: Connection) => {
    setEdges((eds) =>
      addEdge(
        {
          ...params,
          id: `edge-${params.source}-${params.target}-${Date.now()}`,
          type: 'animated',
          animated: true,
          markerEnd: MarkerType.ArrowClosed,
        },
        eds,
      ),
    );
  }, []);

  const onNodeClick = useCallback((_: ReactMouseEvent, node: GraphFlowNode) => {
    setSelectedNodeId(node.id);
    setSelectedGraphNode(node.data);
    openDrawer('graph-node', { ...node.data });
  }, [setSelectedGraphNode, openDrawer]);

  const onPaneClick = useCallback(() => {
    setSelectedNodeId(null);
    setSelectedGraphNode(null);
  }, [setSelectedGraphNode]);

  const minimapNodeColor = useCallback((node: Node) => {
    const trustState = node.data.trustState;
    const color = typeof trustState === 'string' ? trustStateDotColors[trustState] : undefined;
    return color ?? '#3d86f4';
  }, []);

  const selectedFlowNode = nodes.find((node) => node.id === selectedNodeId) ?? null;
  const incomingNodes: GraphFlowNode[] = selectedFlowNode
    ? (getIncomers(selectedFlowNode, nodes, edges) as GraphFlowNode[])
    : [];
  const outgoingNodes: GraphFlowNode[] = selectedFlowNode
    ? (getOutgoers(selectedFlowNode, nodes, edges) as GraphFlowNode[])
    : [];

  return (
    <div className="space-y-6">
      <Section
        title="Behavioral Knowledge Graph"
        description="Traverse the connected network of software behavior, dependencies, incidents, invariants, and historical ghosts."
      >
        <div className="surface-card relative h-[64vh] min-h-[520px] overflow-hidden">
          <ReactFlow
            nodes={nodes}
            edges={edges}
            onNodesChange={onNodesChange}
            onEdgesChange={onEdgesChange}
            onConnect={onConnect}
            onNodeClick={onNodeClick}
            onPaneClick={onPaneClick}
            nodeTypes={nodeTypes}
            edgeTypes={edgeTypes}
            fitView
            minZoom={0.35}
            maxZoom={1.6}
          >
            <Background color="#c2cdde" gap={16} />
            <Controls position="top-left" />
            <MiniMap position="top-right" pannable zoomable nodeColor={minimapNodeColor} />
          </ReactFlow>

          {/* Legend */}
          <div className="absolute bottom-4 right-4 surface-card-elevated p-3 rounded-lg z-10 min-w-[200px]">
            <h4 className="text-caption font-semibold text-[var(--color-text-primary)] mb-2">Node Types</h4>
            <div className="space-y-1.5 text-body-sm text-[var(--color-text-secondary)]">
              {legendNodeTypes.map((item) => (
                <div key={item.label} className="flex items-center gap-2">
                  <span className={cn('flex-shrink-0', item.color)}>{item.icon}</span>
                  <span>{item.label}</span>
                </div>
              ))}
            </div>
            <div className="border-t border-[var(--color-surface-border)] my-2 pt-2">
              <h4 className="text-caption font-semibold text-[var(--color-text-primary)] mb-2">Trust States</h4>
              <div className="space-y-1.5 text-body-sm text-[var(--color-text-secondary)]">
                {legendTrustStates.map((item) => (
                  <div key={item.label} className="flex items-center gap-2">
                    <StateBadge state={item.state} size="sm" variant="dot" />
                    <span>{item.label}</span>
                  </div>
                ))}
              </div>
            </div>
          </div>

          {/* Selected node overlay */}
          {selectedGraphNode && selectedFlowNode && (
            <div className="absolute bottom-4 left-4 surface-card-elevated p-4 rounded-lg z-10 max-w-xs">
              <div className="flex items-center justify-between gap-3 mb-2">
                <h4 className="text-subheading font-semibold text-[var(--color-text-primary)] truncate">{selectedGraphNode.label}</h4>
                <button
                  onClick={() => {
                    setSelectedNodeId(null);
                    setSelectedGraphNode(null);
                  }}
                  className="p-1 rounded-md text-[var(--color-text-muted)] hover:text-[var(--color-text-primary)] hover:bg-[var(--color-surface-border)]"
                  aria-label="Clear selection"
                >
                  <X size={14} />
                </button>
              </div>
              <StateBadge state={selectedGraphNode.trustState} size="sm" />
              <p className="text-body-sm text-[var(--color-text-secondary)] mt-2">{selectedGraphNode.data.description || 'No description'}</p>
              <button
                className="btn btn--ghost btn-sm w-full mt-3"
                onClick={() => openDrawer('graph-node', { ...selectedGraphNode })}
              >
                <Eye size={14} />
                Inspect
              </button>
            </div>
          )}
        </div>
      </Section>

      {/* Relationships */}
      {selectedFlowNode && (
        <Section title="Node Relationships">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <RelationshipPanel
              title="Incoming Connections"
              nodes={incomingNodes}
              onSelect={(node) => {
                setSelectedNodeId(node.id);
                setSelectedGraphNode(node.data);
              }}
            />
            <RelationshipPanel
              title="Outgoing Connections"
              nodes={outgoingNodes}
              onSelect={(node) => {
                setSelectedNodeId(node.id);
                setSelectedGraphNode(node.data);
              }}
            />
            <RelationshipPanel
              title="Selected Node"
              nodes={[selectedFlowNode]}
              onSelect={(node) => {
                setSelectedNodeId(node.id);
                setSelectedGraphNode(node.data);
              }}
            />
          </div>
        </Section>
      )}
    </div>
  );
}