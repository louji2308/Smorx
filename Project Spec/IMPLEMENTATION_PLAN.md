# SOFTWARE EVOLUTION INTELLIGENCE SYSTEM
# SINGLE IMPLEMENTATION PLAN
## Nebius x NVIDIA Global AI Hackathon — Track 1

**Document status:** Master implementation blueprint
**Implementation mode:** Orchestrated, evidence-first, parallel-agent engineering
**Primary product identity:** Behavioral software engineering system
**Primary narrative:** HISTORY → GOVERNANCE → INTENT → IMPACT → VERIFICATION → CHANGE → EVIDENCE → ALIGNMENT → CERTIFICATION → MEMORY

---

## 0. PURPOSE OF THIS DOCUMENT

This document is the execution blueprint for implementing the complete system established by the project architecture, product demo specification, Track 1 requirements/contracts, and selected technology stack.

It is intentionally organized as an implementation sequence rather than a product-description document.

The system must be built as **one product accumulating state across a governed software-evolution lifecycle**, not as 21 disconnected screens. The eight journey tabs and 21 primary product moments are operational workspaces inside one persistent system.

The implementation must preserve the following central proposition:

> The Coding Agent can propose a software change. It cannot decide by itself that the change is safe. Evidence establishes what changed. Intent establishes what was allowed. Independent verification establishes what can be trusted.

The Track 1 engineering loop is:

```text
TASK
  ↓
UNDERSTAND
  ↓
INSPECT
  ↓
PLAN
  ↓
ACT
  ↓
EXECUTE
  ↓
OBSERVE
  ↓
DIAGNOSE
  ↓
PATCH
  ↓
RETEST
  ↓
VERIFY
  ↓
REPORT
```

Every implementation phase in this document must preserve that larger loop and must introduce measurable, testable behavior rather than merely adding UI.

---

# 1. SOURCE-OF-TRUTH PRINCIPLES

The implementation is governed by the uploaded project specifications. The most important established requirements are:

- The system operates on a real repository.
- Code execution occurs in a Nebius Token Factory Sandbox.
- At least one NVIDIA open-source model participates meaningfully in runtime reasoning.
- The agent inspects, plans, modifies, executes, tests, observes, diagnoses, iterates, and verifies.
- Execution results are machine-authoritative over model assertions.
- Important mutations are attributable to task → decision → tool call → result.
- Failed executions become evidence and drive the next reasoning cycle.
- Execution and repair loops are bounded.
- Candidate code is never equivalent to certified code.
- Independent verification is a separate trust boundary.
- Evidence is collected, normalized, linked, interpreted, and fused at claim level.
- Behavioral Delta and Intent Alignment remain conceptually distinct.
- Failure is preserved as historical evidence rather than overwritten.
- Certification binds implementation, environment, dependency state, verification, and behavior.
- Certification feeds new evidence back into behavioral memory.

These requirements are reflected directly in the architecture and contracts. fileciteturn2file0L61-L137 fileciteturn2file2L1065-L1141

---

# 2. NON-NEGOTIABLE MASTER INVARIANTS

These are system laws. They are not optional implementation preferences.

## I1 — No evidence, no success

A verified claim requires objective supporting evidence.

## I2 — Model cannot fabricate execution

A model statement such as “tests pass” is never authoritative. The recorded execution result is authoritative.

## I3 — Every consequential mutation is attributable

```text
Task
→ Decision
→ Tool Call
→ Execution Result
→ Mutation
```

## I4 — Failure is information

```text
Failure
→ Evidence
→ Diagnosis
→ Next Decision
```

## I5 — The agent can stop safely

Every autonomous loop supports:

```text
Continue
Retry
Rollback
Stop / Block
```

## I6 — Completion is objective

The system does not terminate with “looks good.” It terminates with acceptance criteria backed by evidence or an explicit unrecoverable/blocked state.

## I7 — Candidate ≠ Certified

The trust transition is:

```text
Candidate
→ Independent Investigation
→ Evidence
→ Intent Alignment
→ Certification
```

Never:

```text
Candidate → Certified
```

## I8 — Failure ≠ Deletion

A repaired result does not erase the original failure. Historical failure remains part of behavioral memory.

## I9 — Locked objects stay locked

Once downstream work begins, the following remain immutable unless the entire workflow intentionally creates a new version:

- Behavioral Constitution
- Intent Ledger
- Semantic Impact Map
- Verification Plan

## I10 — Orchestrator owns delegation

The main agent must plan the work before delegation, spawn multiple independent subagents when parallelism exists, run them concurrently, collect their outputs, reconcile conflicts, and only then choose the next wave.

## I11 — Subagents do not silently mutate shared truth

Specialist agents return evidence/artifacts/recommendations through defined interfaces. Persistent state transitions occur through the orchestrator/control plane.

## I12 — Phase gates are mandatory

A phase is not “done” because code exists. It is done only when its implementation, tests, integration checks, evidence, and exit criteria have passed.

---

# 3. GLOBAL ORCHESTRATION MODEL

## 3.1 Main Orchestrator Responsibilities

The orchestrator is the system's control plane. It must:

1. Read current project state.
2. Read the phase contract.
3. Build a dependency graph for the phase.
4. Identify independent workstreams.
5. Spawn multiple subagents in parallel whenever dependencies allow.
6. Track each subagent's state.
7. Collect structured outputs.
8. Detect contradictions or missing evidence.
9. Delegate integration/reconciliation work where appropriate.
10. Validate outputs against contracts/policies.
11. Persist evidence and execution traces.
12. Decide the next phase/wave.
13. Stop or block when safety, evidence, or progress requirements are not satisfied.

## 3.2 Required Subagent Lifecycle

Each subagent invocation must conceptually include:

```text
AGENT ASSIGNMENT
→ CONTEXT PACK
→ OBJECTIVE
→ INPUTS
→ ALLOWED TOOLS
→ CONSTRAINTS
→ EXPECTED ARTIFACT
→ EXECUTION
→ RESULT
→ EVIDENCE
→ CONFIDENCE
→ NEXT RECOMMENDATION
```

## 3.3 Parallel Delegation Rule

When tasks are independent:

```text
                 ORCHESTRATOR
                /      |      \
               /       |       \
        SUBAGENT A SUBAGENT B SUBAGENT C
               \       |       /
                \      |      /
                  RESULT FUSION
```

Do not implement:

```text
A → wait → B → wait → C
```

unless B genuinely depends on A's result.

## 3.4 Dependency-Aware Parallelism

The orchestrator must distinguish:

- independent tasks → parallel;
- data-dependent tasks → sequential only where necessary;
- merge/reconciliation tasks → after the parallel wave;
- shared-state mutations → serialized through an explicit integration gate.

## 3.5 Chrome DevTools MCP Role

Chrome DevTools MCP is an engineering/debugging capability available throughout implementation. It is not reserved for the final day.

Use it for:

- browser/runtime inspection;
- console error detection;
- network request inspection;
- API payload verification;
- SSE/WebSocket inspection;
- performance traces;
- rendering/debugging investigation;
- browser state validation;
- responsive/device behavior checks;
- final regression testing.

The current Chrome DevTools-for-agents tooling supports MCP-based live-browser control/inspection, and the current stable tooling includes network and performance capabilities. citeturn209117search1turn209117search8

When connecting to an authenticated browser session, the agent must treat the browser as a sensitive execution environment because the DevTools agent can inspect and interact with the active session. Use isolated profiles for testing wherever possible. citeturn209117search0turn209117search1

---

# 4. GLOBAL PHASE TEMPLATE

Every phase below follows this implementation contract.

### A. Phase Objective
What capability becomes real.

### B. Inputs
Contracts, data, services, and prior phase outputs.

### C. Implementation Steps
Ordered engineering work.

### D. Parallel Subagent Wave
Multiple specialist agents to run simultaneously where independent.

### E. Integration Wave
Reconcile and connect results.

### F. Phase Testing
Unit/contract + integration + behavioral/evidence tests.

### G. Chrome DevTools Validation
Browser/runtime checks where applicable.

### H. Exit Gate
Objective conditions required before proceeding.

### I. Deliverables
Concrete repository/database/config/UI artifacts.

---

# PHASE 0 — MASTER CONTRACTS, REPOSITORY FOUNDATION & EXECUTION GOVERNANCE

## Objective
Create the engineering foundation that prevents later architectural drift.

