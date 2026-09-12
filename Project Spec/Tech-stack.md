+=========================================================================================================================================+
|                                      RECOMMENDED PRODUCTION ARCHITECTURE — HACKATHON BUILD                                              |
|                                      Nebius x NVIDIA Global AI Hackathon — Track 1                                                     |
+=========================================================================================================================================+

| PRIMARY DESIGN DECISION                                                                                                                |
|-----------------------------------------------------------------------------------------------------------------------------------------|
| This project should NOT be built as a generic "AI coding assistant".                                                                  |
|                                                                                                                                        |
| It should be implemented as:                                                                                                          |
|                                                                                                                                        |
|        A BEHAVIORAL SOFTWARE ENGINEERING SYSTEM                                                                                       |
|        where NVIDIA Nemotron provides reasoning, Nebius provides inference + execution infrastructure,                                |
|        and the application's core value is evidence-backed behavioral memory, governed intent,                                       |
|        semantic analysis, independent verification, repair, and certification.                                                        |
|                                                                                                                                        |
| Track 1 fit:                                                                                                                           |
|        User -> Coding/Engineering Agent -> Nebius Token Factory Sandbox -> writes code / runs code / tests code                       |
|        -> independent verification -> evidence -> repair -> re-verification -> certification                                         |
+=========================================================================================================================================+


+-----------------------------------------------------------------------------------------------------------------------------------------+
|                                      LAYER 1 — USER EXPERIENCE                                                                          |
+-----------------------------------------------------------------------------------------------------------------------------------------+
|                                                                                                                                         |
|                                      WEB APPLICATION                                                                                    |
|                                                                                                                                         |
|        React + Next.js                                                                                                                  |
|        TypeScript                                                                                                                        |
|        Tailwind CSS                                                                                                                      |
|        Monaco Editor                                                                                                                     |
|                                                                                                                                         |
|        Responsibilities:                                                                                                                 |
|        -> 21 primary product moments                                                                                                    |
|        -> persistent application shell                                                                                                  |
|        -> behavioral graphs / relationship visualization                                                                                |
|        -> evidence inspectors / drawers                                                                                                 |
|        -> intent and verification locks                                                                                                 |
|        -> candidate / failure / repair / certificate views                                                                              |
|        -> execution status streaming                                                                                                    |
|                                                                                                                                         |
|        IMPORTANT: UI is a thin client.                                                                                                  |
|        It does not become the intelligence layer.                                                                                        |
|                                                                                                                                         |
+-----------------------------------------------+-----------------------------------------------------------------------------------------+
                                                |
                                                | HTTPS / WebSocket / SSE
                                                v
+-----------------------------------------------------------------------------------------------------------------------------------------+
|                                      LAYER 2 — APPLICATION API                                                                           |
+-----------------------------------------------------------------------------------------------------------------------------------------+
|                                                                                                                                         |
|                                     Python + FastAPI                                                                                     |
|                                                                                                                                         |
|        API responsibilities:                                                                                                            |
|        -> project management                                                                                                             |
|        -> archaeology orchestration                                                                                                     |
|        -> behavioral object management                                                                                                  |
|        -> constitution management                                                                                                       |
|        -> intent compilation / locking                                                                                                  |
|        -> semantic impact orchestration                                                                                                 |
|        -> verification-plan generation                                                                                                  |
|        -> candidate-patch lifecycle                                                                                                     |
|        -> evidence ingestion                                                                                                             |
|        -> claim/evidence fusion                                                                                                          |
|        -> behavioral delta calculation                                                                                                   |
|        -> repair orchestration                                                                                                          |
|        -> certification artifact generation                                                                                              |
|        -> persistent state transitions                                                                                                  |
|                                                                                                                                         |
|        Deployment target:                                                                                                                |
|        -> Nebius AI Cloud Serverless Endpoint                                                                                           |
|                                                                                                                                         |
+-----------------------------------------------+-----------------------------------------------------------------------------------------+
                                                |
                                                |
                 +------------------------------+------------------------------+
                 |                                                             |
                 |                                                             |
                 v                                                             v
