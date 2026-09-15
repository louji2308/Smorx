'use client';

import { useEffect } from 'react';
import { useAppStore } from '@/store/appStore';
import { AppShell } from '@/components/shell/AppShell';
import { DiscoverTab } from '@/components/discover/DiscoverTab';
import { GovernTab } from '@/components/govern/GovernTab';
import DefineTab from '@/components/define/DefineTab';
import AnalyzeTab from '@/components/analyze/AnalyzeTab';
import { DevelopTab } from '@/components/develop/DevelopTab';
import { VerifyTab } from '@/components/verify/VerifyTab';
import DecideTab from '@/components/decide/DecideTab';
import CertifyTab from '@/components/certify/CertifyTab';
import { createDemoJourney } from '@/lib/demo-journey';

export default function HomePage() {
  const { activeTab, project, domain, setProject, setRepository, setChange, setConstitution, seedDomain } = useAppStore();

  // Initialize with demo data if not set
  useEffect(() => {
    if (!project) {
      setProject({
        id: 'proj-1',
        name: 'Payments API',
        slug: 'payments-api',
        description: 'Core payment processing service with authentication and tenant isolation',
      });
      setRepository({
        id: 'repo-1',
        name: 'github.com/acme/payments',
        url: 'https://github.com/acme/payments',
        defaultBranch: 'main',
        lastInspectedAt: new Date().toISOString(),
      });
      setChange({
        id: 'change-1',
        externalId: '#184',
        title: 'Replace authentication provider and add passkey login',
        description: 'Migrate from legacy auth provider to new provider with passkey support while preserving password login, authorization, and session compatibility',
        status: 'OPEN',
        commitSha: 'e8d1a91c',
      });
      setConstitution({
        id: 'const-1',
        title: 'Behavioral Constitution v1.0',
        version: 1,
        status: 'ACTIVE',
        claimCount: 42,
        protectedCount: 32,
        locked: true,
      });
    }

    // Deterministic demo journey fixture for Change #184 (Define -> Certify)
    if (!domain.intentLedger) {
      seedDomain(createDemoJourney());
    }
  }, [project, domain.intentLedger, setProject, setRepository, setChange, setConstitution, seedDomain]);

  const renderTabContent = () => {
    switch (activeTab) {
      case 'Discover':
        return <DiscoverTab />;
      case 'Govern':
        return <GovernTab />;
      case 'Define':
        return <DefineTab />;
      case 'Analyze':
        return <AnalyzeTab />;
      case 'Develop':
        return <DevelopTab />;
      case 'Verify':
        return <VerifyTab />;
      case 'Decide':
        return <DecideTab />;
      case 'Certify':
        return <CertifyTab />;
      default:
        return <DiscoverTab />;
    }
  };

  return (
    <AppShell>
      {renderTabContent()}
    </AppShell>
  );
}