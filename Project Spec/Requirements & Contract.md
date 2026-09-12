# Track 1 — Requirements & Predefined Contracts

## 0. Governing principle

The project must be treated as:

> **An autonomous software-engineering system that takes a real software task, operates on a real repository inside a Nebius Token Factory Sandbox, executes and tests changes, observes the results, and iterates until it reaches a verified outcome.**

The system is **not** considered complete merely because an LLM generated code.

The fundamental success loop is:

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

---

# 1. HACKATHON HARD REQUIREMENTS

These are **non-negotiable external requirements**.

## H1 — Nebius infrastructure requirement

The submitted project **MUST run on either**:

* Nebius Token Factory
* Nebius AI Cloud

For Track 1 specifically, the implementation should use **Token Factory Sandboxes** as the actual execution environment for the software-engineering loop.

### Contract

```text
H1-INFRA:
Every actual code-execution workflow demonstrated by the product
MUST execute within a Nebius-controlled sandbox environment.
```

A local mock execution path cannot be presented as the real system.

---

## H2 — NVIDIA open-source model requirement

The submission **MUST use at least one NVIDIA open-source model**.

For this project, Nemotron should be the primary reasoning model family.

### Contract

```text
H2-MODEL:
At least one meaningful runtime decision in the demonstrated
software-engineering workflow MUST be produced using an
NVIDIA open-source model.
```

Merely mentioning Nemotron in README/documentation is insufficient.

---

## H3 — Track 1 requirement

The system MUST belong to:

> **Coding and Agentic Engineering**

The official description expects coding agents/developer tools that **write, run, and test code in Token Factory Sandboxes**.

### Contract

```text
H3-TRACK:
The system MUST be capable of all three:
1. WRITE code
2. RUN code
3. TEST code
inside the sandbox workflow.
```

All three need to be demonstrable.

---

## H4 — Real repository requirement

The agent should operate on an actual software repository rather than generating an isolated code snippet.

### Contract

```text
H4-REPOSITORY:
The agent MUST have a repository state that it can inspect,
modify, execute, and validate.
```

---

## H5 — Public source repository

Submission MUST contain a public:

* GitHub
* GitLab
* Bitbucket

repository with:

* OSI-approved open-source license
* README
* setup instructions
* execution instructions
* explanation of NVIDIA model usage
* explanation of Nebius usage
* other relevant services

---

## H6 — Working demonstration

A working demo URL should be provided.

For this project, that means judges should be able to understand and, where practical, exercise the actual agent workflow.

---

## H7 — Demo video

Maximum:

**3 minutes**

It must demonstrate actual operation and explain how Nebius and NVIDIA technology are used.

For this project, the video should visibly prove the **agent loop**, not spend most of its time on marketing.

---

# 2. CORE SYSTEM REQUIREMENTS

These are requirements of the product itself.

---

# R1 — Task ingestion

The system MUST accept a concrete software-engineering task.

Examples:

```text
"Fix the failing authentication test."

"Add pagination to the users API."

"Find and resolve the memory leak."

"Implement the requested feature and make all relevant tests pass."
```

### Required task representation

Internally normalize the request into:

```text
Task
├── objective
├── repository
├── constraints
├── acceptance criteria
├── priority
└── execution budget
```

### Contract

```text
TASK-CONTRACT-01

Every execution MUST have:
- a task objective
- a target repository
- measurable acceptance criteria

The agent MUST NOT begin unrestricted code modification
without a task context.
```

---

# R2 — Repository inspection

Before making modifications, the agent MUST inspect enough of the repository to form a grounded plan.

Minimum inspection capability:

```text
Directory structure
Relevant files
Dependencies
Configuration
Tests
Entry points
Existing implementation
```

### Contract

```text
REPO-CONTRACT-01

The agent MUST inspect repository state before generating a
final implementation plan.

The plan MUST reference actual repository artifacts.
```

This prevents:

> “The model guessed the architecture.”

---

# R3 — Planning

The agent MUST create an explicit execution plan.

The plan should contain:

