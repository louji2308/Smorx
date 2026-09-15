import { create } from 'zustand';
import { persist, subscribeWithSelector } from 'zustand/middleware';
import type {
  GlobalAppState,
  ProjectContext,
  RepositoryContext,
  ChangeContext,
  ConstitutionContext,
  WorkflowState,
  WorkflowStage,
  JourneyTab,
  TrustState,
  SelectedObject,
  DrawerState,
  EvidenceItem,
  ClaimItem,
  GraphNodeData,
  DomainState,
} from '@/types';

interface AppStore extends GlobalAppState {
  // Actions
  setProject: (project: ProjectContext | null) => void;
  setRepository: (repository: RepositoryContext | null) => void;
  setChange: (change: ChangeContext | null) => void;
  setConstitution: (constitution: ConstitutionContext | null) => void;
  setWorkflowState: (workflow: Partial<WorkflowState>) => void;
  setActiveTab: (tab: JourneyTab) => void;
  setSelectedObject: (object: SelectedObject | null) => void;
  setSelectedEvidence: (evidence: EvidenceItem | null) => void;
  setSelectedClaim: (claim: ClaimItem | null) => void;
  setSelectedGraphNode: (node: GraphNodeData | null) => void;
  openDrawer: (type: DrawerState['type'], data: Record<string, unknown>) => void;
  closeDrawer: () => void;
  completeStage: (stage: WorkflowStage) => void;
  lockStage: (stage: WorkflowStage) => void;
  setTrustStatus: (status: TrustState) => void;
  seedDomain: (domain: DomainState) => void;
  updateDomain: (partial: Partial<DomainState>) => void;
  reset: () => void;
}

const initialState: GlobalAppState = {
  project: null,
  repository: null,
  change: null,
  constitution: null,
  workflow: {
    currentStage: 'Discover',
    completedStages: [],
    lockedStages: [],
    trustStatus: 'HISTORICAL',
  },
  activeTab: 'Discover',
  selectedObject: null,
  selectedEvidence: null,
  selectedClaim: null,
  selectedGraphNode: null,
  drawerState: {
    isOpen: false,
    type: null,
    data: null,
  },
  domain: {
    intentLedger: null,
    intents: [],
    impact: null,
    verificationContract: null,
    verificationRuns: [],
    candidatePatches: [],
    decision: null,
    certificate: null,
  },
};

export const useAppStore = create<AppStore>()(
  subscribeWithSelector(
    persist(
      (set, get) => ({
        ...initialState,

        setProject: (project) => set({ project }),
        setRepository: (repository) => set({ repository }),
        setChange: (change) => set({ change }),
        setConstitution: (constitution) => set({ constitution }),

        setWorkflowState: (workflow) =>
          set((state) => ({
            workflow: { ...state.workflow, ...workflow },
          })),

        setActiveTab: (tab) => set({ activeTab: tab }),

        setSelectedObject: (object) => set({ selectedObject: object }),
        setSelectedEvidence: (evidence) => set({ selectedEvidence: evidence }),
        setSelectedClaim: (claim) => set({ selectedClaim: claim }),
        setSelectedGraphNode: (node) => set({ selectedGraphNode: node }),

        openDrawer: (type, data) =>
          set({
            drawerState: { isOpen: true, type, data },
          }),

        closeDrawer: () =>
          set({
            drawerState: { isOpen: false, type: null, data: null },
          }),

        completeStage: (stage) =>
          set((state) => {
            const completedStages = state.workflow.completedStages.includes(stage)
              ? state.workflow.completedStages
              : [...state.workflow.completedStages, stage];
            const stages = ['Discover', 'Govern', 'Define', 'Analyze', 'Develop', 'Verify', 'Decide', 'Certify'] as WorkflowStage[];
            const currentIndex = stages.indexOf(stage);
            const nextStage = stages[currentIndex + 1] || stage;
            return {
              workflow: {
                ...state.workflow,
                completedStages,
                currentStage: nextStage,
              },
              activeTab: nextStage,
            };
          }),

        lockStage: (stage) =>
          set((state) => ({
            workflow: {
              ...state.workflow,
              lockedStages: state.workflow.lockedStages.includes(stage)
                ? state.workflow.lockedStages
                : [...state.workflow.lockedStages, stage],
            },
          })),

        setTrustStatus: (status) =>
          set((state) => ({
            workflow: {
              ...state.workflow,
              trustStatus: status,
            },
          })),

        seedDomain: (domain) => set({ domain }),
        updateDomain: (partial) =>
          set((state) => ({ domain: { ...state.domain, ...partial } })),

        reset: () => set(initialState),
      }),
      {
        name: 'smorx-app-state',
        partialize: (state) => ({
          project: state.project,
          repository: state.repository,
          change: state.change,
          constitution: state.constitution,
          workflow: state.workflow,
          activeTab: state.activeTab,
        }),
      }
    )
  )
);

// Selectors for common use cases
export const useProject = () => useAppStore((state) => state.project);
export const useRepository = () => useAppStore((state) => state.repository);
export const useChange = () => useAppStore((state) => state.change);
export const useConstitution = () => useAppStore((state) => state.constitution);
export const useWorkflow = () => useAppStore((state) => state.workflow);
export const useActiveTab = () => useAppStore((state) => state.activeTab);
export const useSelectedObject = () => useAppStore((state) => state.selectedObject);
export const useSelectedEvidence = () => useAppStore((state) => state.selectedEvidence);
export const useSelectedClaim = () => useAppStore((state) => state.selectedClaim);
export const useSelectedGraphNode = () => useAppStore((state) => state.selectedGraphNode);
export const useDrawer = () => useAppStore((state) => state.drawerState);
export const useTrustStatus = () => useAppStore((state) => state.workflow.trustStatus);