+---------------------------------------------+           +-------------------------------------------------------------+
|     LAYER 3 — NVIDIA / NEBIUS INTELLIGENCE  |           |      LAYER 4 — PROJECT MEMORY / KNOWLEDGE                 |
+---------------------------------------------+           +-------------------------------------------------------------+
|                                             |           |                                                             |
|      NEBIUS TOKEN FACTORY                   |           |  PRIMARY PERSISTENCE                                        |
|                                             |           |                                                             |
|      NVIDIA Nemotron 3 Nano                |           |  PostgreSQL / Supabase                                      |
|      NVIDIA Nemotron 3 Super               |           |                                                             |
|      NVIDIA Nemotron 3 Ultra               |           |  Stores:                                                     |
|                                             |           |  -> Projects                                                |
|      OpenAI-compatible API                  |           |  -> Archaeology runs                                         |
|                                             |           |  -> Behavioral findings                                      |
|      MODEL ROUTING                          |           |  -> Invariants                                               |
|                                             |           |  -> Incidents                                                |
|      Nano                                  |           |  -> Dependencies                                             |
|      -> extraction / classification         |           |  -> Risk zones                                               |
|      -> lightweight reasoning               |           |  -> Ghost metadata                                           |
|      -> routine tool decisions              |           |  -> Constitutional claims                                    |
|                                             |           |  -> Authority                                                |
|      Super                                 |           |  -> Confidence                                               |
|      -> architecture reasoning              |           |  -> Intent Ledger                                            |
|      -> semantic analysis                   |           |  -> Semantic Impact Map                                      |
|      -> evidence synthesis                  |           |  -> Verification Plan                                        |
|      -> repair reasoning                    |           |  -> Candidate patches                                        |
|                                             |           |  -> Verification results                                     |
|      Ultra                                 |           |  -> Evidence                                                 |
|      -> only high-value / hard reasoning    |           |  -> Behavioral Delta                                         |
|      -> final synthesis / certification     |           |  -> Failure F-183                                            |
|                                             |           |  -> Certificates                                             |
|      WHY                                     |           |                                                             |
|      NVIDIA model + Nebius inference        |           |  Supabase advantage:                                         |
|      gives direct hackathon relevance        |           |  -> managed Postgres                                         |
|      without self-hosting GPU inference.    |           |  -> authentication if needed                                 |
|                                             |           |  -> storage                                                  |
+----------------------+----------------------+           |  -> realtime updates                                         |
                       |                                  |  -> almost no database infrastructure work                  |
                       |                                  +-------------------------------------------------------------+
                       |
                       | model calls
                       v
+-----------------------------------------------------------------------------------------------------------------------------------------+
|                              LAYER 5 — AGENT ORCHESTRATION                                                                               |
+-----------------------------------------------------------------------------------------------------------------------------------------+
|                                                                                                                                         |
|                           NVIDIA NeMo Agent Toolkit                                                                                     |
|                                                                                                                                         |
|        Use as the agent orchestration / evaluation layer instead of building a custom agent framework from zero.                       |
|                                                                                                                                         |
|        Responsibilities:                                                                                                               |
|        -> agent workflow orchestration                                                                                                  |
|        -> tool routing                                                                                                                   |
|        -> agent evaluation                                                                                                               |
|        -> instrumentation                                                                                                               |
|        -> tracing / profiling                                                                                                            |
|        -> interoperability with other agent frameworks                                                                                  |
|                                                                                                                                         |
|        CORE SPECIALIZED AGENTS                                                                                                          |
|                                                                                                                                         |
|        +----------------------+                                                                                                        |
|        | Archaeology Agent    |                                                                                                        |
|        +----------+-----------+                                                                                                        |
|                   |                                                                                                                     |
|                   v                                                                                                                     |
|        +----------------------+                                                                                                        |
|        | Knowledge Agent      |                                                                                                        |
|        +----------+-----------+                                                                                                        |
|                   |                                                                                                                     |
|                   v                                                                                                                     |
|        +----------------------+                                                                                                        |
|        | Intent Agent         |                                                                                                        |
|        +----------+-----------+                                                                                                        |
|                   |                                                                                                                     |
|                   v                                                                                                                     |
|        +----------------------+                                                                                                        |
|        | Impact Agent         |                                                                                                        |
|        +----------+-----------+                                                                                                        |
|                   |                                                                                                                     |
|                   v                                                                                                                     |
|        +----------------------+                                                                                                        |
|        | Coding Agent         |                                                                                                        |
|        +----------+-----------+                                                                                                        |
|                   |                                                                                                                     |
|                   v                                                                                                                     |
|        +----------------------+                                                                                                        |
|        | Verification Agent   |                                                                                                        |
|        +----------+-----------+                                                                                                        |
|                   |                                                                                                                     |
|                   v                                                                                                                     |
|        +----------------------+                                                                                                        |
|        | Evidence Agent       |                                                                                                        |
|        +----------+-----------+                                                                                                        |
|                   |                                                                                                                     |
|                   v                                                                                                                     |
|        +----------------------+                                                                                                        |
|        | Repair Agent         |                                                                                                        |
|        +----------+-----------+                                                                                                        |
|                   |                                                                                                                     |
|                   v                                                                                                                     |
|        +----------------------+                                                                                                        |
|        | Certification Agent  |                                                                                                        |
|        +----------------------+                                                                                                        |
|                                                                                                                                         |
|        IMPORTANT: these are logical agent roles, not necessarily 9 permanently running services.                                      |
|        They should be implemented as orchestrated capabilities to minimize infrastructure complexity.                                  |
|                                                                                                                                         |
+-----------------------------------------------+-----------------------------------------------------------------------------------------+
                                                |
                                                | Coding / execution tasks
                                                v