```text
1. Problem interpretation
2. Suspected affected components
3. Files likely to change
4. Proposed implementation strategy
5. Tests/validation to perform
6. Completion criteria
```

### Contract

```text
PLAN-CONTRACT-01

No implementation step may be considered intentional unless
it belongs to the current execution plan or was introduced
as a documented response to new execution evidence.
```

That second clause is important because autonomous agents must be able to adapt.

---

# R4 — Sandbox creation

The system MUST establish an isolated execution environment.

Conceptually:

```text
Repository
   ↓
Sandbox
   ↓
Execution State
```

The agent should never blindly mutate the user's canonical repository state.

---

# R5 — Safe state management

The agent MUST maintain identifiable state.

Recommended:

```text
BASE
 ↓
WORKING STATE
 ↓
CHECKPOINT
 ↓
EXPERIMENT
```

Where supported, exploit:

* checkpoints
* branches
* rollback
* isolated execution

This is one of the areas where the Nebius Sandbox platform can become a genuine architectural advantage.

---

# R6 — File modification

The agent MUST be capable of modifying actual repository files.

Required operations:

```text
READ
CREATE
UPDATE
DELETE
```

But destructive operations should require policy validation.

### Contract

```text
FILE-CONTRACT-01

Every mutation MUST identify:
- target path
- operation
- previous state or relevant context
- resulting state

The system MUST retain enough information to explain the change.
```

---

# R7 — Command execution

The system MUST be capable of executing repository commands within the sandbox.

Examples:

```text
pytest
npm test
npm run build
cargo test
go test
mvn test
ruff
eslint
tsc
```

depending on the repository.

The command result must be captured.

### Required execution record

```text
Command
Exit code
stdout
stderr
Duration
Environment
Working directory
```

### Contract

```text
EXEC-CONTRACT-01

The agent MUST treat the sandbox execution result as authoritative
for whether that execution succeeded.

The language model MUST NOT mark an execution as successful
when the process exit state indicates failure.
```

This is a critical anti-hallucination contract.

---

# R8 — Test execution

The agent MUST be able to run tests relevant to the task.

Tests can be:

* existing tests
* generated tests
* targeted tests
* integration tests
* build checks
* lint/type checks where appropriate

### Contract

```text
TEST-CONTRACT-01

"Implementation complete" MUST NOT imply "verified."

Verification requires objective execution evidence.
```

---

# R9 — Failure observation

A failed command must return to the reasoning system.

Architecture:

```text
EXECUTION
   ↓
RESULT
   ↓
FAILURE ANALYSIS
   ↓
NEW DECISION
```

### Contract

```text
OBSERVATION-CONTRACT-01

Every failed execution MUST produce an observable event
available to the agent's next decision cycle.
```

This is what converts a code generator into an agent.

---

# R10 — Iterative repair

The agent MUST support multiple iterations.

Minimum conceptual loop:

```text
Attempt 1
 ↓
Fail
 ↓
Diagnose
 ↓
Patch
 ↓
Attempt 2
 ↓
Fail/Pass
 ↓
...
```

### Contract

```text
ITERATION-CONTRACT-01

The system MUST NOT terminate the engineering workflow solely
because a candidate patch was generated.

Termination requires either:
A. verified success, or
B. an explicit unrecoverable state.
```

---

# R11 — Root-cause reasoning

The agent should distinguish:

```text
Observed failure
≠
Root cause
```

For example:

```text
pytest failed
      ↓
AssertionError
      ↓
wrong state initialization
      ↓
incorrect session expiry handling
```

### Contract

```text
REASONING-CONTRACT-01

A repair iteration MUST be associated with an explicit diagnosis
or hypothesis, even if the hypothesis changes later.
```

---

# R12 — Verification

The agent MUST have a final verification stage.

Example:

```text
Acceptance criteria
        ↓
Relevant tests
        ↓
Build/lint/type checks
        ↓
Final state inspection
        ↓
VERIFIED
```

### Contract

```text
VERIFY-CONTRACT-01

The agent MAY declare VERIFIED only when every required
acceptance criterion has objective supporting evidence.
```

