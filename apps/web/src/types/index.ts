/**
 * Core type definitions for the Software Evolution Intelligence System
 * Aligned with the behavioral data model from packages/behavior and packages/contracts
 */

// Trust state semantic types
export type TrustState =
  | 'OBSERVED'
  | 'PROTECTED'
  | 'LOCKED'
  | 'UNVERIFIED'
  | 'VIOLATED'
  | 'REPAIR_REQUIRED'
  | 'CERTIFIED'
  | 'HISTORICAL';

// Journey tabs
export type JourneyTab =
  | 'Discover'
  | 'Govern'
  | 'Define'
  | 'Analyze'
  | 'Develop'
  | 'Verify'
  | 'Decide'
  | 'Certify';

// Workflow state progression
export type WorkflowStage =
  | 'Discover'
  | 'Govern'
  | 'Define'
  | 'Analyze'
  | 'Develop'
  | 'Verify'
  | 'Decide'
  | 'Certify';

export interface WorkflowState {
  currentStage: WorkflowStage;
  completedStages: WorkflowStage[];
  lockedStages: WorkflowStage[];
  trustStatus: TrustState;
}

// Project context
export interface ProjectContext {
  id: string;
  name: string;
  slug: string;
  description?: string;
}

export interface RepositoryContext {
  id: string;
  name: string;
  url?: string;
  defaultBranch: string;
  lastInspectedAt?: string;
}

export interface ChangeContext {
  id: string;
  externalId?: string;
  title: string;
  description?: string;
  status: string;
  commitSha?: string;
}

export interface ConstitutionContext {
  id: string;
  title: string;
  version: number;
  status: ConstitutionStatus;
  claimCount: number;
  protectedCount: number;
  locked: boolean;
}

export type ConstitutionStatus = 'DRAFT' | 'REVIEW' | 'ACTIVE' | 'LOCKED';

// Global application state
export interface GlobalAppState {
  project: ProjectContext | null;
  repository: RepositoryContext | null;
  change: ChangeContext | null;
  constitution: ConstitutionContext | null;
  workflow: WorkflowState;
  activeTab: JourneyTab;
  selectedObject: SelectedObject | null;
  selectedEvidence: EvidenceItem | null;
  selectedClaim: ClaimItem | null;
  selectedGraphNode: GraphNodeData | null;
  drawerState: DrawerState;
  domain: DomainState;
}

export interface SelectedObject {
  type: 'behavior' | 'invariant' | 'incident' | 'dependency' | 'riskZone' | 'ghost' | 'evidence' | 'claim';
  id: string;
  data: Record<string, unknown>;
}

export interface DrawerState {
  isOpen: boolean;
  type: 'evidence' | 'claim' | 'provenance' | 'graph-node' | 'code-diff' | 'execution-trace' | 'certificate' | null;
  data: Record<string, unknown> | null;
}

// Evidence types from the behavioral model
export type EvidenceType =
  | 'STATIC_ANALYSIS'
  | 'DIFFERENTIAL_EXECUTION'
  | 'HISTORICAL_GHOST_REPLAY'
  | 'METAMORPHIC_CHECK'
  | 'ADVERSARIAL_SCENARIO'
  | 'MUTATION_TEST'
  | 'EXECUTION_TRACE'
  | 'TEST_RESULT'
  | 'RUNTIME_OBSERVATION'
  | 'REPOSITORY_SNAPSHOT'
  | 'MODEL_DECISION'
  | 'CERTIFICATE_BINDING';

export interface EvidenceItem {
  id: string;
  claimId?: string;
  evidenceType: EvidenceType;
  source: string;
  timestamp: string;
  provenance?: string;
  relatedTaskId?: string;
  relatedRunId?: string;
  relatedArtifact?: string;
  machineResult: Record<string, unknown>;
  hash: string;
}

export interface ClaimItem {
  id: string;
  claimId: string;
  statement: string;
  authority: string;
  confidence: number;
  status: TrustState;
  locked: boolean;
  createdAt: string;
  evidenceIds: string[];
}

