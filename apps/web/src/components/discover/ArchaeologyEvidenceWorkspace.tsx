'use client';

import { useState, type ReactNode } from 'react';
import { useAppStore } from '@/store/appStore';
import { Section, EmptyState } from '@/components/shell/AppShell';
import { StateBadge } from '@/components/ui/StateBadge';
import { lucideReact } from '@/lib/lucide-imports';
import { cn, getBehavioralObjectColor } from '@/lib/design-tokens';
import type { TrustState } from '@/types';

const { Search, Shield, AlertTriangle, GitBranch, Database, Zap, Ghost, FileText, ChevronRight, Settings, Layers, Clock } = lucideReact;

/**
 * ArchaeologyEvidenceWorkspace - Screen 2: Explore Evidence
 * Primary exploration environment for archaeology findings
 */
export function ArchaeologyEvidenceWorkspace() {
  const { setSelectedObject, setSelectedEvidence, openDrawer } = useAppStore();
  const [selectedCategory, setSelectedCategory] = useState<Category>('behaviors');
  const [searchQuery, setSearchQuery] = useState('');
  const [filterStatus, setFilterStatus] = useState<string>('all');

  const categories: CategoryConfig[] = [
    { id: 'behaviors', label: 'Behaviors', count: 24, icon: <Search size={16} />, color: 'text-[#4a6cf7]' },
    { id: 'invariants', label: 'Invariants', count: 18, icon: <Shield size={16} />, color: 'text-[#0e9f6e]' },
    { id: 'incidents', label: 'Incidents', count: 7, icon: <AlertTriangle size={16} />, color: 'text-[#d8493c]' },
    { id: 'dependencies', label: 'Dependencies', count: 42, icon: <Database size={16} />, color: 'text-[#c08a17]' },
    { id: 'couplings', label: 'Couplings', count: 15, icon: <GitBranch size={16} />, color: 'text-[#7c5ce0]' },
    { id: 'riskZones', label: 'Risk Zones', count: 8, icon: <Zap size={16} />, color: 'text-[#e98c4e]' },
    { id: 'ghosts', label: 'Ghosts', count: 3, icon: <Ghost size={16} />, color: 'text-[#7c5ce0]' },
    { id: 'evidence', label: 'Evidence', count: 156, icon: <FileText size={16} />, color: 'text-[var(--color-text-primary)]' },
  ];

  // Mock data for demonstration
  const mockBehaviors: FindingItem[] = [
    { id: 'b-017', name: 'Payment timeout triggers retry', type: 'BEHAVIOR', description: 'When payment gateway returns timeout, system automatically retries with exponential backoff', confidence: 0.94, protected: true, status: 'PROTECTED', evidenceCount: 5 },
    { id: 'b-024', name: 'Repeated payment requests use idempotency protection', type: 'BEHAVIOR', description: 'Duplicate payment requests with same idempotency key are deduplicated', confidence: 0.99, protected: true, status: 'PROTECTED', evidenceCount: 8 },
    { id: 'b-041', name: 'Authentication caching reduces latency', type: 'BEHAVIOR', description: 'Auth tokens cached for 15 minutes to reduce provider calls', confidence: 0.68, protected: false, status: 'OBSERVED', evidenceCount: 3 },
    { id: 'b-089', name: 'Session refresh on 401 response', type: 'BEHAVIOR', description: 'Automatic token refresh when API returns unauthorized', confidence: 0.87, protected: true, status: 'PROTECTED', evidenceCount: 4 },
  ];

  const mockInvariants: FindingItem[] = [
    { id: 'inv-001', name: 'Tenant isolation must never be violated', type: 'INVARIANT', statement: 'Cross-tenant data access MUST return 403', severity: 'CRITICAL', confidence: 0.99, status: 'PROTECTED' },
    { id: 'inv-002', name: 'Payment idempotency guarantee', type: 'INVARIANT', statement: 'Same idempotency key MUST return identical result', severity: 'CRITICAL', confidence: 0.98, status: 'PROTECTED' },
    { id: 'inv-003', name: 'Audit trail immutability', type: 'INVARIANT', statement: 'Audit logs MUST be append-only', severity: 'HIGH', confidence: 0.95, status: 'PROTECTED' },
  ];

  const mockIncidents: FindingItem[] = [
    { id: 'inc-61', name: 'Auth bypass via session refresh', type: 'INCIDENT', description: 'Session refresh endpoint allowed cross-tenant access', severity: 'CRITICAL', status: 'RESOLVED', detectedAt: '2024-03-15' },
    { id: 'inc-102', name: 'Payment duplicate charge', type: 'INCIDENT', description: 'Race condition caused duplicate charges for same idempotency key', severity: 'HIGH', status: 'RESOLVED', detectedAt: '2024-01-22' },
  ];

  const mockDependencies: FindingItem[] = [
    { id: 'dep-stripe', name: 'Stripe SDK', type: 'DEPENDENCY', version: '^14.0.0', risk: 'LOW', ecosystem: 'npm', status: 'OBSERVED' },
    { id: 'dep-auth0', name: 'Auth0 SDK', type: 'DEPENDENCY', version: '^3.0.0', risk: 'MEDIUM', ecosystem: 'npm', status: 'OBSERVED' },
    { id: 'dep-postgres', name: 'PostgreSQL', type: 'DEPENDENCY', version: '15.x', risk: 'LOW', ecosystem: 'system', status: 'PROTECTED' },
  ];

  const mockGhosts: FindingItem[] = [
    { id: 'ghost-221', name: 'Ghost #221 - Tenant isolation bypass', type: 'GHOST', description: 'Historical replay of auth provider migration showing 403→200 regression', status: 'CANDIDATE', confidence: 0.91 },
    { id: 'ghost-184', name: 'Ghost #184 - Payment retry storm', type: 'GHOST', description: 'Retry logic caused cascade failure under load', status: 'CONFIRMED', confidence: 0.87 },
  ];

  const getItemsForCategory = (category: string): FindingItem[] => {
    switch (category) {
      case 'behaviors': return mockBehaviors;
      case 'invariants': return mockInvariants;
      case 'incidents': return mockIncidents;
      case 'dependencies': return mockDependencies;
      case 'ghosts': return mockGhosts;
      default: return [];
    }
  };

  const items = getItemsForCategory(selectedCategory);
  const filteredItems = items.filter(item => {
    const matchesSearch = item.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      item.description?.toLowerCase().includes(searchQuery.toLowerCase());
    const matchesStatus = filterStatus === 'all' || item.status === filterStatus;
    return matchesSearch && matchesStatus;
  });

  return (
    <div className="space-y-6">
      <Section
        title="Evidence Exploration"
        description="Explore behavioral findings and their supporting evidence from software archaeology."
      >
        {/* Toolbar: search + status filter */}
        <div className="surface-card p-4 flex flex-col sm:flex-row items-stretch sm:items-center gap-3">
          <div className="relative flex-1">
            <input
              type="text"
              name="finding-search"
              id="finding-search"
              placeholder="Search findings..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="input w-full pl-10"
            />
            <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-[var(--color-text-muted)]" />
          </div>
          <select
            name="finding-status"
            id="finding-status"
            value={filterStatus}
            onChange={(e) => setFilterStatus(e.target.value)}
            className="input w-full sm:w-48"
          >
            <option value="all">All Status</option>
            <option value="PROTECTED">Protected</option>
            <option value="OBSERVED">Observed</option>
            <option value="RESOLVED">Resolved</option>
            <option value="CANDIDATE">Candidate</option>
            <option value="CONFIRMED">Confirmed</option>
          </select>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-[260px_1fr] gap-6">
          {/* Left: Category Navigation Rail */}
          <aside className="surface-card overflow-hidden flex flex-col">
            <div className="p-4 border-b border-[var(--color-surface-border)]">
              <h3 className="text-subheading font-semibold">Categories</h3>
              <p className="text-caption text-[var(--color-text-muted)] mt-1">
                {categories.find(c => c.id === selectedCategory)?.count || 0} findings
              </p>
            </div>
            <nav className="flex-1 overflow-y-auto p-2 space-y-1">
              {categories.map((cat) => (
                <button
                  key={cat.id}
                  onClick={() => setSelectedCategory(cat.id)}
                  className={cn(
                    'w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-left transition-all',
                    selectedCategory === cat.id
? 'bg-[color-mix(in_srgb,_var(--color-accent-primary)_10%,_transparent)] border border-[color-mix(in_srgb,_var(--color-accent-primary)_30%,_transparent)] text-[var(--color-accent-primary)]'
                      : 'text-[var(--color-text-secondary)] hover:bg-[var(--color-surface)] hover:text-[var(--color-text-primary)]',
                  )}
                >
                  <span className={cn('flex-shrink-0', cat.color)}>
                    {cat.icon}
                  </span>
                  <div className="flex-1 min-w-0">
                    <p className="text-body-sm font-medium truncate">{cat.label}</p>
                    <p className="text-caption text-[var(--color-text-muted)] truncate">{cat.count} findings</p>
                  </div>
                </button>
              ))}
              <button
                onClick={() => setSelectedCategory('evidence')}
                className={cn(
                  'w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-left transition-all border-t border-[var(--color-surface-border)] pt-3 mt-2',
                  selectedCategory === 'evidence'
                    ? 'bg-[color-mix(in_srgb,_var(--color-accent-primary)_10%,_transparent)] border border-[color-mix(in_srgb,_var(--color-accent-primary)_30%,_transparent)] text-[var(--color-accent-primary)]'
                    : 'text-[var(--color-text-secondary)] hover:bg-[var(--color-surface)] hover:text-[var(--color-text-primary)]',
                )}
              >
                <span className={cn('flex-shrink-0', categories.find(c => c.id === 'evidence')?.color)}>
                  <FileText size={16} />
                </span>
                <div className="flex-1 min-w-0">
                  <p className="text-body-sm font-medium truncate">All Evidence</p>
                  <p className="text-caption text-[var(--color-text-muted)] truncate">156 evidence items</p>
                </div>
              </button>
            </nav>
          </aside>

          {/* Right: Primary Evidence Region */}
          <div className="flex flex-col min-w-0">
            {/* Category Header */}
            <div className="surface-card p-4 flex-shrink-0">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <div className={cn('flex items-center justify-center w-10 h-10 rounded-lg bg-[var(--color-surface)] border border-[var(--color-surface-border)]', categories.find(c => c.id === selectedCategory)?.color)}>
                    {categories.find(c => c.id === selectedCategory)?.icon}
                  </div>
                  <div>
                    <h3 className="text-heading font-semibold">{categories.find(c => c.id === selectedCategory)?.label}</h3>
                    <p className="text-body-sm text-[var(--color-text-muted)]">
                      {filteredItems.length} of {items.length} findings
                      {searchQuery && ` matching "${searchQuery}"`}
                    </p>
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  <button className="btn btn--ghost btn-sm">
                    <Settings size={16} />
                    Columns
                  </button>
                  <button className="btn btn--ghost btn-sm">
                    <Layers size={16} />
                    Group
                  </button>
                </div>
              </div>
            </div>

            {/* Findings List */}
            <div className="flex-1 overflow-y-auto surface-card">
              {filteredItems.length === 0 ? (
                <EmptyState
                  icon={<Search size={32} />}
                  title="No findings match"
                  description={searchQuery ? `No ${categories.find(c => c.id === selectedCategory)?.label.toLowerCase()} found matching "${searchQuery}"` : `No ${categories.find(c => c.id === selectedCategory)?.label.toLowerCase()} discovered yet`}
                />
              ) : (
                <div className="divide-y divide-[var(--color-surface-border)]">
                  {filteredItems.map((item, index) => (
                    <button
                      key={item.id}
                      onClick={() => {
                        setSelectedObject({
                          type: selectedCategory as any,
                          id: item.id,
                          data: { ...item },
                        });
                        openDrawer('evidence', { ...item });
                      }}
                      className="w-full p-4 hover:bg-[var(--color-surface)] transition-colors text-left flex items-start gap-4"
                    >
                      <div className={cn('flex-shrink-0 w-10 h-10 rounded-lg flex items-center justify-center', getBehavioralObjectColor(item.type as any))}>
                        {categories.find(c => c.id === selectedCategory)?.icon}
                      </div>
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2 flex-wrap">
                          <span className="font-mono text-body-sm font-medium truncate max-w-[300px]">{item.name}</span>
                          <StateBadge state={item.status as TrustState} size="sm" variant="dot" />
                        </div>
                        {item.description && (
                          <p className="text-body-sm text-[var(--color-text-secondary)] mt-1 line-clamp-2">{item.description}</p>
                        )}
                        <div className="flex items-center gap-4 mt-2 text-caption text-[var(--color-text-muted)]">
                          {item.confidence !== undefined && (
                            <span className="flex items-center gap-1">
                              <Shield size={12} />
                              {Math.round(item.confidence * 100)}% confidence
                            </span>
                          )}
                          {item.evidenceCount !== undefined && (
                            <span className="flex items-center gap-1">
                              <FileText size={12} />
                              {item.evidenceCount} evidence
                            </span>
                          )}
                          {item.severity && (
                            <span className={cn('flex items-center gap-1', item.severity === 'CRITICAL' && 'text-[var(--color-trust-violated)]')}>
                              <AlertTriangle size={12} />
                              {item.severity}
                            </span>
                          )}
                          {item.detectedAt && (
                            <span className="flex items-center gap-1">
                              <Clock size={12} />
                              {new Date(item.detectedAt).toLocaleDateString()}
                            </span>
                          )}
                        </div>
                      </div>
                      <ChevronRight className="text-[var(--color-text-muted)] flex-shrink-0" size={16} />
                    </button>
                  ))}
                </div>
              )}
            </div>
          </div>
        </div>
      </Section>
    </div>
  );
}

type Category = 'behaviors' | 'invariants' | 'incidents' | 'dependencies' | 'couplings' | 'riskZones' | 'ghosts' | 'evidence';

interface CategoryConfig {
  id: Category;
  label: string;
  count: number;
  icon: ReactNode;
  color: string;
}

interface FindingItem {
  id: string;
  name: string;
  type: string;
  description?: string;
  status: string;
  confidence?: number;
  protected?: boolean;
  evidenceCount?: number;
  severity?: string;
  detectedAt?: string;
  statement?: string;
  version?: string;
  risk?: string;
  ecosystem?: string;
}