+=========================================================================================================================================+
|                            LAYER 6 — NEBIUS TOKEN FACTORY SANDBOX                                                                       |
|                                  CORE TRACK-1 EXECUTION LAYER                                                                           |
+=========================================================================================================================================+
|                                                                                                                                         |
|                                  DISPOSABLE CODE ENVIRONMENT                                                                             |
|                                                                                                                                         |
|       +--------------------------+                                                                                                     |
|       | Candidate Patch #1       |                                                                                                     |
|       +------------+-------------+                                                                                                     |
|                    |                                                                                                                    |
|                    v                                                                                                                    |
|       +--------------------------+                                                                                                     |
|       | NEBIUS SANDBOX           |                                                                                                     |
|       |                          |                                                                                                     |
|       | Repository               |                                                                                                     |
|       | Dependencies             |                                                                                                     |
|       | Runtime                  |                                                                                                     |
|       | Candidate code            |                                                                                                     |
|       | Environment              |                                                                                                     |
|       | Tests                    |                                                                                                     |
|       +------------+-------------+                                                                                                     |
|                    |                                                                                                                    |
|           +--------+--------+----------------------+                                                                                   |
|           |                 |                      |                                                                                   |
|           v                 v                      v                                                                                   |
|        WRITE CODE        RUN CODE               RUN TESTS                                                                               |
|           |                 |                      |                                                                                   |
|           +--------+--------+----------------------+                                                                                   |
|                    |                                                                                                                    |
|                    v                                                                                                                    |
|              EXECUTION OUTPUT                                                                                                           |
|                    |                                                                                                                    |
|                    v                                                                                                                    |
|              STRUCTURED EVIDENCE                                                                                                       |
|                                                                                                                                         |
|       THIS IS THE CRITICAL TRACK-1 IMPLEMENTATION.                                                                                     |
|       The coding agent does not merely generate text; it operates through an actual code-execution sandbox.                            |
|                                                                                                                                         |
|       Do NOT build a custom Docker/code-execution platform from scratch.                                                               |
|       Use the Nebius Token Factory Sandbox as the execution primitive.                                                                  |
|                                                                                                                                         |
+-----------------------------------------------+-----------------------------------------------------------------------------------------+
                                                |
                                                | execution results
                                                v
+-----------------------------------------------------------------------------------------------------------------------------------------+
|                              LAYER 7 — INDEPENDENT VERIFICATION                                                                         |
+-----------------------------------------------------------------------------------------------------------------------------------------+
|                                                                                                                                         |
|                                 VERIFICATION CONTROL PLANE                                                                              |
|                                                                                                                                         |
|    IMPORTANT TRUST BOUNDARY                                                                                                             |
|                                                                                                                                         |
|    CODING AGENT ENVIRONMENT                         !=                         VERIFIER ENVIRONMENT                                      |
|                                                                                                                                         |
|    Coding Agent creates candidate                                           Independent system investigates                            |
|                                                                                                                                         |
|    Candidate Patch #1                                                        Locked Constitution                                        |
|    Development checks                                                        Locked Intent                                             |
|                                                                                Locked Verification Plan                                   |
|                                                                                                                                         |
|       +--------------------+                                                                                                            |
|       | Static Analysis    |                                                                                                            |
|       +--------------------+                                                                                                            |
|                                                                                                                                         |
|       +--------------------+                                                                                                            |
|       | Differential       |                                                                                                            |
|       | Execution          |                                                                                                            |
|       +--------------------+                                                                                                            |
|                                                                                                                                         |
|       +--------------------+                                                                                                            |
|       | Historical Ghost   |                                                                                                            |
|       | Replay             |                                                                                                            |
|       +--------------------+                                                                                                            |
|                                                                                                                                         |
|       +--------------------+                                                                                                            |
|       | Metamorphic        |                                                                                                            |
|       | Checks             |                                                                                                            |
|       +--------------------+                                                                                                            |
|                                                                                                                                         |
|       +--------------------+                                                                                                            |
|       | Adversarial        |                                                                                                            |
|       | Scenarios          |                                                                                                            |
|       +--------------------+                                                                                                            |
|                                                                                                                                         |
|       +--------------------+                                                                                                            |
|       | Mutation Testing   |                                                                                                            |
|       +--------------------+                                                                                                            |
|                                                                                                                                         |
|       All modules emit evidence rather than a single "test score".                                                                    |
|                                                                                                                                         |
+-----------------------------------------------+-----------------------------------------------------------------------------------------+
                                                |
                                                v