## Inputs
All five source documents and the master contracts.

## Implementation Steps

### 0.1 Create repository structure

Establish a clean monorepo or clearly separated application structure:

```text
/apps
  /web
  /api

/packages
  /contracts
  /agent-runtime
  /tools
  /evidence
  /behavior
  /verification
  /ui

/infrastructure
  /docker
  /nebius

/tests
  /unit
  /integration
  /e2e
  /security
  /evaluation

/docs
/scripts
```

Exact folder names may be adjusted during implementation, but ownership boundaries must remain explicit.

### 0.2 Encode contracts

Create typed schemas for:

- Task
- Action
- Tool invocation
- Execution result
- Failure
- Evidence
- Claim
- Behavioral object
- Intent
- Verification plan
- Candidate patch
- Behavioral delta
- Repair package
- Certificate
- Agent run
- Subagent run
- Phase gate

### 0.3 Implement state machine

Minimum agent states:

```text
CREATED
INSPECTED
PLANNED
EXECUTING
OBSERVED
FAILED
ITERATING
VERIFIED
BLOCKED
```

These states must be represented in code rather than only in UI copy. fileciteturn2file0L11-L57

### 0.4 Implement loop controls

Configurable values must exist for:

- max iterations;
- max runtime;
- max command count;
- max repair attempts;
- no-progress threshold;
- per-tool timeout;
- per-agent timeout;
- total phase timeout.

### 0.5 Implement immutable-state/version conventions

Define how locked objects receive versions and how downstream references are tied to exact versions.

### 0.6 Establish development quality gates

Minimum:

- formatter;
- linter;
- type checking;
- test runner;
- build command;
- environment validation;
- secret scanning;
- dependency audit.

## Parallel Subagent Wave

**Architecture Agent** — boundaries and ownership.

**Contract Agent** — schemas/state/validation.

**DevOps Agent** — local/dev deployment foundation.

**QA Agent** — baseline testing conventions.

**Documentation Agent** — engineering conventions and ADR structure.

## Integration Wave
Orchestrator validates that every major domain maps to one owner and every contract has a machine-readable representation.

## Phase Testing

- schema validation;
- state transition tests;
- invalid-transition tests;
- bounded-loop tests;
- build/lint/type tests;
- environment boot tests.

## Chrome DevTools Validation
Create a minimal health page and verify:

- browser loads;
- no console errors;
- health endpoint succeeds;
- frontend can reach backend;
- no unexpected failed network requests.

## Exit Gate
The repository boots cleanly, contracts compile, state-machine tests pass, and the basic frontend/backend health path works.

## Deliverables

- repository structure;
- contract package;
- state machine;
- quality tooling;
- base CI checks;
- engineering ADRs;
- phase-gate script.

---

# PHASE 1 — NEBIUS + NVIDIA INFRASTRUCTURE LAYER

## Objective
Make the actual hackathon infrastructure operational before building the product around mocks.

The selected architecture uses NeMo/Nemotron for reasoning, Nebius Token Factory for inference, and Nebius Token Factory Sandboxes for real repository execution. fileciteturn3file0L493-L520

## Implementation Steps

### 1.1 Token Factory connectivity

Implement:

- environment configuration;
- secure API key loading;
- model endpoint abstraction;
- model request/response schemas;
- retry policy;
- timeout policy;
- request tracing.

### 1.2 Model router

Implement an explicit router.

Conceptually:

```text
Task Classifier
    ↓
Simple → lightweight Nemotron
Normal → stronger Nemotron
Hard → highest reasoning Nemotron
```

Model selection must be explainable by task requirements rather than model size alone. fileciteturn2file1L546-L576

### 1.3 Sandbox adapter

Implement the application abstraction around:

- sandbox creation;
- sandbox state;
- command execution;
- file operations;
- checkpoints;
- rollback;
- branch/candidate state;
- cleanup.

Use the Nebius sandbox primitive instead of building custom execution infrastructure. fileciteturn3file0L118-L123

### 1.4 MCP/SDK decision

Implement a single internal `SandboxExecutionPort` so the rest of the application is independent of whether the actual adapter uses the official Sandbox SDK, Contree MCP, or another supported mechanism.

Primary implementation path should favor the supported Nebius primitive actually available in the development environment.

### 1.5 NeMo integration

Integrate the chosen NVIDIA orchestration/evaluation capabilities without creating a parallel custom agent framework where NVIDIA tooling already solves the requirement.

Current NeMo documentation positions the platform around agent lifecycle management, evaluation, observation, optimization, and tool/model integration. citeturn177875search0turn177875search1

## Parallel Subagent Wave

**Nebius Infrastructure Agent**

**Nemotron Integration Agent**

**Sandbox Agent**

**NeMo Runtime Agent**

**Infrastructure Observability Agent**

## Integration Wave

Build one real path:

```text
FastAPI
→ Agent Runtime
→ Nemotron
→ Sandbox
→ Command
→ Machine Result
```

## Phase Testing

1. Create sandbox.
2. Inspect sandbox.
3. Run a deterministic command.
4. Capture exit code/stdout/stderr/duration.
5. Write/read a file.
6. Checkpoint.
7. Make a controlled change.
8. Roll back.
9. Destroy/cleanup.
10. Confirm real Nemotron response.

## Chrome DevTools Validation

Inspect:

- API health requests;
- model-related backend status;
- SSE or WebSocket stream behavior if used;
- failed API requests;
- console errors.

## Exit Gate
A real repository can be placed into a real Nebius execution environment and a machine-verifiable command result returns successfully.

## Deliverables

- model adapter;
- model router;
- sandbox adapter;
- execution service;
- secure configuration;
- infrastructure health tests.

---

# PHASE 2 — BEHAVIORAL DATA MODEL & PERSISTENCE

## Objective
Create the durable knowledge layer that differentiates this project from a generic coding agent.

The system stores historical software reality, behavioral findings, governance state, evidence, intent, verification results, failure history, and certificates. fileciteturn2file3L1186-L1286

## Implementation Steps

### 2.1 Core entities

Implement relational models for at least:

```text
Project
Repository
Change
Task
Run
AgentRun
SubagentRun
Behavior
Invariant
Incident
Dependency
RiskZone
Ghost
Evidence
Claim
Constitution
ConstitutionClaim
IntentLedger
IntentItem
SemanticImpact
VerificationPlan
VerificationCase
CandidatePatch
Execution
Failure
BehavioralDelta
IntentAlignment
RepairPackage
Certificate
MemoryUpdate
```

### 2.2 Evidence identity

Each evidence object must have:

- stable identity;
- type;
- timestamp;
- source;
- provenance;
- related task/run;
- related artifact;
- machine result;
- hash where appropriate.

### 2.3 Ownership model

Persist which object owns each semantic truth:

- Constitution owns governance;
- Intent Ledger owns user intent;
- Semantic Impact Map owns impact;
- Verification Plan owns verification contract;
- Candidate Patch owns development output;
- Verification owns independent investigation;
- Behavioral Delta owns observed difference;
- Certificate owns certification.

### 2.4 Event and trace model

Every consequential event becomes a structured event.

### 2.5 Versioning

Locked objects must be immutable references. New versions create new identities rather than silently mutating historical state.

## Parallel Subagent Wave

**Database Agent**

**Behavioral Model Agent**

**Evidence/Provenance Agent**

**Versioning Agent**

**Persistence/Test Agent**

## Integration Wave
Build a seed dataset representing the demo scenario:

```text
Payments API
Change #184
AUTH-017
Ghost #221
Failure F-183
```

This dataset must remain clearly marked as demo/scenario data rather than being confused with real repository execution evidence.

## Phase Testing

- create/read/update/version tests;
- lock tests;
- provenance traversal tests;
- foreign-key/reference tests;
- historical preservation tests;
- evidence deduplication tests;
- certificate relationship tests.

## Exit Gate
The full lifecycle can be represented and queried without losing ownership, version, provenance, or historical evidence.

## Deliverables

- PostgreSQL schema;
- migration system;
- repository/data access layer;
- evidence event schema;
- seed/demo data.

---

# PHASE 3 — ORCHESTRATOR + PARALLEL MULTI-AGENT RUNTIME

## Objective
Implement the central intelligence architecture: an orchestrator that plans, delegates parallel work, collects evidence, synthesizes results, and controls the workflow.