This should become one of the system's strongest invariants.

---

# 3. AGENT STATE CONTRACT

The agent should have an explicit state machine.

```text
                ┌────────────┐
                │   INTAKE   │
                └─────┬──────┘
                      ↓
                ┌────────────┐
                │ INSPECTING │
                └─────┬──────┘
                      ↓
                ┌────────────┐
                │  PLANNING  │
                └─────┬──────┘
                      ↓
                ┌────────────┐
                │ EXECUTING  │
                └─────┬──────┘
                      ↓
                ┌────────────┐
                │ OBSERVING  │
                └─────┬──────┘
                      ↓
               ┌──────┴───────┐
               ↓              ↓
           FAILURE          SUCCESS
               ↓              ↓
          DIAGNOSING       VERIFYING
               ↓              ↓
             PATCH       ┌─────┴─────┐
               │         │           │
               └──→ EXECUTE       VERIFIED
```

---

# 4. PREDEFINED STATE CONTRACTS

These should be hard-coded concepts in the system.

## State S0 — CREATED

```text
Task exists.
No code execution has happened.
No claim of progress may be made beyond initialization.
```

---

## State S1 — INSPECTED

Required evidence:

```text
Repository discovered
Relevant files identified
Relevant tests identified
Environment understood
```

---

## State S2 — PLANNED

Required:

```text
Problem interpretation
Implementation strategy
Validation strategy
```

---

## State S3 — EXECUTING

The agent is performing a concrete action.

---

## State S4 — OBSERVED

The action completed and produced machine-readable results.

---

## State S5 — FAILED

At least one expected condition was not met.

---

## State S6 — ITERATING

The agent has used observed evidence to decide on another action.

---

## State S7 — VERIFIED

All required acceptance criteria have evidence.

---

## State S8 — BLOCKED

The agent cannot safely continue.

This is **not** equivalent to success.

---

# 5. THE MOST IMPORTANT GLOBAL INVARIANTS

These should be treated as immutable system laws.

## Invariant I1 — No evidence, no success

```text
NO EXECUTION EVIDENCE
        ↓
NO VERIFIED CLAIM
```

---

## Invariant I2 — Model cannot fabricate execution

```text
Model says: "Tests pass"
             ↓
System checks actual execution
             ↓
Only execution result is authoritative
```

---

## Invariant I3 — Every mutation is attributable

Every file change must be traceable to:

```text
Task
→ Decision
→ Tool call
→ Result
```

---

## Invariant I4 — Failure is information

A failed test is not merely an error condition.

It becomes:

```text
Evidence
→ Diagnosis
→ Next decision
```

---

## Invariant I5 — Agent must be able to stop safely

The agent must have:

```text
Continue
Retry
Rollback
Stop / Block
```

It must never be trapped in an uncontrolled infinite repair loop.

---

## Invariant I6 — Completion is objective

The agent cannot say:

> “Looks good.”

It must say, conceptually:

> “Acceptance criteria A/B/C have supporting execution evidence.”

---

# 6. TOOL CONTRACTS

Every tool exposed to the agent should follow a predefined contract.

## `repository.inspect`

Input:

```json
{
  "path": "...",
  "depth": 3
}
```

Output:

```json
{
  "files": [],
  "directories": [],
  "metadata": {}
}
```

---

## `file.read`

Contract:

```text
Input:
- path

Output:
- exact file content
- metadata
```

The tool MUST NOT silently fabricate missing files.

---

## `file.write`

Input:

```text
path
content
reason
```

Output:

```text
success
path
change_summary
```

---

## `command.run`

Input:

```text
command
working_directory
timeout
```

Output:

```text
exit_code
stdout
stderr
duration
```

This is a very important contract because the **exit code must be machine authoritative**.

---

## `test.run`

Input:

```text
test target
```

Output:

```text
passed
failed
skipped
duration
stdout
stderr
```

---

## `sandbox.create`

Input:

```text
repository
base_state
resource_constraints
```