// Behavioral object types
export type BehavioralObjectType = 'BEHAVIOR' | 'INVARIANT' | 'INCIDENT' | 'DEPENDENCY' | 'RISK_ZONE' | 'GHOST';

export interface BehavioralObject {
  id: string;
  objectType: BehavioralObjectType;
  name: string;
  description?: string;
  status: string;
  confidence?: number;
  protected?: boolean;
  discoveredAt?: string;
  repositoryId: string;
  claimIds?: string[];
  metadata?: Record<string, unknown>;
}

// Graph data for React Flow
export interface GraphNodeData {
  id: string;
  type: BehavioralObjectType;
  label: string;
  data: BehavioralObject;
  position: { x: number; y: number };
  trustState: TrustState;
}

export interface GraphEdgeData {
  id: string;
  source: string;
  target: string;
  type: string;
  label?: string;
  data?: Record<string, unknown>;
}

// Execution event
export interface ExecutionEvent {
  id: string;
  runId: string;
  agentRunId?: string;
  kind: 'COMMAND' | 'TEST' | 'BUILD' | 'VERIFICATION';
  command?: string;
  cwd?: string;
  exitCode?: number;
  stdout?: string;
  stderr?: string;
  durationMs?: number;
  status: 'PENDING' | 'RUNNING' | 'COMPLETED' | 'FAILED';
  startedAt?: string;
  finishedAt?: string;
  machineResult: Record<string, unknown>;
}

// Test result
export interface TestResult {
  id: string;
  executionId: string;
  name: string;
  status: 'passed' | 'failed' | 'skipped' | 'error';
  duration: number;
  stdout?: string;
  stderr?: string;
  file?: string;
  line?: number;
}

// Provenance link
export interface ProvenanceLink {
  id: string;
  evidenceId: string;
  type: 'task' | 'run' | 'agent_run' | 'subagent_run' | 'execution' | 'verification_case';
  targetId: string;
  targetLabel: string;
}

// Code diff
export interface CodeDiff {
  filePath: string;
  oldContent?: string;
  newContent?: string;
  hunks: DiffHunk[];
}

export interface DiffHunk {
  oldStart: number;
  oldLines: number;
  newStart: number;
  newLines: number;
  lines: DiffLine[];
}

export interface DiffLine {
  type: 'context' | 'add' | 'remove';
  content: string;
  lineNumber?: number;
}

// Context drawer types
export type DrawerType =
  | 'evidence'
  | 'claim'
  | 'provenance'
  | 'graph-node'
  | 'code-diff'
  | 'execution-trace'
  | 'certificate'
  | null;

export interface DrawerConfig {
  type: DrawerType;
  title: string;
  data: Record<string, unknown> | null;
  size?: 'sm' | 'md' | 'lg' | 'xl' | 'full';
}

// API response types
export interface ApiResponse<T> {
  data: T | null;
  error: ApiError | null;
  meta?: Record<string, unknown>;
}

export interface ApiError {
  code: string;
  message: string;
  details?: Record<string, unknown>;
}

// Pagination
export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  pageSize: number;
  hasMore: boolean;
}

// Archaeology specific types
export interface ArchaeologyRun {
  id: string;
  projectId: string;
  repositoryId: string;
  status: 'QUEUED' | 'RUNNING' | 'COMPLETED' | 'FAILED' | 'BLOCKED';
  startedAt: string;
  finishedAt?: string;
  evidenceCount: number;
  behaviorCount: number;
  invariantCount: number;
  incidentCount: number;
  ghostCount: number;
  riskZoneCount: number;
  dependencyCount: number;
}

export interface ArchaeologyFindings {
  behaviors: BehavioralObject[];
  invariants: BehavioralObject[];
  incidents: BehavioralObject[];
  dependencies: BehavioralObject[];
  riskZones: BehavioralObject[];
  ghosts: BehavioralObject[];
  evidence: EvidenceItem[];
}