+-----------------------------------------------------------------------------------------------------------------------------------------+
|                                   LAYER 8 — EVIDENCE ENGINE                                                                              |
+-----------------------------------------------------------------------------------------------------------------------------------------+
|                                                                                                                                         |
|    Evidence Collector                                                                                                                   |
|         |                                                                                                                               |
|         +---- Source Code                                                                                                                |
|         +---- Git History                                                                                                                |
|         +---- Runtime Observations                                                                                                      |
|         +---- Tests                                                                                                                      |
|         +---- Incidents                                                                                                                  |
|         +---- Dependencies                                                                                                               |
|         +---- Ghosts                                                                                                                      |
|         +---- Adversarial Scenarios                                                                                                     |
|         +---- Execution Traces                                                                                                          |
|                                                                                                                                         |
|                                  |                                                                                                      |
|                                  v                                                                                                      |
|                          Evidence Normalization                                                                                          |
|                                  |                                                                                                      |
|                                  v                                                                                                      |
|                          Claim Evidence Fusion                                                                                           |
|                                  |                                                                                                      |
|                                  +--> Authority                                                                                          |
|                                  +--> Relevance                                                                                          |
|                                  +--> Provenance                                                                                        |
|                                  +--> Severity                                                                                           |
|                                  +--> Confidence                                                                                        |
|                                  |                                                                                                      |
|                                  v                                                                                                      |
|                         Claim-Level Assessment                                                                                            |
|                                                                                                                                         |
|                         Example: AUTH-017                                                                                                |
|                                  |                                                                                                      |
|                +-----------------+-----------------+                                                                                     |
|                |                 |                 |                                                                                     |
|                v                 v                 v                                                                                     |
|          Ghost #221         Adversarial #14   Static Analysis                                                                             |
|             FAIL                 FAIL             WARNING                                                                                |
|                |                 |                 |                                                                                     |
|                +-----------------+-----------------+                                                                                     |
|                                  |                                                                                                      |
|                                  v                                                                                                      |
|                              VIOLATED                                                                                                    |
|                                                                                                                                         |
+-----------------------------------------------+-----------------------------------------------------------------------------------------+
                                                |
                                                v
+-----------------------------------------------------------------------------------------------------------------------------------------+
|                                  LAYER 9 — BEHAVIOR / INTENT ENGINE                                                                      |
+-----------------------------------------------------------------------------------------------------------------------------------------+
|                                                                                                                                         |
|                           LOCKED HUMAN INTENT                                                                                             |
|                                  |                                                                                                      |
|                                  v                                                                                                      |
|                         Intent Ledger #184                                                                                                |
|                                  |                                                                                                      |
|                   +--------------+--------------+                                                                                       |
|                   |              |              |                                                                                       |
|                   v              v              v                                                                                       |
|                ADD            REPLACE         PRESERVE                                                                                  |
|                passkeys       provider        password                                                                                 |
|                                                sessions                                                                                 |
|                                                authorization                                                                            |
|                                                tenant isolation                                                                         |
|                                  |                                                                                                      |
|                                  v                                                                                                      |
|                           BEHAVIORAL DELTA                                                                                                |
|                                  |                                                                                                      |
|                     what actually changed                                                                                               |
|                                  |                                                                                                      |
|                                  v                                                                                                      |
|                           INTENT ALIGNMENT                                                                                                |
|                                  |                                                                                                      |
|                 +----------------+----------------+                                                                                      |
|                 |                                 |                                                                                      |
|                 v                                 v                                                                                      |
|             AUTHORIZED                    UNEXPLAINED / UNAUTHORIZED                                                                     |
|                                                   |                                                                                     |
|                                                   v                                                                                     |
|                                            REPAIR REQUIRED                                                                               |
|                                                                                                                                         |
+-----------------------------------------------+-----------------------------------------------------------------------------------------+
                                                |
                                                v