Output:

```text
sandbox_id
state_id
```

---

## `sandbox.checkpoint`

Creates a recoverable state.

---

## `sandbox.rollback`

Restores a previous safe state.

---

# 7. AGENT DECISION CONTRACT

The model should not directly perform unrestricted actions.

Use this conceptual interface:

```text
MODEL
 ↓
DECISION
 ↓
POLICY VALIDATION
 ↓
TOOL
 ↓
SANDBOX
 ↓
RESULT
 ↓
MODEL
```

Not:

```text
MODEL
 ↓
DO WHATEVER YOU WANT
```

---

# 8. PREDEFINED ACTION CONTRACT

Every action produced by the agent should have:

```text
ACTION_ID
ACTION_TYPE
RATIONALE
TARGET
EXPECTED_RESULT
```

Example:

```json
{
  "action_id": "A-042",
  "action_type": "run_test",
  "target": "tests/test_auth.py",
  "rationale": "Validate session-expiry fix",
  "expected_result": "All auth tests pass"
}
```

Then execution produces the actual result.

This makes the entire system auditable.

---

# 9. FAILURE CONTRACT

Define failure categories in advance.

```text
F1 — syntax/build failure
F2 — unit-test failure
F3 — integration failure
F4 — environment/dependency failure
F5 — timeout
F6 — permission failure
F7 — tool failure
F8 — ambiguous result
F9 — acceptance criterion failure
F10 — safety/policy block
```

Each failure should generate:

```text
failure classification
evidence
probable cause
next action
```

---

# 10. LOOP CONTROL CONTRACT

An autonomous agent cannot be allowed to retry forever.

Define:

```text
MAX_ITERATIONS
MAX_RUNTIME
MAX_COMMAND_COUNT
MAX_REPAIR_ATTEMPTS
```

And preferably:

```text
no-progress detector
```

Example:

```text
Attempt 1 → failure
Attempt 2 → same failure
Attempt 3 → same failure
Attempt 4 → same failure
             ↓
         NO PROGRESS
             ↓
           BLOCK
```

### Contract

```text
LOOP-CONTRACT-01

If consecutive iterations produce materially equivalent failures
without measurable progress, the agent MUST transition to BLOCKED
rather than continue indefinitely.
```

---

# 11. GIT / REPOSITORY SAFETY CONTRACT

The canonical repository should be protected.

Preferred flow:

```text
BASE REPOSITORY
      ↓
SANDBOX COPY / BRANCH
      ↓
EXPERIMENT
      ↓
VERIFY
      ↓
FINAL PATCH
```

Do not immediately overwrite the original state.

---

# 12. MULTI-CANDIDATE CONTRACT

This is optional for MVP but potentially one of your strongest differentiators.

Allow:

```text
Base
 ├── Candidate A
 ├── Candidate B
 └── Candidate C
```

Then objectively evaluate them.

### Contract

```text
MULTI-CANDIDATE-01

Candidate selection MUST be evidence-based.

The chosen candidate MUST have a measurable reason for selection,
such as test success, benchmark result, regression count, or
acceptance-criteria coverage.
```

This is where Nebius Sandbox branching can become a **core product capability**, rather than just a hosting choice.

---

# 13. MODEL ROUTING CONTRACT

A model router can select different Nemotron variants according to task difficulty.

Example:

```text
Simple operation
      ↓
smaller / faster Nemotron

Normal reasoning
      ↓
mid-tier Nemotron

Complex debugging / architecture
      ↓
stronger Nemotron
```

### Contract

```text
MODEL-CONTRACT-01

Model selection MUST be explainable by task requirements.

The system MUST NOT select a model solely because it is larger.
```

This also gives you a strong story for the hackathon feedback form.

---

# 14. OPTIONAL TAVILY CONTRACT

Do not add Tavily just to chase the $3,000 prize.

Use it only where external technical knowledge is actually required.

Example:

```text
Unknown library behavior
        ↓
Tavily search
        ↓
Relevant documentation
        ↓
Agent reasoning
        ↓
Code change
        ↓
Sandbox verification
```