// Constitution types
export interface ConstitutionClaimItem {
  id: string;
  constitutionId: string;
  category: string;
  rule: string;
  severity: 'CRITICAL' | 'HIGH' | 'MEDIUM' | 'LOW';
  position: number;
  version: number;
  locked: boolean;
  authority: string;
  confidence: number;
  status: TrustState;
  evidenceIds: string[];
  affectedSoftware?: string[];
  governanceConsequence?: string;
  verificationRequirements?: string[];
}

export interface ConstitutionVersion {
  id: string;
  version: number;
  title: string;
  status: ConstitutionStatus;
  claimCount: number;
  protectedCount: number;
  observedCount: number;
  hypothesisCount: number;
  conflictCount: number;
  ratifiedAt?: string;
  locked: boolean;
}

// Intent types
export type IntentKind = 'ADD' | 'REPLACE' | 'PRESERVE' | 'PERFORMANCE' | 'SECURITY';

export interface IntentItem {
  id: string;
  intentLedgerId: string;
  statement: string;
  kind: IntentKind;
  priority: 'CRITICAL' | 'HIGH' | 'NORMAL' | 'LOW';
  status: 'PENDING' | 'CONFIRMED' | 'LOCKED' | 'SUPERSEDED';
  authorized: boolean;
  sourceRef?: string;
}

// Verification types
export type VerificationModality =
  | 'STATIC_ANALYSIS'
  | 'DIFFERENTIAL_EXECUTION'
  | 'HISTORICAL_GHOST_REPLAY'
  | 'METAMORPHIC_CHECK'
  | 'ADVERSARIAL_SCENARIO'
  | 'MUTATION_TEST';

export interface VerificationCase {
  id: string;
  verificationPlanId: string;
  name: string;
  kind: VerificationModality;
  description?: string;
  method?: string;
  expected?: string;
  threshold?: number;
  status: 'PENDING' | 'RUNNING' | 'PASSED' | 'FAILED' | 'BLOCKED';
  independent: boolean;
  owningModule?: string;
  evidenceIds: string[];
  result?: {
    passed: number;
    failed: number;
    skipped: number;
    durationMs: number;
  };
}

export interface VerificationPlan {
  id: string;
  changeId: string;
  title: string;
  claimIds: string[];
  modalities: VerificationModality[];
  status: 'DRAFT' | 'LOCKED' | 'COMPLETED' | 'SUPERSEDED';
  locked: boolean;
  createdAt: string;
  cases: VerificationCase[];
}

// Behavioral Delta
export interface BehavioralDelta {
  id: string;
  changeId: string;
  candidatePatchId: string;
  claimId: string;
  classification: 'ADDED' | 'REMOVED' | 'ALTERED' | 'UNCHANGED' | 'UNEXPLAINED';
  authorized?: boolean;
  intentAlignment: 'PENDING' | 'ALIGNED' | 'MISALIGNED';
  observedAt: string;
  evidenceIds: string[];
  metric?: string;
  baselineValue?: string;
  candidateValue?: string;
  magnitude?: number;
}

// Repair Package
export interface RepairPackage {
  id: string;
  failureId: string;
  expectedBehavior: string;
  observedBehavior: string;
  affectedClaimId: string;
  evidenceIds: string[];
  suspectedPath: string;
  requiredOutcome: string;
  acceptanceCriteria: string[];
  constraints: string[];
  createdAt: string;
  status: 'CREATED' | 'IN_PROGRESS' | 'COMPLETED' | 'FAILED';
}

// Certificate
export interface Certificate {
  id: string;
  certificateId: string;
  changeId: string;
  commit: string;
  behavioralDeltaId: string;
  verificationEvidenceIds: string[];
  intentLedgerId: string;
  protectedBehaviors: string[];
  candidatePatchId: string;
  environment: Record<string, unknown>;
  dependencyState: Record<string, unknown>;
  status: 'DRAFT' | 'ISSUED' | 'CERTIFIED' | 'REVOKED';
  certificateHash: string;
  evidenceTraversal: string[];
  issuedAt: string;
}