+-----------------------------------------------------------------------------------------------------------------------------------------+
|                                  LAYER 10 — REPAIR LOOP                                                                                  |
+-----------------------------------------------------------------------------------------------------------------------------------------+
|                                                                                                                                         |
|                                 Failure F-183                                                                                            |
|                                      |                                                                                                  |
|                                      v                                                                                                  |
|                                 Repair Package                                                                                           |
|                                      |                                                                                                  |
|                                      +--> Expected = 403                                                                                 |
|                                      +--> Observed = 200                                                                                  |
|                                      +--> Claim = AUTH-017                                                                                |
|                                      +--> Evidence = Ghost #221 + Adversarial #14                                                        |
|                                      +--> Path = Session refresh -> authorization bypass                                                |
|                                      +--> Outcome = Restore authorization semantics                                                     |
|                                      |                                                                                                  |
|                                      v                                                                                                  |
|                               CODING AGENT                                                                                                |
|                                      |                                                                                                  |
|                                      v                                                                                                  |
|                                Candidate Patch #2                                                                                         |
|                                      |                                                                                                  |
|                                      v                                                                                                  |
|                           NEBIUS SANDBOX AGAIN                                                                                            |
|                                      |                                                                                                  |
|                                      v                                                                                                  |
|                         INDEPENDENT RE-VERIFICATION                                                                                      |
|                                      |                                                                                                  |
|                                      v                                                                                                  |
|                                  FAIL -> PASS                                                                                             |
|                                                                                                                                         |
|    IMPORTANT: Candidate Patch #1 and Failure F-183 are never overwritten.                                                              |
|                                                                                                                                         |
+-----------------------------------------------+-----------------------------------------------------------------------------------------+
                                                |
                                                v
+-----------------------------------------------------------------------------------------------------------------------------------------+
|                               LAYER 11 — CERTIFICATION                                                                                   |
+-----------------------------------------------------------------------------------------------------------------------------------------+
|                                                                                                                                         |
|                           FINAL INTENT ALIGNMENT                                                                                         |
|                                      |                                                                                                  |
|                                      v                                                                                                  |
|                         Unexplained changes = 0                                                                                            |
|                         Critical unauthorized changes = 0                                                                                 |
|                                      |                                                                                                  |
|                                      v                                                                                                  |
|                            CERTIFICATION ELIGIBLE                                                                                        |
|                                      |                                                                                                  |
|                                      v                                                                                                  |
|                              CHANGE CERTIFICATE                                                                                           |
|                                      |                                                                                                  |
|          +---------------------------+---------------------------+                                                                         |
|          |                           |                           |                                                                         |
|          v                           v                           v                                                                         |
|       Change                     Behavior                  Verification                                                                    |
|       #184                       32 / 32 preserved         8 scenarios                                                                     |
|       Commit                     unintended deltas 0      7 metamorphic                                                                    |
|                                                            93% mutation coverage                                                            |
|          |                           |                           |                                                                         |
|          +---------------------------+---------------------------+                                                                         |
|                                      |                                                                                                  |
|                                      v                                                                                                  |
|                                  Integrity                                                                                               |
|                            Environment hash                                                                                                |
|                            Dependency state LOCKED                                                                                        |
|                            Certificate hash                                                                                                |
|                                      |                                                                                                  |
|                                      v                                                                                                  |
|                                  CERTIFIED                                                                                                |
|                                      |                                                                                                  |
|                                      v                                                                                                  |
|                                    MERGE                                                                                                  |
+-----------------------------------------------+-----------------------------------------------------------------------------------------+
                                                |
                                                v
+-----------------------------------------------------------------------------------------------------------------------------------------+
|                                LAYER 12 — CONTINUOUS MEMORY                                                                               |
+-----------------------------------------------------------------------------------------------------------------------------------------+
|                                                                                                                                         |
|   CERTIFIED CHANGE                                                                                                                       |
|         |                                                                                                                               |
|         +--> New Behavioral Evidence                                                                                                    |
|         +--> Updated Behavioral Knowledge                                                                                               |
|         +--> Preserved Failure F-183                                                                                                    |
|         +--> Preserved Ghost #221                                                                                                       |
|         +--> Updated verification knowledge                                                                                             |
|         |                                                                                                                               |
|         v                                                                                                                               |
|   BEHAVIORAL MEMORY                                                                                                                      |
|         |                                                                                                                               |
|         v                                                                                                                               |
|   FUTURE CHANGE                                                                                                                          |
|         |                                                                                                                               |
|         +------------------------------> same architecture repeats                                                                       |
|                                                                                                                                         |
+=========================================================================================================================================+


+=========================================================================================================================================+
|                                             SUPPORTING TECHNOLOGY STACK                                                                  |
+=========================================================================================================================================+

