'use client';

import { useState } from 'react';
import { useAppStore } from '@/store/appStore';
import { Section, EmptyState } from '@/components/shell/AppShell';
import { Claim, type ClaimData } from '@/components/ui/Claim';
import { lucideReact } from '@/lib/lucide-imports';
import { cn } from '@/lib/design-tokens';

const { Shield, Search, Lock, Clock, Settings, Plus, CheckCircle2 } = lucideReact;

/**
 * ConstitutionWorkspace - Screen 1: Behavioral Constitution Workspace
 * Govern archaeological findings into protected constitutional claims
 */
export function ConstitutionWorkspace({ onActivate }: { onActivate?: () => void }) {
  const { setSelectedClaim, openDrawer } = useAppStore();
  const [selectedAuthority, setSelectedAuthority] = useState<string>('all');
  const [selectedStatus, setSelectedStatus] = useState<string>('all');
  const [searchQuery, setSearchQuery] = useState('');
  const [showHistorical, setShowHistorical] = useState(false);

  // Demo fixture data (deterministic; backend wiring is a later phase)
  const mockClaims: ClaimData[] = [
    {
      id: 'claim-1',
      claimId: 'AUTH-017',
      statement: 'Tenant isolation must never be violated. Cross-tenant data access MUST return 403.',
      authority: 'CRITICAL',
      confidence: 0.99,
      status: 'PROTECTED',
      locked: true,
      createdAt: '2024-01-15T10:00:00Z',
      evidenceIds: ['ev-001', 'ev-002', 'ev-003', 'ev-004', 'ev-005'],
      affectedSoftware: ['auth/session.ts', 'middleware/tenant.ts', 'api/tenant.ts'],
      governanceConsequence: 'Any change affecting tenant isolation requires independent verification and constitutional amendment',
      verificationRequirements: [
        'Historical Ghost replay - 8 scenarios',
        'Adversarial tenant switch testing - 21 cases',
        'Differential execution - 14 cases',
      ],
    },
    {
      id: 'claim-2',
      claimId: 'AUTH-022',
      statement: 'Authorization semantics must remain consistent across authentication provider changes.',
      authority: 'CRITICAL',
      confidence: 0.97,
      status: 'PROTECTED',
      locked: true,
      createdAt: '2024-01-15T10:00:00Z',
      evidenceIds: ['ev-006', 'ev-007', 'ev-008'],
      affectedSoftware: ['auth/authorization.ts', 'middleware/auth.ts'],
      governanceConsequence: 'Provider migration must preserve authorization decision logic',
      verificationRequirements: [
        'Differential execution - 12 cases',
        'Metamorphic checks - 7',
      ],
    },
    {
      id: 'claim-3',
      claimId: 'AUTH-023',
      statement: 'Session compatibility must be preserved during authentication changes.',
      authority: 'HIGH',
      confidence: 0.94,
      status: 'PROTECTED',
      locked: true,
      createdAt: '2024-01-15T10:00:00Z',
      evidenceIds: ['ev-009', 'ev-010'],
      affectedSoftware: ['auth/session.ts', 'auth/token.ts'],
      governanceConsequence: 'Session format and validation logic must remain backward compatible',
      verificationRequirements: [
        'Session compatibility testing - 9 cases',
        'Historical Ghost replay - 3 scenarios',
      ],
    },
    {
      id: 'claim-4',
      claimId: 'AUTH-031',
      statement: 'Authentication contract: valid credentials must produce valid session token.',
      authority: 'HIGH',
      confidence: 0.96,
      status: 'PROTECTED',
      locked: true,
      createdAt: '2024-01-15T10:00:00Z',
      evidenceIds: ['ev-011', 'ev-012', 'ev-013'],
      affectedSoftware: ['auth/provider.ts', 'auth/credentials.ts'],
      governanceConsequence: 'New provider must implement identical contract',
      verificationRequirements: [
        'Static analysis',
        'Differential execution - 8 cases',
      ],
    },
    {
      id: 'claim-5',
      claimId: 'AUD-011',
      statement: 'Authentication audit events must be emitted for all auth state changes.',
      authority: 'HIGH',
      confidence: 0.91,
      status: 'PROTECTED',
      locked: true,
      createdAt: '2024-01-15T10:00:00Z',
      evidenceIds: ['ev-014', 'ev-015'],
      affectedSoftware: ['auth/audit.ts', 'middleware/audit.ts'],
      governanceConsequence: 'Audit trail gaps are constitutional violations',
      verificationRequirements: [
        'Static dependency analysis',
        'Metamorphic checks - 5',
      ],
    },
    {
      id: 'claim-6',
      claimId: 'CACHE-041',
      statement: 'Authentication caching reduces provider latency by ~40%.',
      authority: 'MEDIUM',
      confidence: 0.68,
      status: 'OBSERVED',
      locked: false,
      createdAt: '2024-01-15T10:00:00Z',
      evidenceIds: ['ev-016', 'ev-017'],
      affectedSoftware: ['auth/cache.ts'],
      governanceConsequence: 'Observed behavior, not enforced',
      verificationRequirements: [],
    },
  ];

  const filteredClaims = mockClaims.filter(claim => {
    const matchesSearch = claim.claimId.toLowerCase().includes(searchQuery.toLowerCase()) ||
      claim.statement.toLowerCase().includes(searchQuery.toLowerCase());
    const matchesAuthority = selectedAuthority === 'all' || claim.authority === selectedAuthority;
    const matchesStatus = selectedStatus === 'all' || claim.status === selectedStatus;
    const matchesHistorical = showHistorical || claim.status !== 'HISTORICAL';
    return matchesSearch && matchesAuthority && matchesStatus && matchesHistorical;
  });

  const authorities = ['all', 'CRITICAL', 'HIGH', 'MEDIUM', 'LOW'];
  const statuses = ['all', 'PROTECTED', 'OBSERVED', 'LOCKED', 'REVIEW', 'HYPOTHESIS', 'CONFLICTING'];

  return (
    <div className="space-y-6">
      <Section
        title="Behavioral Constitution Workspace"
        description="Govern archaeological findings into protected constitutional claims with authority, confidence, and evidence."
      >
      {/* Constitution Header */}
      <div className="surface-card p-4">
        <div className="flex flex-col gap-4">
          <div className="flex items-center justify-between flex-wrap gap-4">
            <div className="flex items-center gap-4">
              <div className="flex items-center justify-center w-12 h-12 rounded-lg bg-[color-mix(in_srgb,_var(--color-trust-protected)_15%,_transparent)] text-[var(--color-trust-protected)]">
                <Shield size={24} />
              </div>
              <div>
                <h2 className="text-heading font-semibold">Behavioral Constitution v1.0</h2>
                <p className="text-body-sm text-[var(--color-text-muted)]">Active governing context for Change #184</p>
              </div>
            </div>
            <div className="flex items-center gap-4">
              <div className="flex items-center gap-2 px-3 py-1 rounded-lg bg-[color-mix(in_srgb,_var(--color-trust-certified)_15%,_transparent)] text-[var(--color-trust-certified)] border border-[color-mix(in_srgb,_var(--color-trust-certified)_30%,_transparent)]">
                <Lock size={14} />
                <span className="text-body-sm font-medium">ACTIVE</span>
              </div>
              <div className="flex items-center gap-2">
                <button className="btn btn--ghost btn-sm">
                  <Plus size={16} />
                  Add Claim
                </button>
                <button className="btn btn--primary btn-sm" onClick={() => onActivate?.()}>
                  <CheckCircle2 size={16} />
                  Activate Constitution
                </button>
              </div>
            </div>
          </div>
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 text-center">
            <div className="p-2 rounded-lg bg-[var(--color-surface)] border border-[var(--color-surface-border)]">
              <p className="text-display font-semibold font-mono text-[var(--color-trust-protected)]">32</p>
              <p className="text-caption text-[var(--color-text-muted)]">Protected</p>
            </div>
            <div className="p-2 rounded-lg bg-[var(--color-surface)] border border-[var(--color-surface-border)]">
              <p className="text-display font-semibold font-mono text-[var(--color-trust-observed)]">7</p>
              <p className="text-caption text-[var(--color-text-muted)]">Observed</p>
            </div>
            <div className="p-2 rounded-lg bg-[var(--color-surface)] border border-[var(--color-surface-border)]">
              <p className="text-display font-semibold font-mono text-[var(--color-trust-unverified)]">3</p>
              <p className="text-caption text-[var(--color-text-muted)]">Hypotheses</p>
            </div>
            <div className="p-2 rounded-lg bg-[var(--color-surface)] border border-[var(--color-surface-border)]">
              <p className="text-display font-semibold font-mono text-[var(--color-trust-violated)]">0</p>
              <p className="text-caption text-[var(--color-text-muted)]">Conflicts</p>
            </div>
          </div>
        </div>
      </div>

      {/* Filters */}
      <div className="surface-card p-4">
        <div className="flex flex-wrap items-center gap-4">
          <div className="relative flex-1 min-w-[250px]">
            <input
              type="text"
              name="claim-search"
              id="claim-search"
              placeholder="Search claims..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="input w-full pl-10"
            />
            <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-[var(--color-text-muted)]" />
          </div>
          <div className="flex items-center gap-1 p-1 rounded-lg bg-[var(--color-surface)] border border-[var(--color-surface-border)]">
            {authorities.map(a => (
              <button
                key={a}
                onClick={() => setSelectedAuthority(a)}
                className={cn(
                  'px-3 py-1.5 rounded-md text-caption font-medium transition-all',
                  selectedAuthority === a
                    ? 'bg-[color-mix(in_srgb,_var(--color-accent-primary)_10%,_transparent)] text-[var(--color-accent-primary)]'
                    : 'text-[var(--color-text-secondary)] hover:text-[var(--color-text-primary)]',
                )}
              >
                {a === 'all' ? 'All' : a}
              </button>
            ))}
          </div>
          <select
            name="claim-status"
            id="claim-status"
            value={selectedStatus}
            onChange={(e) => setSelectedStatus(e.target.value)}
            className="input w-36"
          >
            {statuses.map(s => <option key={s} value={s}>{s === 'all' ? 'All Status' : s}</option>)}
          </select>
          <label className="flex items-center gap-2 text-body-sm">
            <input
              type="checkbox"
              name="show-historical"
              id="show-historical"
              checked={showHistorical}
              onChange={(e) => setShowHistorical(e.target.checked)}
              className="w-4 h-4 rounded border-[var(--color-surface-border)] bg-[var(--color-surface)] text-[var(--color-accent-primary)] focus:ring-[var(--color-accent-primary)]"
            />
            Show Historical
          </label>
        </div>
      </div>
      </Section>

      {/* Claims List */}
      <Section title={`Claims (${filteredClaims.length} of ${mockClaims.length})`}>
        <div className="space-y-4">
          {filteredClaims.length === 0 ? (
            <EmptyState
              icon={<Shield size={32} />}
              title="No claims match filters"
              description="Adjust your search or filter criteria"
            />
          ) : (
            filteredClaims.map((claim) => (
              <Claim
                key={claim.id}
                claim={claim}
                variant="card"
                onSelect={(c) => {
                  setSelectedClaim(c);
                  openDrawer('claim', { ...c });
                }}
              />
            ))
          )}
        </div>
      </Section>

      {/* Historical vs Intent Context */}
      <Section title="Historical Memory vs Intent Memory">
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <div className="surface-card p-4">
            <div className="flex items-center gap-2 mb-4">
              <Clock size={20} className="text-[var(--color-trust-historical)]" />
              <h3 className="text-[0.875rem] font-semibold text-[var(--color-trust-historical)]">Historical Memory (What Happened)</h3>
            </div>
            <div className="space-y-3">
              {[
                'Session refresh allowed cross-tenant access (Incident #61)',
                'Auth provider v1 used JWT with 15min expiry',
                'Payment retry used fixed 1s interval',
                'Audit logs missing for auth state changes',
              ].map((item, i) => (
                <div key={i} className="flex items-center gap-3 p-3 bg-[var(--color-surface)] rounded-lg border border-[var(--color-surface-border)]">
                  <div className="flex-shrink-0 w-8 h-8 rounded-lg bg-[color-mix(in_srgb,_var(--color-trust-historical)_15%,_transparent)] text-[var(--color-trust-historical)] flex items-center justify-center">
                    <Clock size={16} />
                  </div>
                  <p className="text-body-sm">{item}</p>
                </div>
              ))}
            </div>
          </div>
          <div className="surface-card p-4">
            <div className="flex items-center gap-2 mb-4">
              <Settings size={20} className="text-[var(--color-trust-protected)]" />
              <h3 className="text-[0.875rem] font-semibold text-[var(--color-trust-protected)]">Intent Memory (What Should Happen)</h3>
            </div>
            <div className="space-y-3">
              {[
                'Tenant isolation MUST return 403 for cross-tenant access',
                'Authorization semantics MUST be provider-agnostic',
                'Session compatibility MUST be preserved',
                'Audit trail MUST be complete and immutable',
              ].map((item, i) => (
                <div key={i} className="flex items-center gap-3 p-3 bg-[var(--color-surface)] rounded-lg border border-[var(--color-surface-border)]">
                  <div className="flex-shrink-0 w-8 h-8 rounded-lg bg-[color-mix(in_srgb,_var(--color-trust-protected)_15%,_transparent)] text-[var(--color-trust-protected)] flex items-center justify-center">
                    <Shield size={16} />
                  </div>
                  <p className="text-body-sm font-medium">{item}</p>
                </div>
              ))}
            </div>
          </div>
        </div>
      </Section>
    </div>
  );
}