// Intent Ledger (Define)
export interface IntentLedger {
  id: string;
  changeId: string;
  title: string;
  status: 'DRAFT' | 'CONFIRMED' | 'LOCKED';
  background: string;
  objectives: string[];
  constraints: string[];
  acceptanceCriteria: string[];
  authorizedBy: string;
  authorizationId: string;
  lockedAt?: string;
}

export type IntentDimension = 'PRESERVE' | 'REPLACE' | 'ADD' | 'PERFORMANCE' | 'SECURITY';

// Semantic impact surface (Analyze)
export interface ImpactSurface {
  id: string;
  kind: 'FILE' | 'CLAIM' | 'DEPENDENCY';
  ref: string;
  label: string;
  direction: 'REPLACE' | 'ADD' | 'TOUCH' | 'REMOVE' | 'UNTOUCHED';
  risk: 'LOW' | 'MEDIUM' | 'HIGH';
  claimId?: string;
  reasoning: string;
}

export interface ImpactRiskZone {
  id: string;
  name: string;
  claimIds: string[];
  risk: 'LOW' | 'MEDIUM' | 'HIGH';
  reasoning: string;
}

export interface ImpactAnalysis {
  id: string;
  changeId: string;
  status: 'PENDING' | 'COMPUTED' | 'LOCKED';
  summary: string;
  surfaces: ImpactSurface[];
  riskZones: ImpactRiskZone[];
  verificationContractId: string;
}

// Candidate patch (Develop)
export interface CandidatePatch {
  id: string;
  changeId: string;
  seq: number;
  title: string;
  status: 'GENERATED' | 'REPAIRED' | 'RECOMMENDED' | 'SUPERSEDED';
  filesChanged: string[];
  additions: number;
  deletions: number;
  sandboxId: string;
  constitutionBarrier: string[];
  execution: ExecutionEvent[];
  traces: SandboxTrace[];
  failureHistory: PatchFailure[];
  supersedes?: string;
}

export interface SandboxTrace {
  id: string;
  command: string;
  cwd: string;
  exitCode: number;
  stdout: string;
  stderr: string;
  durationMs: number;
}

export interface PatchFailure {
  id: string;
  runId: string;
  classification:
    | 'syntax/build failure'
    | 'unit-test failure'
    | 'integration failure'
    | 'environment/dependency failure'
    | 'timeout'
    | 'permission failure'
    | 'tool failure'
    | 'ambiguous result'
    | 'acceptance-criterion failure'
    | 'safety/policy block';
  evidenceId: string;
  notes: string;
}

// Verification run (Verify)
export type VerificationRunStatus = 'PENDING' | 'RUNNING' | 'COMPLETED' | 'FAILED';

export interface VerificationRun {
  id: string;
  planId: string;
  label: string;
  status: VerificationRunStatus;
  startedAt: string;
  finishedAt?: string;
  cases: VerificationCase[];
}

// Behavioral delta decision (Decide)
export interface DecisionEntry {
  deltaId: string;
  claimId: string;
  claimLabel: string;
  classification: BehavioralDelta['classification'];
  alignment: 'PENDING' | 'ALIGNED' | 'MISALIGNED';
  magnitude: number;
  reasoning: string;
  evidenceIds: string[];
}

export interface DecisionSummary {
  id: string;
  changeId: string;
  status: 'REVIEWING' | 'DECIDED' | 'REPAIR_REQUIRED';
  entries: DecisionEntry[];
  summary: string;
}

// Global journey domain state (fixture-driven, deterministic; backend wiring is a later phase)
export interface DomainState {
  intentLedger: IntentLedger | null;
  intents: IntentItem[];
  impact: ImpactAnalysis | null;
  verificationContract: VerificationPlan | null;
  verificationRuns: VerificationRun[];
  candidatePatches: CandidatePatch[];
  decision: DecisionSummary | null;
  certificate: Certificate | null;
}