### Contract

```text
TAVILY-CONTRACT-01

A Tavily invocation MUST materially contribute to a runtime
engineering decision.

Static/import-only usage does not qualify.
```

The hackathon explicitly requires a functional runtime API call to qualify for the Best Use of Tavily award.

---

# 15. OBSERVABILITY REQUIREMENTS

Every run should produce an execution trace.

Conceptually:

```text
RUN #17

Task received
↓
Repository inspected
↓
Plan generated
↓
Sandbox created
↓
File modified
↓
pytest executed
↓
FAIL: 3 tests
↓
Failure analyzed
↓
Patch generated
↓
pytest executed
↓
PASS: 42 tests
↓
Acceptance verified
```

This trace is enormously useful for:

* debugging
* judging
* demo
* replay
* evaluation
* user trust

---

# 16. EVIDENCE CONTRACT

Every important claim should have evidence attached.

Example:

```text
CLAIM:
"Authentication bug fixed."

EVIDENCE:
tests/test_auth.py
42 passed
exit_code = 0
```

Another:

```text
CLAIM:
"Build succeeds."

EVIDENCE:
npm run build
exit_code = 0
```

### Global rule

```text
CLAIM → EVIDENCE
```

Never:

```text
CLAIM → MODEL ASSERTION
```

---

# 17. FINAL RESULT CONTRACT

The final result must contain at least:

```text
Task
Repository
Files changed
Tests executed
Tests passed
Tests failed
Final verification status
Remaining limitations
```

A good final response object conceptually looks like:

```text
RESULT
├── status: VERIFIED
├── task: ...
├── files_changed: [...]
├── tests:
│   ├── passed: 42
│   └── failed: 0
├── iterations: 3
├── sandbox: ...
└── evidence: [...]
```

---

# 18. SECURITY REQUIREMENTS

Because the agent executes arbitrary repository code, security cannot be treated as an optional feature.

The execution environment should isolate:

```text
filesystem
processes
network
credentials
environment variables
resource usage
```

Never expose unrestricted host credentials to repository code.

The sandbox is therefore not only a judging requirement; it is part of the security model.

---

# 19. HUMAN CONTROL CONTRACT

The agent should support explicit human intervention.

Minimum:

```text
START
PAUSE
APPROVE
ABORT
ROLLBACK
```

For high-risk operations, the system can request approval.

Example:

```text
Agent proposes:
"Delete production configuration file"

        ↓

POLICY
        ↓

HUMAN APPROVAL REQUIRED
```

This is especially useful if you later evolve the system beyond a hackathon demo.

---

# 20. UI REQUIREMENTS

The interface should make the agent's engineering process visible.

The user should be able to see:

```text
┌─────────────────────────────────────────────┐
│ TASK                                        │
├─────────────────────────────────────────────┤
│ Repository                                  │
│ Current objective                           │
│ Acceptance criteria                         │
├─────────────────────────────────────────────┤
│ AGENT                                      │
│ Inspecting → Planning → Executing           │
│                                             │
│ Current action: Running auth tests          │
├─────────────────────────────────────────────┤
│ SANDBOX                                    │
│ Branch: fix/session-expiry                  │
│ Status: Running                             │
├─────────────────────────────────────────────┤
│ CHANGES                                    │
│ auth/session.py                             │
│ middleware/auth.py                          │
├─────────────────────────────────────────────┤
│ TESTS                                      │
│ 39 passed                                   │
│ 3 failed                                    │
├─────────────────────────────────────────────┤
│ ITERATION 2                                │
│ Diagnosing session expiry failure            │
├─────────────────────────────────────────────┤
│ VERIFICATION                               │
│ ✓ Build                                     │
│ ✓ Unit tests                                │
│ ✓ Acceptance criteria                       │
└─────────────────────────────────────────────┘
```

The UI should communicate **state**, not just expose a chat box.

---

# 21. MVP REQUIREMENTS

Do not try to implement every advanced idea simultaneously.

The minimum credible Track 1 system should have:

### MUST

```text
1. User task input
2. Repository loading
3. Nebius Sandbox creation
4. Nemotron inference
5. Repository inspection
6. Planning
7. File modification
8. Command execution
9. Test execution
10. Failure observation
11. Iterative repair
12. Final verification
13. Execution trace
14. Public demo
15. Public source repository
```

That is the real minimum.

---

# 22. STRONG VERSION REQUIREMENTS

After MVP:

```text
1. Checkpoints
2. Rollback
3. Multiple candidate patches
4. Branch comparison
5. Automatic strategy selection
6. Model routing
7. Documentation search
8. Tavily integration
9. Benchmarking
10. Failure classification
11. No-progress detection
12. Human approval gates
13. Persistent run history
14. Evaluation metrics
```

---

# 23. WINNING-LEVEL REQUIREMENTS

The system should eventually demonstrate at least one genuinely differentiated capability.

My preferred one:

## Autonomous patch search

Instead of:

```text
Problem
 ↓
one patch
 ↓
test
```

build:

```text
Problem
 ↓
Reason about solution space
 ↓
Generate candidate strategies
 ↓
Create isolated sandbox branches
 ↓
Implement A/B/C
 ↓
Run tests/benchmarks
 ↓
Compare objectively
 ↓
Discard inferior candidates
 ↓
Select best solution
 ↓
Final verification
```

This gives your project a much stronger identity:

> **An agent that searches the space of executable software solutions rather than merely generating a single code answer.**

That is a compelling use of Nebius Sandbox capabilities.

---

# 24. SUBMISSION CONTRACT

Before submission, the project MUST satisfy this checklist.

```text
[ ] Correct Track selected
[ ] Uses NVIDIA open-source model
[ ] Uses Nebius Token Factory or AI Cloud
[ ] Track 1 behavior demonstrated
[ ] Agent writes code
[ ] Agent runs code
[ ] Agent tests code
[ ] Agent observes actual execution result
[ ] Agent iterates after failure
[ ] Final result objectively verified
[ ] Public GitHub/GitLab/Bitbucket repository
[ ] OSI-approved license
[ ] README
[ ] Setup instructions
[ ] Run instructions
[ ] NVIDIA usage documented
[ ] Nebius usage documented
[ ] Working demo URL
[ ] Public YouTube demo ≤ 3 minutes
[ ] Demo explicitly explains Nebius + NVIDIA usage
[ ] Required Devpost questions answered
[ ] Existing-project changes documented if applicable
```

---

# 25. FINAL IMMUTABLE CONTRACT SET

I would actually put these at the top of the engineering repository as the **master contracts**:

```text
CONTRACT C01
The system must operate on a real software repository.

CONTRACT C02
Code execution must occur inside the designated Nebius execution
environment.

CONTRACT C03
At least one NVIDIA open-source model must participate meaningfully
in runtime reasoning.

CONTRACT C04
The agent must be able to inspect, modify, execute, and test code.

CONTRACT C05
Execution results are authoritative over model assertions.

CONTRACT C06
A failed execution must be observable by the next agent cycle.

CONTRACT C07
The agent must be able to iterate based on execution evidence.

CONTRACT C08
The system may declare VERIFIED only when acceptance criteria have
objective evidence.

CONTRACT C09
Every consequential mutation must be attributable to a task,
decision, and execution event.

CONTRACT C10
The agent must have bounded execution and retry behavior.

CONTRACT C11
The system must be able to recover from failed experiments.

CONTRACT C12
The final result must expose evidence of what was changed and
how it was verified.
```

## The single most important architectural invariant

Everything should revolve around this:

```text
         MODEL DECISION
               ↓
           TOOL ACTION
               ↓
        NEBIUS SANDBOX
               ↓
       ACTUAL EXECUTION
               ↓
       ACTUAL OBSERVATION
               ↓
         MODEL REASONING
               ↓
         NEXT DECISION
               ↺
```

**Not this:**

```text
USER
 ↓
LLM
 ↓
CODE
 ↓
DONE
```