| AREA                         | RECOMMENDED TECHNOLOGY                    | WHY IT BELONGS HERE                                              |
|------------------------------|-------------------------------------------|------------------------------------------------------------------|
| Frontend                     | Next.js + React + TypeScript              | Fast product implementation; strong app routing/UI              |
| Styling                      | Tailwind CSS                              | Fast, consistent implementation of dense expert UI              |
| Code editor                  | Monaco Editor                             | Avoid building an editor from scratch                           |
| Graph visualization          | React Flow                                | Avoid building graph interaction primitives                     |
| Backend                      | Python + FastAPI                          | Excellent fit for orchestration, code analysis and AI tooling   |
| Agent orchestration          | NVIDIA NeMo Agent Toolkit                 | NVIDIA-native agent orchestration/evaluation                     |
| Primary LLM                  | NVIDIA Nemotron 3 Nano                    | Efficient routine reasoning / extraction / classification       |
| Advanced LLM                 | NVIDIA Nemotron 3 Super                   | Complex reasoning / architecture / evidence synthesis           |
| Highest reasoning            | NVIDIA Nemotron 3 Ultra                   | Reserve for expensive/high-value reasoning only                 |
| Inference                    | Nebius Token Factory                      | Required Nebius runtime + NVIDIA Nemotron models                |
| Coding execution             | Nebius Token Factory Sandboxes            | Direct Track-1 coding/run/test primitive                        |
| Primary database             | Supabase PostgreSQL                       | Managed relational persistence; avoids DB operations            |
| File/evidence storage        | Supabase Storage                          | Avoid custom object-storage layer                               |
| Auth                         | Supabase Auth                             | Optional; avoid building authentication                          |
| Realtime UI                  | Supabase Realtime                         | Optional; simplifies live evidence/status updates               |
| Background jobs              | Nebius Serverless Jobs                    | Batch archaeology / indexing / evaluation                        |
| API deployment               | Nebius Serverless Endpoint                | Managed HTTP inference/application endpoint                     |
| Containerization             | Docker                                    | Reproducible Nebius deployment                                  |
| Evaluation / tracing         | NVIDIA NeMo Agent Toolkit                 | Agent evaluation + profiling                                    |
| Web research                 | Tavily                                    | Optional; useful for documentation / external technical context |
| Environment secrets          | Nebius Secret / environment mechanism     | Keep API keys out of application code                            |
| Source control               | GitHub                                    | Natural source + commit provenance                              |
| Local development             | Dev Container / Docker Compose             | Same environment shape across developers                        |


+=========================================================================================================================================+
|                                           OPTIONAL INTEGRATIONS — PRIORITY ORDER                                                        |
+=========================================================================================================================================+

| PRIORITY | INTEGRATION                         | USE IN THIS PROJECT                                      | COMPLEXITY REDUCTION                                    |
|----------|-------------------------------------|----------------------------------------------------------|---------------------------------------------------------|
| 1        | NVIDIA NeMo Agent Toolkit           | Agent orchestration + evaluation + instrumentation       | Avoid custom agent runtime                              |
| 2        | Nebius Token Factory                | Nemotron inference                                       | Avoid self-hosting LLM infrastructure                   |
| 3        | Nebius Token Factory Sandboxes      | Code write/run/test                                      | Avoid building execution infrastructure                 |
| 4        | React Flow                          | Knowledge Graph + Impact Graph                           | Avoid custom graph interaction                          |
| 5        | Monaco Editor                       | Candidate patch / source inspection                      | Avoid building editor                                   |
| 6        | Supabase                            | DB + Auth + Storage + Realtime                          | Avoid backend persistence infrastructure                |
| 7        | Nebius Serverless Jobs              | Archaeology / batch evaluation / asynchronous workloads | Avoid job-worker infrastructure                         |
| 8        | Nebius Serverless Endpoints         | Backend deployment                                       | Avoid VM / Kubernetes operations                        |
| 9        | Tavily                              | Optional external technical research                    | Adds useful live evidence / hackathon bonus potential   |
| 10       | NVIDIA NeMo Guardrails             | Optional policy/guardrail layer                         | Adds controlled AI interaction with less custom logic   |
| 11       | NVIDIA OpenShell / NemoClaw         | Optional additional agent security layer                | Use only if sandbox/security requirements justify it    |


+=========================================================================================================================================+
|                                             WHAT SHOULD NOT BE BUILT FROM SCRATCH                                                      |
+=========================================================================================================================================+
|                                                                                                                                         |
|  DO NOT BUILD                                                                                                                           |
|                                                                                                                                         |
|  X  Custom GPU inference server                                                                                                         |
|  X  Custom LLM serving layer                                                                                                            |
|  X  Custom code execution VM                                                                                                            |
|  X  Custom sandbox orchestration                                                                                                        |
|  X  Custom graph rendering engine                                                                                                      |
|  X  Custom code editor                                                                                                                  |
|  X  Custom authentication                                                                                                               |
|  X  Custom file/object storage system                                                                                                   |
|  X  Custom background-job infrastructure                                                                                                |
|  X  Custom agent runtime if NeMo Agent Toolkit can own orchestration                                                                   |
|                                                                                                                                         |
|  BUILD YOURSELF                                                                                                                         |
|                                                                                                                                         |
|  ✓ Behavioral data model                                                                                                                 |
|  ✓ Behavioral Constitution logic                                                                                                         |
|  ✓ Intent Ledger semantics                                                                                                               |
|  ✓ Semantic Impact reasoning specific to software behavior                                                                               |
|  ✓ Evidence fusion logic                                                                                                                 |
|  ✓ Behavioral Delta / Intent Alignment                                                                                                    |
|  ✓ Ghost representation / reconstruction logic                                                                                            |
|  ✓ Failure Archaeology                                                                                                                    |
|  ✓ Certification binding logic                                                                                                           |
|  ✓ Product UX / 21 primary product moments                                                                                                |
|  ✓ The actual novel intelligence of the project                                                                                          |
|                                                                                                                                         |
+=========================================================================================================================================+