The project architecture identifies specialist capabilities for archaeology, knowledge, intent, impact, coding, verification, evidence, repair, and certification. These are logical roles rather than nine permanently running services. fileciteturn3file0L29-L76

## Implementation Steps

### 3.1 Agent runtime abstraction

Create a common interface:

```text
AgentCapability
AgentContext
AgentAssignment
AgentResult
AgentEvidence
AgentFailure
```

### 3.2 Orchestrator state

The orchestrator tracks:

- current phase;
- current workflow state;
- active wave;
- pending tasks;
- dependencies;
- agent results;
- evidence;
- conflicts;
- next transition.

### 3.3 Parallel task graph

Implement a dependency-aware execution graph.

Example:

```text
                 Inspect Repository
                        |
          +-------------+-------------+
          |             |             |
       Analyze       Analyze       Analyze
       Tests         Deps          Runtime
          |             |             |
          +-------------+-------------+
                        |
                  Result Fusion
```

### 3.4 Specialist capabilities

Implement logical capabilities first:

- Archaeology
- Knowledge
- Intent
- Impact
- Coding
- Verification
- Evidence
- Repair
- Certification

### 3.5 Tool permission model

Every agent receives only the tools required for its role.

### 3.6 Evidence-first result schema

A subagent result cannot consist only of prose. It must return structured claims/evidence/artifacts.

### 3.7 Failure and conflict handling

The orchestrator must support:

- subagent timeout;
- partial results;
- contradictory findings;
- failed specialist;
- retry;
- replacement specialist;
- human review/block.

### 3.8 Parallelism telemetry

Record:

- wave ID;
- parallel tasks;
- start/end timestamps;
- dependencies;
- duration;
- outputs;
- failures.

## Parallel Subagent Wave

**Orchestrator Agent** — lifecycle/control.

**Agent Runtime Agent** — execution abstraction.

**Parallel Scheduler Agent** — dependency graph/concurrency.

**Tool Routing Agent** — controlled tool access.

**Trace/Evaluation Agent** — instrumentation.

## Integration Wave
Run a synthetic workflow with multiple independent agents and prove the orchestrator does not serially execute independent tasks.

## Phase Testing

### Orchestration tests

- parallel start;
- result collection;
- dependency enforcement;
- conflict detection;
- timeout;
- cancellation;
- retry;
- no-progress block;
- state transition correctness.

### Evidence tests

Every subagent result must be attributable to:

`assignment → agent → action/tool → result`.

Current NeMo evaluation capabilities can score agent outcomes and trajectories, and current observability capabilities can capture model calls, tool calls, errors, and end-to-end traces. These should be leveraged for evaluation/instrumentation rather than replaced with a completely custom telemetry system. citeturn177875search2turn177875search9

## Chrome DevTools Validation

Use browser execution only after the orchestrator API is available. Inspect:

- event-stream ordering;
- concurrent task status;
- duplicate network requests;
- frontend state updates;
- console failures.

## Exit Gate
The orchestrator demonstrably runs independent work in parallel, fuses results, records trace state, handles failures, and can block safely.

## Deliverables

- orchestrator runtime;
- specialist capability interfaces;
- parallel scheduler;
- task graph;
- agent telemetry;
- orchestrator tests.

---

# PHASE 4 — TOOL LAYER, POLICY LAYER & AGENT CONTROL PLANE

## Objective
Give agents controlled, auditable engineering tools rather than unrestricted execution.

The required tool contracts include repository inspection, file read/write, command execution, test execution, sandbox creation/checkpoint/rollback, with machine-readable execution results. fileciteturn2file0L141-L276

## Implementation Steps

### 4.1 Repository inspection tool

Return:

- files;
- directories;
- metadata;
- relevant repository state.

### 4.2 File tools

Implement:

```text
file.read
file.write
file.create
file.delete
```

All mutations record path, operation, reason, before/after context, and resulting state.

### 4.3 Command execution

Record:

- command;
- working directory;
- timeout;
- exit code;
- stdout;
- stderr;
- duration;
- environment metadata;
- run ID.

### 4.4 Test runner

Normalize outcomes into:

```text
passed
failed
skipped
error
```

### 4.5 Sandbox controls

Implement:

- create;
- checkpoint;
- rollback;
- branch/candidate where supported;
- cleanup.

### 4.6 Policy engine

Before a consequential tool call:

```text
MODEL DECISION
→ POLICY
→ APPROVED / DENIED / HUMAN APPROVAL
→ TOOL
```

### 4.7 Human control

Implement:

```text
START
PAUSE
APPROVE
ABORT
ROLLBACK
```

High-risk operations can transition to approval-required state. fileciteturn2file1L883-L913

## Parallel Subagent Wave

**Repository Tool Agent**

**Sandbox Tool Agent**

**Policy Agent**

**Execution Evidence Agent**

**Human-Control Agent**

## Integration Wave
Connect all tools to the orchestrator through one policy-controlled registry.

## Phase Testing

- malformed arguments;
- nonexistent file;
- invalid path;
- destructive operation;
- long-running command;
- timeout;
- rollback;
- permission failure;
- duplicate execution;
- policy denial;
- human approval;
- evidence attribution.

## Chrome DevTools Validation
Verify the browser cannot directly invoke privileged operations without backend authorization.

Inspect network requests for:

- missing auth;
- excessive payloads;
- duplicate mutation requests;
- leaked secrets.

## Exit Gate
No model-generated action can bypass policy or execute without a structured decision and recorded result.

## Deliverables

- tool registry;
- policy engine;
- tool contracts;
- human intervention state;
- tool-level tests.

---

# PHASE 5 — PERSISTENT APPLICATION SHELL + DESIGN SYSTEM

## Objective
Create the one-system UI shell in which the 21 product moments live.

The product specification explicitly requires one persistent application shell with eight journey tabs and contextual inspectors rather than separate pages for every small state. fileciteturn1file7L179-L260

## Implementation Steps

### 5.1 Shell

Implement:

- left navigation;
- project context;
- repository context;
- change context;
- constitution state;
- workflow state;
- trust state;
- global evidence affordance.

### 5.2 Eight journey tabs

```text
Discover
Govern
Define
Analyze
Develop
Verify
Decide
Certify
```

### 5.3 Shared visual language

Implement semantic states:

```text
OBSERVED
PROTECTED
LOCKED
UNVERIFIED
VIOLATED
REPAIR REQUIRED
CERTIFIED
```

Critical states must not be diluted by excessive color or decorative UI.

### 5.4 Shared components

Create reusable components for:

- state badge;
- claim;
- evidence item;
- provenance link;
- execution event;
- test result;
- graph node;
- evidence inspector;
- claim inspector;
- code diff;
- context drawer;
- phase transition.

### 5.5 Contextual inspector architecture

Never create primary pages for:

- provenance;
- individual evidence;
- claim detail;
- risk;
- test modality detail;
- execution traces;
- certificate evidence.

Use contextual drawers/panels instead. fileciteturn2file4L1500-L1516

## Parallel Subagent Wave

**Frontend Architecture Agent**

**Design System Agent**

**Interaction/Motion Agent**

**Browser QA Agent**

**Accessibility Agent**

## Integration Wave
Build the shell with real state from the backend instead of static mocked navigation states.

## Phase Testing

- component tests;
- routing tests;
- state rendering tests;
- accessibility checks;
- keyboard navigation;
- loading/error/empty states;
- responsive layout tests.

## Chrome DevTools Validation

Use Chrome DevTools MCP continuously:

- console;
- DOM/accessibility inspection;
- network;
- rendering;
- responsive emulation;
- performance spot checks.

## Exit Gate
The application feels like one persistent system and the shell can display authoritative backend state without console or network errors.

## Deliverables

- production shell;
- design token system;
- shared component library;
- inspector framework;
- navigation/state infrastructure.

---

# PHASE 6 — DISCOVER + GOVERN

## Objective
Implement the first evidence-to-governance half of the journey.

## Product Moments

1. Archaeology Launch
2. Archaeology Evidence Workspace
3. Behavioral Knowledge Graph
4. Behavioral Constitution Workspace
5. Constitution Activation & Active State

These are the first five of the 21 primary product moments. fileciteturn1file7L217-L225

## Implementation Steps

### 6.1 Software Archaeology

Input:

- repository;
- Git history;
- runtime observations;
- tests;
- incidents;
- dependencies.

Produce:

- behaviors;
- invariants;
- incidents;
- dependencies;
- couplings;
- risk zones;
- Ghost candidates;
- evidence records.

### 6.2 Archaeology orchestration

Run independent extraction tasks in parallel:

```text
Source analysis
Git analysis
Test analysis
Dependency analysis
Runtime analysis
Incident analysis
```

### 6.3 Evidence normalization

Normalize all findings into the behavioral model.

### 6.4 Knowledge Graph

Implement graph relationships for:

- behavior;
- software component;
- dependency;
- incident;
- invariant;
- Ghost;
- evidence.

Use React Flow for graph interaction, consistent with the selected stack. fileciteturn1file2L56-L70

### 6.5 Constitution generation

Transform archaeological findings into claims with:

- authority;
- confidence;
- evidence;
- protected state;
- historical/intention distinction;
- verification requirements.

### 6.6 Constitution activation

Activation creates immutable governing context.

## Parallel Subagent Wave

**Archaeology Agent**

**Git History Agent**

**Runtime/Test Agent**

**Dependency Agent**

**Knowledge Graph Agent**

**Constitution Agent**

## Integration Wave
The orchestrator fuses findings and creates the versioned Behavioral Constitution.

## Phase Testing

- extraction correctness;
- evidence-to-behavior linkage;
- graph relationship integrity;
- authority/confidence independence;
- constitution lock;
- historical-vs-governed state tests.

## Chrome DevTools Validation

The UI must render:

- archaeology progress;
- evidence counts;
- graph selection;
- claim inspector;
- locked constitution state.

Inspect network payloads against persisted objects.

## Exit Gate
A real repository can produce evidence-backed behavioral memory and a locked Behavioral Constitution.

## Deliverables

- archaeology pipeline;
- graph;
- behavioral findings;
- constitution engine;
- first five product moments.

---

# PHASE 7 — DEFINE + ANALYZE

## Objective
Turn human intent into an immutable, testable verification contract before coding begins.

## Product Moments

6. Change Definition
7. Intent Ledger & Constitutional Constraints
8. Semantic Impact Workspace
9. Verification Contract & Pre-Coding Lock

## Implementation Steps

### 7.1 Change definition

Normalize the human request into:

```text
objective
repository
constraints
acceptance criteria
priority
execution budget
```

### 7.2 Intent compilation

Decompose the request into:

```text
ADD
REPLACE
PRESERVE
PERFORMANCE
SECURITY
```

### 7.3 Constitutional constraint resolution

Map change intent to relevant protected claims.

### 7.4 Lock Intent Ledger

After confirmation:

```text
Intent Ledger → LOCKED
```

### 7.5 Semantic impact analysis

Analyze:

- behaviors;
- code components;
- functions;
- dependencies;
- data flows;
- risk zones;
- historical Ghosts;
- protected behaviors.

### 7.6 Verification plan generation

Generate tests and investigation modalities required to validate the affected behaviors.

### 7.7 Lock verification

The Verification Plan becomes immutable before the Coding Agent is invoked.

## Parallel Subagent Wave

**Intent Agent**

**Constitution Mapping Agent**

**Semantic Impact Agent**

**Verification Planning Agent**

**Risk Analysis Agent**

## Integration Wave

The orchestrator resolves findings and creates one locked pre-coding context object:

```text
Human Request
+ Intent Ledger
+ Behavioral Constitution
+ Semantic Impact Map
+ Verification Plan
```

## Phase Testing

- incomplete task rejected;
- intent ambiguity detected;
- protected behavior mapping;
- impact relationship tests;
- lock immutability;
- verification coverage tests;
- unauthorized post-lock mutation tests.

## Chrome DevTools Validation
Verify:

- locked state renders consistently;
- UI cannot mutate locked objects through client-side tampering;
- network calls are authorized server-side.

## Exit Gate
The system cannot invoke the Coding Agent unless the required pre-coding objects are valid and locked.

## Deliverables

- change compiler;
- intent ledger;
- semantic impact engine;
- verification planner;
- pre-coding lock gate.

---

# PHASE 8 — DEVELOP / CODING AGENT / REAL SANDBOX LOOP

## Objective
Implement the actual autonomous Track 1 engineering loop.

The system must write, run, and test code inside the designated sandbox workflow. The MVP contract explicitly requires repository loading, sandbox creation, Nemotron inference, inspection, planning, file modification, command/test execution, failure observation, iterative repair, final verification, and execution tracing. fileciteturn2file2L962-L988

## Product Moment

10. Development Plane / Candidate Patch

## Implementation Steps

### 8.1 Task handoff

Pass the immutable pre-coding context to the Coding Agent.

### 8.2 Repository inspection

The Coding Agent inspects:

- structure;
- dependencies;
- tests;
- configuration;
- entry points;
- relevant implementation.

### 8.3 Explicit plan generation

The agent returns:

- interpretation;
- affected components;
- files;
- implementation strategy;
- tests;
- completion criteria.

### 8.4 Sandbox creation

Create an isolated working state derived from the canonical repository.

### 8.5 Candidate patch generation

The Coding Agent modifies repository files using controlled tools.

### 8.6 Execution

Run appropriate:

- unit tests;
- integration tests;
- build;
- lint;
- type checks;
- task-specific commands.

### 8.7 Failure observation

Normalize execution failures into the predefined failure taxonomy:

```text
F1 build/syntax
F2 unit test
F3 integration
F4 environment/dependency
F5 timeout
F6 permission
F7 tool
F8 ambiguous
F9 acceptance criterion
F10 safety/policy
```

### 8.8 Diagnosis

The Coding Agent must distinguish:

`observed failure ≠ root cause`.

### 8.9 Iterative patching

Use evidence from execution to create the next decision.

### 8.10 Optional multi-candidate path

Where useful, branch:

```text
BASE
 ├── Candidate A
 ├── Candidate B
 └── Candidate C
```

and compare objectively. This is one of the strongest differentiators identified in the Track 1 materials. fileciteturn2file2L1015-L1061

## Parallel Subagent Wave

**Repository Analysis Agent**

**Coding Agent**

**Command/Test Agent**

**Debugging/Reflection Agent**

**Browser/DevTools Agent** where the repository exposes a browser runtime.

When multi-candidate search is activated:

**Candidate A Coding Agent**

**Candidate B Coding Agent**

**Candidate C Coding Agent**

must run independently and concurrently.

## Integration Wave
The orchestrator selects the candidate/iteration based on actual machine evidence, not model confidence.

## Phase Testing

- task normalization;
- inspection completeness;
- plan completeness;
- file mutation attribution;
- command correctness;
- exit-code authority;
- failure propagation;
- repair iteration;
- loop bounds;
- rollback;
- candidate comparison.

## Chrome DevTools Validation
Where the software has a UI/runtime path:

- launch app;
- inspect console;
- inspect network;
- identify runtime errors;
- correlate UI failure to backend/execution events.

## Exit Gate
A real task can produce a real candidate patch in a real Nebius Sandbox, including an observable success or failure and at least one adaptive execution cycle.

## Deliverables

- Coding Agent capability;
- sandbox-driven edit/run/test loop;
- execution trace;
- candidate patch artifacts;
- iterative repair control.

---

# PHASE 9 — INDEPENDENT VERIFICATION PLANE

## Objective
Create the trust boundary where the candidate is independently investigated.

The architecture explicitly separates the Coding Agent's development plane from the independent verification plane. fileciteturn3file0L129-L172

## Product Moments

11. Independent Verification Lab
12. Verification Control Center
13. Claim Evidence & Fusion

## Implementation Steps

### 9.1 Trust boundary

Ensure the verifier does not inherit authority from the Coding Agent.

### 9.2 Static analysis

Analyze candidate source for relevant issues and affected paths.

### 9.3 Differential execution

Compare baseline and candidate behavior.

### 9.4 Historical Ghost replay

Replay relevant historical scenarios.

### 9.5 Metamorphic checks

Validate expected invariants under controlled transformations.

### 9.6 Adversarial scenarios

Actively attempt to violate protected behavior.

### 9.7 Mutation testing

Introduce targeted mutations to determine whether the verification strategy can detect regressions.

### 9.8 Evidence collection

Each module must emit its own evidence.

Do not reduce verification to one opaque score.

### 9.9 Claim Evidence Fusion

Fuse evidence by:

- authority;
- relevance;
- provenance;
- severity;
- confidence;
- evidence type.

### 9.10 Claim-level assessment

Possible outputs:

```text
SUPPORTING
CONTRADICTING
INSUFFICIENT
CONFLICTING
```

## Parallel Subagent Wave

These verification modules must run concurrently where their inputs permit:

**Static Analysis Agent**

**Differential Execution Agent**

**Historical Ghost Agent**

**Metamorphic Agent**

**Adversarial Agent**

**Mutation Agent**

Then a separate:

**Evidence Fusion Agent**

runs after the module wave completes.

## Integration Wave
Produce claim-level assessments such as:

```text
AUTH-017
  ← Ghost #221 FAIL
  ← Adversarial #14 FAIL
  ← Static Analysis WARNING
  → VIOLATED
```

## Phase Testing

- independent execution reproducibility;
- module isolation;
- evidence provenance;
- conflicting-evidence handling;
- claim fusion correctness;
- verifier cannot mutate candidate without authorization;
- verification plan immutability.

Current NeMo evaluation capabilities are suitable for task/trajectory evaluation and can preserve trial evidence, while NeMo observability can retain detailed traces. Use these capabilities to measure verification-agent behavior where appropriate. citeturn177875search2turn177875search9

## Chrome DevTools Validation
For browser-facing regression cases:

- compare browser network behavior before/after;
- inspect console errors;
- replay user flows;
- capture performance evidence;
- record concrete runtime observations.

## Exit Gate
The system can prove a candidate's behavior using multiple independent verification mechanisms and fuse those results into claim-level evidence.

## Deliverables

- verification lab;
- verification modules;
- control center;
- evidence collector;
- claim fusion engine.

---

# PHASE 10 — BEHAVIORAL DELTA + INTENT ALIGNMENT + REPAIR

## Objective
Determine what actually changed, whether the change was allowed, and generate an evidence-driven repair when it was not.

## Product Moments

14. Behavioral Delta & Intent Alignment
15. Certification Decision
16. Repair Package & Coding Repair

The product specification explicitly requires the behavioral delta, intent alignment, and repair decision to remain separate concepts even though they can occupy one integrated workspace.

## Implementation Steps

### 10.1 Behavioral Delta

Compare baseline and candidate behaviors.

Output:

- added behavior;
- removed behavior;
- altered behavior;
- unchanged protected behavior;
- unexplained changes.

### 10.2 Intent Alignment

Map each meaningful delta to the Intent Ledger.

Determine:

```text
AUTHORIZED
UNAUTHORIZED
UNEXPLAINED
```

### 10.3 Certification decision

A candidate with unauthorized critical change becomes:

```text
REPAIR REQUIRED
```

### 10.4 Repair package

The repair package must contain:

- failure ID;
- expected behavior;
- observed behavior;
- affected claim;
- evidence;
- suspected path;
- required outcome;
- relevant acceptance criteria;
- constraints.

### 10.5 Evidence-driven repair

The Coding Agent receives the structured repair package, not merely the sentence “fix it.”

### 10.6 Candidate Patch #2

Repair occurs in a controlled new/branched sandbox state.

The original Candidate Patch #1 and Failure F-183 remain preserved.

## Parallel Subagent Wave

**Behavioral Delta Agent**

**Intent Alignment Agent**

**Certification Decision Agent**

**Repair Analysis Agent**

When several repair strategies are plausible:

**Repair Candidate A Agent**

**Repair Candidate B Agent**

**Repair Candidate C Agent**

run concurrently and are objectively compared.

## Integration Wave

Create the causal chain:

```text
Evidence
→ Failure
→ Suspected Path
→ Repair Strategy
→ Candidate Patch #2
```

## Phase Testing

- delta classification;
- authorized/un­authorized classification;
- preservation constraints;
- repair-package completeness;
- candidate repair comparison;
- repaired candidate provenance;
- failure preservation.

## Chrome DevTools Validation
When UI behavior is part of the affected behavior:

- reproduce the failing browser flow;
- capture the before/after Network requests;
- inspect Console;
- compare browser-visible behavior;
- confirm repair did not create frontend regressions.

## Exit Gate
The system can deterministically decide whether a behavioral change was authorized and can generate a structured repair loop for unauthorized changes.

## Deliverables

- Behavioral Delta engine;
- Intent Alignment engine;
- Certification Decision engine;
- Repair Package;
- Candidate Patch #2 lifecycle.

---

# PHASE 11 — RE-VERIFICATION + CERTIFICATION + CONTINUOUS MEMORY

## Objective
Restore trust independently, create the evidence-bound certificate, and close the software-memory loop.

## Product Moments

17. Independent Re-Verification
18. Failure Archaeology & Future Memory
19. Final Intent Alignment
20. Change Certificate
21. Continuous Behavioral Evolution

The final product must return certification outcomes to behavioral memory rather than stopping at a success page. fileciteturn1file14L1316-L1335

## Implementation Steps

### 11.1 Independent re-verification

Repeat relevant verification modules against Candidate Patch #2 under the locked conditions.

### 11.2 Before/after proof

Produce evidence such as:

```text
Ghost #221
FAIL → PASS

Tenant isolation
FAIL → PASS

Adversarial tenant switch
FAIL → PASS
```

### 11.3 Final intent alignment

Required final condition:

```text
Unexplained changes = 0
Critical unauthorized changes = 0
```

or an explicitly non-certifiable outcome.

### 11.4 Failure archaeology

Persist:

- Failure F-183;
- Ghost #221;
- claim relationships;
- root cause evidence;
- repair evidence;
- verification evidence.

### 11.5 Certificate generation

Bind:

```text
Change
→ Commit
→ Intent
→ Protected Behaviors
→ Behavioral Delta
→ Verification Evidence
→ Candidate Implementation
→ Environment
→ Dependency State
→ Certificate Identity
```

### 11.6 Certificate integrity

Generate hashes/identifiers as appropriate and make the final artifact machine-verifiable.

### 11.7 Merge authorization

Merge becomes available only when certification criteria and review requirements are satisfied.

### 11.8 Memory update

On merge/certification:

```text
Certified Change
→ New Behavioral Evidence
→ Updated Behavioral Knowledge
→ Preserved Failure
→ Updated Verification Knowledge
→ Future Change Context
```

## Parallel Subagent Wave

**Re-Verification Agent**

**Failure Archaeology Agent**

**Certificate Integrity Agent**

**Certification Agent**

**Memory Evolution Agent**

## Integration Wave
Generate the final evidence-bound certificate and update persistent behavioral memory without mutating prior evidence.

## Phase Testing

- re-verification reproducibility;
- certificate binding;
- certificate tamper detection;
- provenance traversal;
- failure preservation;
- merge gate;
- memory update correctness;
- future retrieval of preserved evidence.

## Chrome DevTools Validation
Inspect the final certificate UI and verify:

- certificate loads from backend state;
- all evidence drawers resolve;
- no failed requests;
- no console errors;
- final merge transition does not lose state.

## Exit Gate
A successful workflow produces a machine-verifiable certificate and expands the behavioral memory while preserving historical failures.

## Deliverables

- re-verification engine;
- certificate generator;
- certificate integrity model;
- failure archaeology;
- memory update pipeline;
- product moments 17–21.

---

# PHASE 12 — FULL SYSTEM INTEGRATION, AUTONOMOUS WORKFLOW & DEMO RELIABILITY

## Objective
Combine all implemented capabilities into one autonomous, repeatable, judge-ready workflow.

## Implementation Steps

### 12.1 Real end-to-end orchestration

Run the complete lifecycle with real services:

```text
Task
→ Discover
→ Govern
→ Define
→ Analyze
→ Lock
→ Develop
→ Verify
→ Decide
→ Repair
→ Re-verify
→ Certify
→ Merge
→ Memory
```

### 12.2 Deterministic demo scenario

Implement one primary scenario matching the designed experience:

- repository: Payments API;
- change: authentication provider + passkey migration;
- protected tenant isolation/authorization/session behavior;
- Candidate Patch #1 introduces the intentionally discoverable regression;
- independent verification detects it;
- evidence drives repair;
- Candidate Patch #2 is independently re-verified;
- certification closes the loop.

The demo specification intentionally uses the failure as the central proof moment rather than hiding it. fileciteturn1file13L899-L985

### 12.3 Parallel candidate strategy

When a target issue has plausible alternate solutions, enable the stronger differentiated path:

```text
BASE
├── Candidate A
├── Candidate B
└── Candidate C
       ↓
parallel tests/benchmarks
       ↓
objective comparison
       ↓
best candidate
```

### 12.4 State replay

A complete workflow must be replayable from the stored run/evidence graph.

### 12.5 Failure injection

Create test modes that intentionally force:

- test failure;
- timeout;
- tool failure;
- policy block;
- conflicting evidence;
- no progress.

### 12.6 Demo reliability controls

Implement:

- run resume;
- explicit reset;
- phase replay;
- cleanup of stale sandboxes;
- idempotent workflow endpoints where possible;
- controlled demo data isolation.

### 12.7 Performance optimization

Reduce:

- redundant model calls;
- redundant database queries;
- duplicate evidence processing;
- unnecessary browser renders;
- unnecessary sandbox creation.

Cache deterministic archaeology/evidence artifacts where safe. The selected technical architecture explicitly recommends structured evidence reuse and avoiding model calls for computations ordinary code can handle. fileciteturn3file2L605-L620

## Parallel Subagent Wave

**Full-Stack Integration Agent**

**Autonomous Workflow Agent**

**Reliability Agent**

**Performance Agent**

**Demo Scenario Agent**

**Browser/DevTools Agent**

**Evaluation Agent**

## Integration Wave
Run multiple complete workflows from clean state and compare traces.

## Phase Testing

- end-to-end success;
- end-to-end failure/recovery;
- resume/replay;
- idempotency;
- stale-state handling;
- candidate branch comparison;
- trace completeness;
- memory persistence.

## Chrome DevTools Validation

Use DevTools MCP to inspect:

- every important route;
- API request sequence;
- SSE/WebSocket behavior;
- console cleanliness;
- runtime errors;
- page performance;
- memory-heavy screens;
- graph rendering;
- navigation transitions.

## Exit Gate
The complete system can repeatedly execute the designed story on real infrastructure without hidden manual intervention and produce the same class of evidence/trust transitions.

## Deliverables

- integrated application;
- reliable demo mode;
- repeatable end-to-end scenario;
- performance baseline;
- production-like deployment.

---

# PHASE 13 — SYSTEM SECURITY OPTIMIZATION

## Objective
Perform dedicated security hardening across the application, agent runtime, sandbox, browser, data plane, and supply chain.

Security is a fundamental part of the product because the system executes repository code. The source requirements explicitly call for isolation of filesystem, processes, network, credentials, environment variables, and resource usage, with no unrestricted host credentials exposed to repository code. fileciteturn2file2L862-L879

## Security Principles

### 13.1 Sandbox isolation

Validate:

- filesystem boundaries;
- process boundaries;
- network policy;
- credential isolation;
- environment-variable isolation;
- resource quotas;
- timeout enforcement.

### 13.2 Agent isolation

Protect against:

- tool abuse;
- prompt injection;
- malicious repository instructions;
- unauthorized tool use;
- policy bypass;
- cross-run state contamination;
- cross-project information leakage.

### 13.3 Data security

Validate:

- secret storage;
- secret access scope;
- database credentials;
- storage permissions;
- logging redaction;
- error-message redaction;
- certificate data integrity.

### 13.4 API security

Test:

- request authentication;
- authorization;
- replay;
- invalid state transition;
- direct object reference manipulation;
- rate limiting where required;
- oversized payloads;
- malformed JSON.

### 13.5 Frontend security

Use Chrome DevTools to inspect:

- network requests;
- response headers;
- client-exposed environment data;
- local/session storage;
- cookies;
- CSP/security header behavior where applicable;
- unexpected third-party traffic.

### 13.6 Browser-session safety

Do not connect the DevTools agent to personal/authenticated profiles for routine testing. Use an isolated browser profile where possible because DevTools for agents can inspect and act on the connected session. citeturn209117search0

### 13.7 Supply-chain security

Validate:

- dependency lockfiles;
- known vulnerabilities;
- untrusted post-install scripts;
- container image provenance;
- exposed secrets in Git history;
- unnecessary permissions.

### 13.8 Security observability

Every security block should become evidence:

```text
Attempt
→ Policy
→ Block
→ Evidence
→ Security Event
```

## Parallel Security Subagent Wave

**Sandbox Security Agent**

**Agent Runtime Security Agent**

**API/Application Security Agent**

**Data/Secrets Security Agent**

**Supply Chain Agent**

**Browser/Chrome Security Agent**

**Threat Modeling Agent**

## Integration Wave

Create a single prioritized security backlog:

```text
CRITICAL
HIGH
MEDIUM
LOW
```

No critical item may be knowingly left without either remediation or a documented blocking decision.

## Phase Testing

### Offensive tests

- malicious tool argument;
- malicious repository file;
- command injection;
- path traversal;
- credential exfiltration attempt;
- environment-variable exposure;
- cross-sandbox access;
- unauthorized state mutation;
- browser session misuse;
- policy bypass.

### Defensive verification

Confirm each attack path produces:

`blocked → recorded → attributable`

## Chrome DevTools Security Validation

Perform dedicated inspections of:

- Network tab;
- Console;
- Application/storage;
- cookies;
- request/response payloads;
- headers;
- browser state;
- runtime exceptions.

## Exit Gate

- no critical unresolved security issue;
- no secret exposed to client code;
- sandbox isolation validated;
- privileged actions policy-controlled;
- security failures observable;
- browser test profile isolated.

## Deliverables

- security hardening changes;
- threat model;
- security regression suite;
- secret/config hardening;
- documented risk register.

---

# PHASE 14 — FINAL END-TO-END TEST, CHROME DEVTOOLS INVESTIGATION & TOTAL OPTIMIZATION

## Objective
This is the final engineering gate. The project is tested from clean start to certified merge using real infrastructure, real agent orchestration, real browser execution, and real machine evidence.

No planned feature work follows this phase. Any defect discovered here becomes a controlled fix/re-test cycle and then re-enters the relevant gate.

## 14.1 Clean-room preparation

Create a clean release candidate:

- clean branch/tag;
- clean environment configuration;
- clean browser test profile;
- clean database/demo namespace;
- clean or controlled sandbox state;
- pinned dependency state;
- release build.

## 14.2 Final full journey

Execute:

```text
USER TASK
↓
ORCHESTRATOR
↓
PARALLEL REPOSITORY/CONTEXT INVESTIGATION
↓
PLAN
↓
LOCKED INTENT
↓
PARALLEL IMPACT ANALYSIS
↓
VERIFICATION LOCK
↓
CODING AGENT
↓
NEBIUS SANDBOX
↓
WRITE
↓
RUN
↓
TEST
↓
FAIL
↓
OBSERVE
↓
DIAGNOSE
↓
PARALLEL INDEPENDENT VERIFICATION
↓
EVIDENCE FUSION
↓
BEHAVIORAL DELTA
↓
INTENT ALIGNMENT
↓
REPAIR
↓
NEW/BRANCHED SANDBOX
↓
RE-VERIFY
↓
FINAL ALIGNMENT
↓
CERTIFICATE
↓
MERGE
↓
EXPANDED BEHAVIORAL MEMORY
```

## 14.3 Parallel final QA agents

### Agent A — Full E2E Workflow

Runs the canonical scenario from beginning to end.

### Agent B — Backend/API QA

Validates every request, response, status code, state transition, and error path.

### Agent C — Chrome DevTools QA

Uses the live browser to inspect:

- Network;
- Console;
- Performance;
- Application;
- runtime state;
- request sequencing;
- SSE/WebSocket behavior;
- rendering behavior.

### Agent D — Sandbox QA

Validates actual code execution, test execution, isolation, rollback, and cleanup.

### Agent E — Orchestrator QA

Validates:

- parallel delegation;
- dependency ordering;
- result fusion;
- retry;
- block;
- cancellation;
- no-progress detection.

### Agent F — Security Regression QA

Re-runs the security suite after final integration.

### Agent G — Performance QA

Finds:

- slow API calls;
- expensive model calls;
- duplicate queries;
- unnecessary render cycles;
- graph performance issues;
- slow initial load;
- large bundle paths;
- long-running sandbox operations.

### Agent H — Evidence/Certificate QA

Ensures the final result has complete provenance and evidence linkage.

## 14.4 Chrome DevTools final protocol

