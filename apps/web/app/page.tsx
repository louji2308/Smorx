'use client';

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
import { OnboardingForm } from '@/components/onboarding/OnboardingForm';

export default function HomePage() {
  const { activeTab, project } = useAppStore();

  if (!project) {
    return <OnboardingForm />;
  }

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
      <div key={activeTab} className="animate-fade-up">
        {renderTabContent()}
      </div>
    </AppShell>
  );
}