+=========================================================================================================================================+
|                                                   MODEL / COMPUTE STRATEGY                                                              |
+=========================================================================================================================================+

| REQUEST TYPE                                      | MODEL                         | REASON                                           |
|---------------------------------------------------|-------------------------------|--------------------------------------------------|
| UI conversational explanation                    | Nemotron 3 Nano               | Cheap / fast                                     |
| Metadata extraction                               | Nemotron 3 Nano               | High-volume lightweight task                    |
| Source summarization                              | Nemotron 3 Nano               | Avoid expensive reasoning                       |
| Behavioral classification                         | Nemotron 3 Nano               | Structured classification                        |
| Intent compilation                               | Nemotron 3 Super              | Requires stronger semantic reasoning             |
| Semantic blast-radius analysis                    | Nemotron 3 Super              | Deeper dependency/behavior reasoning             |
| Evidence fusion                                  | Nemotron 3 Super              | Claim-level interpretation                       |
| Repair planning                                  | Nemotron 3 Super              | Multi-step reasoning                             |
| Difficult architecture reasoning                  | Nemotron 3 Ultra              | Reserve for exceptional cases                    |
| Final certification synthesis                    | Nemotron 3 Ultra / Super      | High-value final reasoning                       |
| Code generation                                  | Nemotron 3 Super              | Strong coding/reasoning balance                  |
| Actual code execution                            | Nebius Sandbox                | LLM should not simulate execution                |
| Actual verification                              | Sandbox + deterministic tools | Evidence must come from execution               |


+=========================================================================================================================================+
|                                                        COST CONTROL ARCHITECTURE                                                        |
+=========================================================================================================================================+

| STRATEGY                                                                                                                               |
|-----------------------------------------------------------------------------------------------------------------------------------------|
|                                                                                                                                         |
|  1. Use Nebius Token Factory rather than self-hosting GPU inference.                                                                     |
|  2. Use Nemotron Nano for the majority of calls.                                                                                        |
|  3. Escalate only complex reasoning to Nemotron Super.                                                                                  |
|  4. Reserve Ultra for rare high-value reasoning.                                                                                        |
|  5. Use Nebius Serverless Jobs for burst workloads instead of always-on workers.                                                       |
|  6. Stop/delete unused Serverless endpoints.                                                                                            |
|  7. Keep state in managed PostgreSQL instead of operating database infrastructure.                                                     |
|  8. Use disposable Nebius Sandboxes for execution rather than permanent compute.                                                       |
|  9. Cache deterministic archaeology and verification artifacts.                                                                         |
| 10. Never call an LLM for calculations that ordinary Python code can perform.                                                          |
| 11. Keep evidence structured so the same evidence can be reused without re-inference.                                                  |
|                                                                                                                                         |
+=========================================================================================================================================+


+=========================================================================================================================================+
|                                                        WHY THIS STACK IS STRONG                                                         |
+=========================================================================================================================================+

| HACKATHON REQUIREMENT                                                                 | IMPLEMENTATION                         |
|---------------------------------------------------------------------------------------|-----------------------------------------|
| Run on Nebius Token Factory or Nebius AI Cloud                                        | Nebius Token Factory + AI Cloud         |
| Use at least one NVIDIA open-source model                                            | NVIDIA Nemotron                         |
| Track 1: coding agents that write/run/test code in Token Factory Sandboxes           | Nebius Token Factory Sandbox            |
| Strong NVIDIA usage                                                                   | Nemotron + NeMo Agent Toolkit            |
| Strong Nebius usage                                                                   | Token Factory + Sandboxes + Serverless   |
| Real agentic engineering                                                              | NeMo Agent Toolkit + Coding Agent        |
| Evidence-first architecture                                                          | Structured evidence engine               |
| Independent verification                                                              | Separate verification plane              |
| Low infrastructure burden                                                             | Managed Nebius + Supabase                |
| High demo reliability                                                                  | Disposable sandbox + locked contracts    |
| Easy future expansion                                                                  | Modular model/tool interfaces             |