Chrome DevTools must be used as an actual final diagnostic instrument rather than merely opening the browser.

### Network pass

Inspect all critical flows for:

- unexpected 4xx/5xx;
- failed preflights;
- duplicate requests;
- incorrect request ordering;
- oversized payloads;
- missing streaming termination;
- incorrect caching behavior;
- leaked data;
- unexpected third-party requests.

### Console pass

Target:

```text
0 uncaught exceptions
0 unhandled promise rejections
0 unexplained errors
```

Warnings may remain only if understood, documented, and non-blocking.

### Performance pass

Inspect critical screens and transitions for:

- slow first render;
- expensive graph updates;
- repeated renders;
- long scripting tasks;
- network dependency bottlenecks;
- unnecessary model-driven UI work.

Current Chrome DevTools for agents supports automated performance-oriented workflows and Lighthouse-style quality audits, making those suitable candidates for this final phase. citeturn209117search6

### Runtime/UI pass

Walk every primary product moment and confirm:

- correct current phase;
- correct trust state;
- correct locked/unlocked controls;
- correct evidence count;
- correct transition;
- correct loading/error behavior;
- contextual inspector behavior.

### State integrity pass

Manually and programmatically attempt:

- browser refresh at critical states;
- duplicate clicks;
- back navigation;
- stale tab state;
- direct URL navigation to locked states;
- repeated mutation requests.

## 14.5 Final contract audit

Execute an automated audit against every master contract:

```text
C01 real repository
C02 Nebius execution
C03 NVIDIA model participation
C04 inspect/modify/execute/test
C05 execution authority
C06 failure observability
C07 evidence-driven iteration
C08 objective verification
C09 mutation attribution
C10 bounded execution
C11 recovery
C12 final evidence
```

No contract is marked PASS based on human interpretation alone; wherever possible, each PASS should point to machine evidence.

## 14.6 Final Track 1 audit

Verify:

- correct track;
- actual sandbox execution;
- actual write;
- actual run;
- actual test;
- actual failure observation;
- adaptive iteration;
- final verification;
- public source repository;
- public demo;
- documented NVIDIA/Nebius usage.

The hackathon source requirements emphasize that “agent” behavior must be demonstrable through real write/run/test execution rather than a code-generation wrapper. fileciteturn0file2L131-L175

## 14.7 Final observability audit

The execution trace should answer:

> What did the agent do, which tools did it use, what happened, where did it fail, what evidence was produced, why did it choose the next action, and why is the final result trusted?

NeMo's current agent evaluation and observability systems are well suited to task trajectory and tool-use measurement and detailed trace inspection. citeturn177875search2turn177875search9

## 14.8 Final optimization loop

For every issue discovered:

```text
OBSERVE
→ CLASSIFY
→ FIX
→ RUN TARGETED TEST
→ RUN REGRESSION TEST
→ RE-INSPECT WITH DEVTOOLS
→ ACCEPT / BLOCK
```

No optimization may silently alter a locked trust contract.

## 14.9 Final release gate

Release only when all are true:

```text
[PASS] Build
[PASS] Types
[PASS] Lint
[PASS] Unit tests
[PASS] Integration tests
[PASS] E2E tests
[PASS] Security regression
[PASS] Sandbox execution
[PASS] Agent orchestration
[PASS] Independent verification
[PASS] Evidence fusion
[PASS] Certificate integrity
[PASS] Chrome console audit
[PASS] Chrome network audit
[PASS] Chrome performance audit
[PASS] Contract audit
[PASS] Track 1 audit
```

## Final Deliverables

- release candidate;
- final test report;
- final trace/evidence bundle;
- security report;
- performance report;
- certificate validation report;
- demo-ready environment;
- submission-ready repository.

---

# 5. CROSS-PHASE TESTING STRATEGY

Testing is a continuous layer, not a Phase 14 activity.

## Level 1 — Unit/Contract

Tests the smallest deterministic behaviors.

Examples:

- schema validation;
- state transitions;
- tool contracts;
- policy rules;
- delta calculations;
- claim fusion;
- certificate hash.

## Level 2 — Integration

Tests subsystem boundaries.

Examples:

- FastAPI ↔ orchestrator;
- orchestrator ↔ Nemotron;
- orchestrator ↔ sandbox;
- evidence ↔ PostgreSQL;
- frontend ↔ API;
- verification ↔ candidate state.

## Level 3 — Behavioral/Evidence

Tests whether the system produces the correct behavioral evidence.

Examples:

- Ghost replay;
- adversarial authorization;
- differential execution;
- mutation detection;
- intent alignment.

## Level 4 — Browser/Runtime

Chrome DevTools MCP validates actual behavior in the live browser.

## Level 5 — Agent Evaluation

Evaluate:

- tool selection;
- plan quality;
- trajectory quality;
- recovery behavior;
- goal completion;
- evidence completeness.

Current NeMo evaluation supports task-driven agent trials with both outcome and trajectory evidence. citeturn177875search2turn177875search5

## Level 6 — Security

Adversarial tests continuously challenge the policy/sandbox boundary.

---

# 6. REQUIRED AGENT ROLE CATALOG

These are logical roles. They do not need to be independent permanent services.

## Core Control

**Orchestrator Agent**

Owns planning, delegation, state transitions, evidence fusion, and phase gates.

## Discovery

**Archaeology Agent**

Finds actual software behavior from source/history/runtime/test evidence.

**Knowledge Agent**

Builds/updates behavioral relationships.

## Governance

**Intent Agent**

Compiles human request into explicit intent.

**Constitution Agent**

Maintains governed/protected behavior.

## Analysis

**Impact Agent**

Computes semantic blast radius and risk.

**Verification Planning Agent**

Creates the pre-coding verification contract.

## Development

**Coding Agent**

Implements the candidate patch through controlled tools.

**Reflection/Debugging Agent**

Reasons from execution failure and selects next actions.

## Verification

**Static Analysis Agent**

**Differential Execution Agent**

**Historical Ghost Agent**

**Metamorphic Agent**

**Adversarial Agent**

**Mutation Agent**

## Evidence

**Evidence Agent**

Normalizes and fuses evidence at claim level.

## Repair

**Repair Agent**

Consumes failure evidence and proposes repair strategies.

## Certification

**Certification Agent**

Builds the evidence-bound certification artifact after all required gates.

## Quality/Safety

**Chrome DevTools QA Agent**

**Security Agent**

**Performance Agent**

**Evaluation Agent**

---

# 7. PARALLEL EXECUTION POLICY

The implementation agent must follow these rules in every phase.

## Rule P1
Identify independent work before spawning agents.

## Rule P2
Spawn at least two independent specialists when two or more independent workstreams exist.

## Rule P3
Do not use one subagent for every task merely because delegation is available.

## Rule P4
Do not run independent subagents sequentially.

## Rule P5
Do not let multiple agents directly mutate the same shared persistent state concurrently.

Instead:

```text
Parallel investigation
→ Artifact results
→ Orchestrator integration
→ Controlled mutation
```

## Rule P6
A failed subagent does not automatically mean phase failure if another valid evidence path exists.

## Rule P7
Conflicting subagent results become a first-class reconciliation event.

## Rule P8
The orchestrator must preserve every material subagent output required for audit/replay.

---

# 8. MODEL ROUTING IMPLEMENTATION POLICY

Use model complexity routing rather than “largest model everywhere.”

The selected architecture recommends a lightweight model for high-volume extraction/classification, a stronger model for semantic reasoning/repair, and the strongest model only for difficult architectural/final reasoning. fileciteturn3file2L583-L601

## Suggested routing

### Lightweight tier

Use for:

- repository summarization;
- metadata extraction;
- simple classification;
- repetitive tool decisions;
- straightforward transformations.

### Strong reasoning tier

Use for:

- coding;
- debugging;
- multi-file reasoning;
- semantic blast radius;
- evidence fusion;
- repair planning.

### Highest reasoning tier

Use only for:

- difficult root-cause analysis;
- ambiguous architectural changes;
- high-value final synthesis;
- difficult certification reasoning.

## Cost constraints

- cache deterministic results;
- do not ask an LLM to calculate deterministic metrics;
- batch independent lightweight operations;
- use serverless jobs for burst workloads where appropriate;
- clean unused endpoints/sandboxes.

---

# 9. DATA / TRUST FLOW TO PRESERVE IN CODE

The implementation should visibly and structurally maintain this graph:

```text
HISTORICAL MEMORY
      ↓
EVIDENCE-BACKED BEHAVIORAL KNOWLEDGE
      ↓
BEHAVIORAL CONSTITUTION
      ↓
HUMAN INTENT
      ↓
INTENT LEDGER — LOCKED
      ↓
SEMANTIC IMPACT MAP — FROZEN
      ↓
VERIFICATION PLAN — LOCKED
      ↓
CODING AGENT
      ↓
CANDIDATE PATCH #1
      ↓
---------------- TRUST BOUNDARY ----------------
      ↓
INDEPENDENT VERIFICATION
      ↓
EVIDENCE
      ↓
CLAIM-LEVEL FUSION
      ↓
BEHAVIORAL DELTA
      ↓
INTENT ALIGNMENT
      ↓
AUTHORIZED / UNAUTHORIZED
      ↓
REPAIR REQUIRED
      ↓
CANDIDATE PATCH #2
      ↓
INDEPENDENT RE-VERIFICATION
      ↓
FINAL INTENT ALIGNMENT
      ↓
CHANGE CERTIFICATE
      ↓
MERGE
      ↓
EXPANDED BEHAVIORAL MEMORY
```

This trust/data relationship is explicitly established in the source architecture. fileciteturn2file3L1186-L1341

---

# 10. CONTEXTUAL VIEW RULE

Every new engineering requirement must be classified as either:

### Primary product moment
A distinct user-facing semantic step that changes the workflow or trust state.

### Contextual view
A detail inside an existing workspace.

Contextual views include:

- Evidence Inspector;
- Claim Inspector;
- Historical vs Intent Inspector;
- Conflict Review;
- Ghost Inspector;
- Execution Trace Drawer;
- Semantic Relationship Inspector;
- Verification Module Detail;
- Mutation Detail;
- Behavioral Change Inspector;
- Unauthorized Decision Inspector;
- Repair Evidence Inspector;
- Certificate Evidence Drawer.

Do not create a new primary page merely because a new object needs inspection. fileciteturn2file4L1500-L1516

---

# 11. PHASE GATE MODEL

Every phase must end with an objective gate.

```text
IMPLEMENTED?
   ↓
CONTRACTS PASS?
   ↓
UNIT TESTS PASS?
   ↓
INTEGRATION PASS?
   ↓
EVIDENCE GENERATED?
   ↓
SECURITY CONDITIONS PASS?
   ↓
CHROME/RUNTIME VALIDATION PASS?
   ↓
EXIT GATE PASS?
```

A failed gate returns the work to the current phase. It does not silently unlock the next phase.

---

# 12. RELEASE / SUBMISSION READINESS CHECKLIST

## Runtime

- [ ] Real repository workflow works.
- [ ] Nebius Sandbox executes the demonstrated engineering work.
- [ ] Nemotron participates in meaningful runtime reasoning.
- [ ] Agent writes code.
- [ ] Agent runs code.
- [ ] Agent tests code.
- [ ] Agent observes actual results.
- [ ] Agent adapts after failure.
- [ ] Final result is objectively verified.

## Architecture

- [ ] Orchestrator controls workflow.
- [ ] Parallel independent subagents are actually parallel.
- [ ] Tool calls pass through policy.
- [ ] Independent verification has a trust boundary.
- [ ] Evidence is persistent and attributable.
- [ ] Candidate and certificate are distinct states.
- [ ] Failure is preserved.
- [ ] Certificate is evidence-bound.

## Product

- [ ] One persistent application shell.
- [ ] Eight journey tabs.
- [ ] 21 primary product moments.
- [ ] Contextual inspectors instead of unnecessary pages.
- [ ] Trust state is visible.
- [ ] Evidence is visible.
- [ ] Failure is visible.
- [ ] Repair is visibly evidence-driven.
- [ ] Final state returns to behavioral memory.

## Security

- [ ] Sandbox isolation validated.
- [ ] No unrestricted host credentials.
- [ ] Secrets are server-side only.
- [ ] Tool actions are policy-controlled.
- [ ] Security blocks are observable.
- [ ] Browser testing uses an isolated profile.

## Quality

- [ ] Build passes.
- [ ] Type checking passes.
- [ ] Lint passes.
- [ ] Unit tests pass.
- [ ] Integration tests pass.
- [ ] E2E tests pass.
- [ ] Agent evaluations pass agreed thresholds.
- [ ] Chrome console clean.
- [ ] Chrome network clean.
- [ ] Chrome performance reviewed.
- [ ] Security regression passes.

## Submission

- [ ] Correct Track selected.
- [ ] Public source repository.
- [ ] OSI-approved license.
- [ ] README.
- [ ] Setup instructions.
- [ ] Run instructions.
- [ ] NVIDIA usage explained.
- [ ] Nebius usage explained.
- [ ] Working demo URL.
- [ ] Public demo video ≤ 3 minutes.
- [ ] Demo explicitly shows the real Track 1 loop.

The source materials identify the public repository, license, setup/run instructions, working demo, demo video, and NVIDIA/Nebius explanations as submission requirements. fileciteturn3file4L1190-L1239

---

# 13. FINAL ENGINEERING PRINCIPLE

The implementation must continuously answer five questions:

### MEMORY
What did the software historically do?

### CONSTITUTION
What behavior is governed?

### INTENT
What did the human authorize?

### EVIDENCE
What did independent execution establish?

### CERTIFICATE
What has now been proven?

Everything else exists to connect those five objects reliably.

The product should therefore remain a closed software-evolution loop:

```text
DISCOVER
→ GOVERN
→ DEFINE
→ ANALYZE
→ LOCK VERIFICATION
→ DEVELOP
→ INDEPENDENTLY VERIFY
→ FUSE EVIDENCE
→ DETERMINE DELTA
→ ALIGN WITH INTENT
→ REPAIR
→ RE-VERIFY
→ CERTIFY
→ PRESERVE MEMORY
→ EVOLVE AGAIN
```

The implementation is complete only when this loop is real, executable, observable, secure, repeatable, and independently testable.

---

# 14. IMPLEMENTATION ORDER — FINAL LOCKED SEQUENCE

```text
PHASE 0
Master Contracts / Repository / Governance
        ↓
PHASE 1
Nebius + NVIDIA Infrastructure
        ↓
PHASE 2
Behavioral Data + Persistence
        ↓
PHASE 3
Orchestrator + Parallel Multi-Agent Runtime
        ↓
PHASE 4
Tools + Policy Control Plane
        ↓
PHASE 5
Application Shell + Design System
        ↓
PHASE 6
Discover + Govern
        ↓
PHASE 7
Define + Analyze
        ↓
PHASE 8
Develop + Real Sandbox Coding Loop
        ↓
PHASE 9
Independent Verification
        ↓
PHASE 10
Behavioral Delta + Intent Alignment + Repair
        ↓
PHASE 11
Re-Verification + Certification + Memory
        ↓
PHASE 12
Full System Integration + Demo Reliability
        ↓
PHASE 13
SYSTEM SECURITY OPTIMIZATION
        ↓
PHASE 14
FINAL END-TO-END TEST + CHROME DEVTOOLS + TOTAL OPTIMIZATION
```

**Phase 13 and Phase 14 are intentionally the final two phases.** No later phase is allowed to introduce planned feature scope.

---

# 15. MASTER SUCCESS DEFINITION

The project is ready when the system can take a real software-engineering task and autonomously operate the following loop:

```text
UNDERSTAND THE REPOSITORY
        ↓
PLAN THE CHANGE
        ↓
PARALLELIZE INDEPENDENT INVESTIGATION
        ↓
DELEGATE SPECIALIST WORK
        ↓
CREATE / MODIFY CODE IN NEBIUS SANDBOX
        ↓
RUN REAL CODE
        ↓
RUN REAL TESTS
        ↓
OBSERVE REAL FAILURES
        ↓
REASON FROM EXECUTION EVIDENCE
        ↓
REPAIR
        ↓
INDEPENDENTLY VERIFY
        ↓
COMPARE BEHAVIOR TO LOCKED HUMAN INTENT
        ↓
CERTIFY ONLY WHEN OBJECTIVE EVIDENCE SUPPORTS IT
        ↓
PRESERVE FAILURE + VERIFICATION AS MEMORY
        ↓
READY FOR THE NEXT EVOLUTION
```

That is the implementation target.