+=========================================================================================================================================+
|                                             HACKATHON CREDIT / COST REALITY                                                             |
+=========================================================================================================================================+
|                                                                                                                                         |
| Nebius Builder Program is currently free to join and provides more than $400 in combined credits/discounts across Nebius and partners. |
| The official program terms also specify $25 Token Factory credits + $25 Tavily credits for successful registration/verification,           |
| with those promotional credits expiring 90 days after issuance.                                                                        |
|                                                                                                                                         |
| The hackathon itself explicitly points builders toward the Nebius Builder Program for credits, Token Factory and Tavily access.         |
|                                                                                                                                         |
| Therefore the recommended implementation is:                                                                                            |
|                                                                                                                                         |
|        DEVELOPMENT -> free / promotional credits wherever available                                                                     |
|        INFERENCE   -> Token Factory credits                                                                                             |
|        EXECUTION   -> Nebius Sandbox / hackathon-access path                                                                           |
|        BATCH       -> Serverless Jobs only when needed                                                                                  |
|        STORAGE     -> Supabase free tier initially                                                                                      |
|        FRONTEND    -> free-tier deployment during development                                                                           |
|                                                                                                                                         |
+=========================================================================================================================================+


+=========================================================================================================================================+
|                                             FINAL OPTIMIZED STACK — USE THIS                                                            |
+=========================================================================================================================================+

| FRONTEND                                                                                                                               |
| Next.js + React + TypeScript + Tailwind CSS + Monaco Editor + React Flow                                                              |
|                                                                                                                                         |
| API / BACKEND                                                                                                                          |
| Python + FastAPI                                                                                                                        |
|                                                                                                                                         |
| AGENT LAYER                                                                                                                            |
| NVIDIA NeMo Agent Toolkit                                                                                                               |
|                                                                                                                                         |
| PRIMARY AI                                                                                                                             |
| NVIDIA Nemotron 3 Nano + Nemotron 3 Super                                                                                              |
|                                                                                                                                         |
| HIGH-END REASONING                                                                                                                     |
| Nemotron 3 Ultra only when required                                                                                                    |
|                                                                                                                                         |
| INFERENCE                                                                                                                              |
| Nebius Token Factory                                                                                                                    |
|                                                                                                                                         |
| CODE EXECUTION                                                                                                                         |
| Nebius Token Factory Sandboxes                                                                                                          |
|                                                                                                                                         |
| BATCH / ASYNC                                                                                                                          |
| Nebius Serverless Jobs                                                                                                                  |
|                                                                                                                                         |
| DEPLOYMENT                                                                                                                             |
| Nebius Serverless Endpoints                                                                                                             |
|                                                                                                                                         |
| DATABASE                                                                                                                               |
| Supabase PostgreSQL                                                                                                                     |
|                                                                                                                                         |
| STORAGE                                                                                                                                |
| Supabase Storage                                                                                                                        |
|                                                                                                                                         |
| AUTH / REALTIME — OPTIONAL                                                                                                              |
| Supabase Auth + Realtime                                                                                                                |
|                                                                                                                                         |
| WEB RESEARCH — OPTIONAL                                                                                                                 |
| Tavily                                                                                                                                |
|                                                                                                                                         |
| SOURCE / PROVENANCE                                                                                                                     |
| GitHub                                                                                                                                  |
|                                                                                                                                         |
| CONTAINER                                                                                                                              |
| Docker                                                                                                                                  |
|                                                                                                                                         |
| OPTIONAL SECURITY                                                                                                                      |
| NVIDIA NeMo Guardrails / OpenShell where justified                                                                                     |
+=========================================================================================================================================+


+=========================================================================================================================================+
|                                                       ONE-SENTENCE ARCHITECTURE                                                         |
|                                                                                                                                         |
|        Next.js UI                                                                                                                       |
|             -> FastAPI                                                                                                                  |
|             -> NVIDIA NeMo Agent Toolkit                                                                                                |
|             -> NVIDIA Nemotron on Nebius Token Factory                                                                                  |
|             -> Nebius Token Factory Sandbox for real code execution                                                                     |
|             -> independent verification modules                                                                                        |
|             -> evidence / claim fusion                                                                                                 |
|             -> behavioral delta + intent alignment                                                                                      |
|             -> evidence-driven repair in a new sandbox                                                                                  |
|             -> independent re-verification                                                                                               |
|             -> evidence-bound certificate                                                                                               |
|             -> PostgreSQL behavioral memory                                                                                              |
|             -> future software evolution                                                                                                |
+=========================================================================================================================================+
