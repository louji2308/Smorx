+------------------------------------------------------------------------------------------------------------------------------------------+
|                                      BEHAVIORAL OPERATING SYSTEM FOR SOFTWARE EVOLUTION                                                |
|                                                                                                                                          |
|  ONE SYSTEM  |  EIGHT JOURNEY TABS  |  TWENTY-ONE PRIMARY PRODUCT MOMENTS  |  CONTEXTUAL VIEWS                          |
+------------------------------------------------------------------------------------------------------------------------------------------+

| PERSISTENT APPLICATION SHELL                                                                                                            |
|------------------------------------------------------------------------------------------------------------------------------------------|
| LEFT NAVIGATION                                                                                                                         |
| Discover -> Govern -> Define -> Analyze -> Develop -> Verify -> Decide -> Certify                                                     |
|                                                                                                                                          |
| TOP CONTEXT                                                                                                                             |
| Project: Payments API  |  Repository: github.com/acme/payments  |  Change: #184  |  Constitution: v1.0 ACTIVE                   |
|                                                                                                                                          |
| WORKFLOW STATE                                                                                                                          |
| Discover -> Govern -> Define -> Analyze -> Develop -> Verify -> Decide -> Certify                                                      |
|                                                                                                                                          |
| TRUST STATUS                                                                                                                            |
| Historical -> Observed -> Protected -> Intent Locked -> Verification Locked -> Candidate/Unverified                                  |
|              -> Independently Investigated -> Repair Required -> Re-verified -> Certified                                             |
|                                                                                                                                          |
| GLOBAL RULE                                                                                                                             |
| Context persists structurally; provenance, claims, evidence, risk, dependencies, execution traces and certificate detail stay contextual|
+------------------------------------------------------------------------------------------------------------------------------------------+


| 01 DISCOVER | WHAT DOES THE SOFTWARE ACTUALLY DO?                                                                                      |
|------------------------------------------------------------------------------------------------------------------------------------------|
| SCREEN 1  | ARCHAEOLOGY LAUNCH                                                                                                         |
|            | Payments API -> github.com/acme/payments -> Ready -> Run Software Archaeology                                          |
|            |                                                                                                                            |
|            | Run Archaeology -> Archaeology Run created -> RUNNING -> Evidence collection begins                                   |
|            |                                                                                                                            |
| SCREEN 2  | ARCHAEOLOGY EVIDENCE WORKSPACE                                                                                             |
|            |                                                                                                                            |
|            | Behaviors | Invariants | Incidents | Dependencies | Couplings | Risk Zones | Ghosts | Evidence                      |
|            |                                                                                                                            |
|            | Source code + Git history + runtime observations + incidents + tests                                                     |
|            |                 -> Behavioral Findings                                                                                   |
|            |                 -> Evidence-backed Behavioral Memory                                                                     |
|            |                                                                                                                            |
| SCREEN 3  | BEHAVIORAL KNOWLEDGE GRAPH                                                                                                  |
|            |                                                                                                                            |
|            | Behaviors -> Software -> Dependencies -> Incidents -> Invariants -> Historical Ghosts -> Evidence                      |
|            |                                                                                                                            |
|            | Authentication -> Session -> Tenant -> Audit -> Invariant -> Incident                                                   |
|            | Payment -> Retry -> Gateway -> Ghost                                                                                       |
|            |                                                                                                                            |
|            | Ghost #221 -> Incident #61 -> Session behavior -> AUTH-017 -> Authentication provider relationship                    |
|            |                                                                                                                            |
|            | DISCOVER OUTPUT                                                                                                            |
|            | Historical / behavioral memory grounded in evidence                                                                       |
+------------------------------------------------------------------------------------------------------------------------------------------+


| 02 GOVERN | WHAT BEHAVIOR SHOULD REMAIN PROTECTED?                                                                                         |
|------------------------------------------------------------------------------------------------------------------------------------------|
| SCREEN 4  | BEHAVIORAL CONSTITUTION WORKSPACE                                                                                              |
|            |                                                                                                                               |
|            | Archaeological behavior                                                                                                      |
|            |        |                                                                                                                      |
|            |        +-> Claim                                                                                                              |
|            |        |     +-> Authority                                                                                                      |
|            |        |     +-> Confidence                                                                                                    |
|            |        |     +-> Evidence                                                                                                       |
|            |        |     +-> Protected state                                                                                                 |
|            |        |     +-> Historical Memory / Intent Memory                                                                                |
|            |        |     +-> Verification requirements                                                                                      |
|            |        |     +-> Human review                                                                                                    |
|            |        |                                                                                                                      |
|            |        +-> OBSERVED                                                                                                        |
|            |        +-> PROTECTED                                                                                                       |
|            |        +-> HYPOTHESIS                                                                                                      |
|            |        +-> REVIEW                                                                                                          |
|            |        +-> CONFLICTING                                                                                                     |
|            |        +-> LOCKED                                                                                                          |
|            |                                                                                                                               |
|            | AUTH-017 Tenant isolation -> Authority CRITICAL -> Confidence 0.99 -> PROTECTED                                      |
|            | PAY-004 Payment timeout triggers retry -> Authority HIGH -> Confidence 0.93 -> PROTECTED                              |
|            | CACHE-041 -> Confidence 0.68 -> NOT ENFORCED                                                                                |
|            |                                                                                                                               |
| SCREEN 5  | CONSTITUTION ACTIVATION & ACTIVE STATE                                                                                       |
|            |                                                                                                                               |
|            | Behavioral Constitution v1.0                                                                                                  |
|            | 42 claims | 32 protected | 7 observed | 3 hypotheses | 0 unresolved conflicts                                             |
|            |                                                                                                                               |
|            | Activate Constitution -> ACTIVE -> immutable governing context                                                             |
|            |                                                                                                                               |
|            | GOVERN OUTPUT                                                                                                                 |
|            | Behavioral Constitution = authoritative governing knowledge                                                                  |
+------------------------------------------------------------------------------------------------------------------------------------------+


| 03 DEFINE | WHAT DOES THE HUMAN WANT CHANGED?                                                                                             |
|------------------------------------------------------------------------------------------------------------------------------------------|
| SCREEN 6  | CHANGE DEFINITION                                                                                                             |
|            |                                                                                                                               |
|            | Change #184                                                                                                                   |
|            | Replace the authentication provider and add passkey login, while preserving password login, authorization, and session        |
|            | compatibility.                                                                                                                |
|            |                                                                                                                               |
|            | Active Constitution                                                                                                           |
|            |        -> relevant claims                                                                                                     |
|            |        -> AUTH-017 Tenant isolation                                                                                             |
|            |        -> AUTH-022 Authorization semantics                                                                                     |
|            |        -> AUTH-023 Session compatibility                                                                                       |
|            |        -> AUTH-031 Authentication contract                                                                                     |
|            |        -> AUD-011 Authentication audit events                                                                                  |
|            |        -> CACHE-041 Authentication caching behavior                                                                            |
|            |                                                                                                                               |
| SCREEN 7  | INTENT LEDGER & CONSTITUTIONAL CONSTRAINTS                                                                                     |
|            |                                                                                                                               |
|            | ADD                                                                                                                            |
|            | -> Add passkey authentication                                                                                                |
|            |                                                                                                                               |
|            | REPLACE                                                                                                                        |
|            | -> Replace existing authentication provider                                                                                   |
|            |                                                                                                                               |
|            | PRESERVE                                                                                                                       |
|            | -> Password login                                                                                                             |
|            | -> Authorization semantics                                                                                                     |
|            | -> Session compatibility                                                                                                       |
|            | -> Tenant isolation                                                                                                            |
|            |                                                                                                                               |
|            | PERFORMANCE                                                                                                                    |
|            | -> Authentication latency <= +10%                                                                                            |
|            |                                                                                                                               |
|            | SECURITY                                                                                                                       |
|            | -> Tenant isolation must remain unchanged                                                                                      |
|            |                                                                                                                               |
|            | Confirm Intent -> Intent Ledger #184 -> LOCKED                                                                                |
|            |                                                                                                                               |
|            | DEFINE OUTPUT                                                                                                                  |
|            | Immutable human intent that downstream stages must use                                                                       |
+------------------------------------------------------------------------------------------------------------------------------------------+


| 04 ANALYZE | WHAT COULD THIS CHANGE AFFECT, AND HOW WILL IT BE CHECKED?                                                                       |
|------------------------------------------------------------------------------------------------------------------------------------------|
| SCREEN 8  | SEMANTIC IMPACT WORKSPACE                                                                                                     |
|            |                                                                                                                               |
|            | Authentication                                                                                                                |
|            |       -> Session                                                                                                              |
|            |       -> Token Flow                                                                                                           |
|            |       -> Authorization                                                                                                        |
|            |       -> Tenant Access                                                                                                        |
|            |                                                                                                                               |
|            | Semantic blast radius                                                                                                         |
|            | -> Code components: 14                                                                                                        |
|            | -> Functions affected: 31                                                                                                     |
|            | -> Dependencies: 3                                                                                                            |
|            | -> Data flows: 7                                                                                                              |
|            | -> Protected behaviors: 4                                                                                                     |
|            | -> Historical Ghosts: 8                                                                                                       |
|            | -> Risk: HIGH                                                                                                                 |
|            |                                                                                                                               |
|            | Select relationship -> affected behaviors + dependencies + risk + Ghosts + protected behavior context                     |
|            |                                                                                                                               |
|            | Semantic Impact Map -> LOCKED                                                                                                 |
|            |                                                                                                                               |
| SCREEN 9  | VERIFICATION CONTRACT & PRE-CODING LOCK                                                                                        |
|            |                                                                                                                               |
|            | PROTECTED                                                                                                                      |
|            | -> Tenant isolation — CRITICAL                                                                                                |
|            | -> Authorization semantics — CRITICAL                                                                                         |
|            | -> Session compatibility — HIGH                                                                                                |
|            | -> Password login — HIGH                                                                                                      |
|            |                                                                                                                               |
|            | REQUIRED VERIFICATION                                                                                                         |
|            | -> Historical Ghost replay — 8 scenarios                                                                                     |
|            | -> Differential execution — 14 cases                                                                                          |
|            | -> Authorization adversarial testing — 21 cases                                                                              |
|            | -> Session compatibility testing — 9 cases                                                                                    |
|            | -> Metamorphic checks — 7                                                                                                      |
|            | -> Mutation testing — 5                                                                                                       |
|            | -> Static dependency analysis                                                                                                 |
|            |                                                                                                                               |
|            | CONSTRAINT                                                                                                                    |
|            | -> Authentication latency <= +10%                                                                                              |
|            |                                                                                                                               |
|            | Lock Verification Plan -> VERIFICATION PLAN — LOCKED                                                                         |
|            |                                                                                                                               |
|            | ANALYZE OUTPUT                                                                                                                 |
|            | Frozen Semantic Impact Map + immutable Verification Plan                                                                     |
+------------------------------------------------------------------------------------------------------------------------------------------+


| 05 DEVELOP | WHAT DID THE CODING AGENT PROPOSE?                                                                                              |
|------------------------------------------------------------------------------------------------------------------------------------------|
| SCREEN 10 | DEVELOPMENT PLANE / CANDIDATE PATCH                                                                                             |
|            |                                                                                                                               |
|            | LOCKED INPUT CONTEXT                                                                                                         |
|            | Human Request + Intent Ledger + Behavioral Constitution + Semantic Impact Map + Verification Plan                            |
|            |                                  |                                                                                            |
|            |                                  v                                                                                            |
|            |                         CODING AGENT                                                                                          |
|            |                                  |                                                                                            |
|            |                                  v                                                                                            |
|            |                         Candidate Patch #1                                                                                     |
|            |                                                                                                                               |
|            | auth/provider.py                                                                                                               |
|            | -> LegacyAuthProvider                                                                                                         |
|            | -> NewAuthProvider                                                                                                            |
|            | -> PasskeyProvider                                                                                                            |
|            |                                                                                                                               |
|            | session.py                                                                                                                     |
|            | -> create_session()                                                                                                           |
|            | -> session compatibility retained                                                                                              |
|            |                                                                                                                               |
|            | DEVELOPMENT CHECKS                                                                                                            |
|            | -> Authentication adapter tests                                                                                                 |
|            | -> Passkey integration tests                                                                                                   |
|            | -> Password login tests                                                                                                        |
|            | -> Session unit tests                                                                                                          |
|            | -> Build/type checks                                                                                                            |
|            |                                                                                                                               |
|            | Persistent trust state = NOT CERTIFIED                                                                                          |
|            |                                                                                                                               |
|            | DEVELOPMENT OUTPUT                                                                                                              |
|            | Candidate Patch #1 -> ready for independent investigation                                                                       |
+------------------------------------------------------------------------------------------------------------------------------------------+


| 06 VERIFY | WHAT DOES INDEPENDENT INVESTIGATION ACTUALLY ESTABLISH?                                                                            |
|------------------------------------------------------------------------------------------------------------------------------------------|
| SCREEN 11 | INDEPENDENT VERIFICATION LAB                                                                                                    |
|            |                                                                                                                               |
|            | DEVELOPMENT PLANE                                                                                                              |
|            | Coding Agent -> Candidate Patch #1                                                                                             |
|            |            |                                                                                                                  |
|            |            X  trust boundary                                                                                                     |
|            |            |                                                                                                                  |
|            | INDEPENDENT PLANE                                                                                                              |
|            | Candidate Patch #1 + Verification Plan + Behavioral Constitution                                                               |
|            |            |                                                                                                                  |
|            |            v                                                                                                                  |
|            | Verification -> Evidence -> Assessment                                                                                        |
|            |                                                                                                                               |
|            | Persistent declaration: The Coding Agent does not control this environment                                                   |
|            |                                                                                                                               |
| SCREEN 12 | VERIFICATION CONTROL CENTER                                                                                                    |
|            |                                                                                                                               |
|            | Independent Verification Modules                                                                                               |
|            |                                                                                                                               |
|            | Static Analysis                                                                                                                |
|            | Differential Execution                                                                                                          |
|            | Historical Ghosts                                                                                                               |
|            | Metamorphic Checks                                                                                                              |
|            | Adversarial Scenarios                                                                                                           |
|            | Mutation Testing                                                                                                                |
|            |                                                                                                                               |
|            | RESULTS                                                                                                                         |
|            | Static Analysis -> complete                                                                                                     |
|            | Differential Execution -> 14 / 14                                                                                              |
|            | Historical Ghosts -> 7 / 8                                                                                                      |
|            | Metamorphic Checks -> 7 / 7                                                                                                     |
|            | Adversarial Scenarios -> 20 / 21                                                                                                |
|            | Mutation Testing -> 4 / 5                                                                                                       |
|            |                                                                                                                               |
|            | Critical finding -> Tenant isolation violated                                                                                   |
|            | Protected behaviors affected = 1                                                                                                |
|            | Historical regressions = 1                                                                                                      |
|            | Adversarial failures = 1                                                                                                       |
|            |                                                                                                                               |
| SCREEN 13 | CLAIM EVIDENCE & FUSION                                                                                                         |
|            |                                                                                                                               |
|            | Change #184                                                                                                                     |
|            |      |                                                                                                                        |
|            |      v                                                                                                                        |
|            | AUTH-017 Tenant Isolation                                                                                                       |
|            |      |                                                                                                                        |
|            |      +-> Ghost #221 -> FAIL                                                                                                     |
|            |      +-> Adversarial #14 -> FAIL                                                                                               |
|            |      +-> Static Analysis -> WARNING                                                                                            |
|            |      +-> Existing integration tests -> PASS                                                                                    |
|            |      +-> Differential cases -> PASS                                                                                             |
|            |                                                                                                                               |
|            | Evidence evaluated by: authority + relevance + provenance + severity + confidence                                            |
|            |                                                                                                                               |
|            | Current Assessment -> VIOLATED                                                                                                  |
|            |                                                                                                                               |
|            | VERIFY OUTPUT                                                                                                                    |
|            | Independent evidence establishes a consequential behavioral contradiction                                                      |
+------------------------------------------------------------------------------------------------------------------------------------------+


| 07 DECIDE | IS THE OBSERVED CHANGE AUTHORIZED?                                                                                              |
|------------------------------------------------------------------------------------------------------------------------------------------|
| SCREEN 14 | BEHAVIORAL DELTA & INTENT ALIGNMENT                                                                                              |
|            |                                                                                                                               |
|            |                         HUMAN INTENT       |       OBSERVED BEHAVIOR                                                          |
|            |                         -------------------|-----------------------                                                          |
|            |                         Add passkeys       | Passkey login                                                                    |
|            |                         Replace provider  | Provider replaced                                                                |
|            |                         Preserve password| Password login preserved                                                         |
|            |                         Preserve sessions | Session compatibility preserved                                                 |
|            |                         Preserve authorization | Tenant authorization changed                                                |
|            |                         Latency <= +10%  | +6.1%                                                                             |
|            |                                                                                                                               |
|            | Authorization row:                                                                                                             |
|            | Intent = Preserve authorization semantics                                                                                        |
|            | Observed = Tenant authorization bypass                                                                                         |
|            | Classification = UNEXPLAINED / UNAUTHORIZED                                                                                   |
|            |                                                                                                                               |
| SCREEN 15 | CERTIFICATION DECISION                                                                                                          |
|            |                                                                                                                               |
|            | Intended behavioral changes = 1                                                                                                 |
|            | Preserved behaviors = 3                                                                                                         |
|            | Changes within constraints = 1                                                                                                  |
|            | Unexplained changes = 1                                                                                                         |
|            | Critical violations = 1                                                                                                         |
|            | Evidence confidence = HIGH                                                                                                      |
|            |                                                                                                                               |
|            | CRITICAL PROTECTED BEHAVIOR CHANGED WITHOUT AUTHORIZATION                                                                       |
|            |                                  |                                                                                            |
|            |                                  v                                                                                            |
|            |                         REPAIR REQUIRED                                                                                         |
|            |                                  |                                                                                            |
|            |                                  v                                                                                            |
|            |                         Generate Repair Package                                                                                 |
|            |                                                                                                                               |
|            | DECIDE OUTPUT                                                                                                                    |
|            | Precise authorization decision grounded in the fused evidence                                                                   |
+------------------------------------------------------------------------------------------------------------------------------------------+


| 08 CERTIFY | CAN THE REPAIRED RESULT BECOME TRUSTED AND REMEMBERED?                                                                              |
|------------------------------------------------------------------------------------------------------------------------------------------|
| SCREEN 16 | REPAIR PACKAGE & CODING REPAIR                                                                                                  |
|            |                                                                                                                               |
|            | FAILURE PACKAGE                                                                                                                |
|            | Failure: Tenant isolation violated during session refresh                                                                       |
|            | Expected: Cross-tenant access -> 403                                                                                            |
|            | Observed: Cross-tenant access -> 200                                                                                            |
|            | Protected Claim: AUTH-017 — Tenant isolation                                                                                   |
|            | Evidence: Ghost #221 + Adversarial scenario #14                                                                                |
|            | Suspected path: Session refresh -> authorization bypass                                                                         |
|            | Required outcome: Restore authorization semantics                                                                               |
|            |                                                                                                                               |
|            | Failure evidence                                                                                                               |
|            |      -> Failure                                                                                                                 |
|            |      -> Suspected Path                                                                                                          |
|            |      -> Repair                                                                                                                  |
|            |      -> Candidate Patch #2                                                                                                      |
|            |                                                                                                                               |
|            | Candidate Patch #2 remains UNVERIFIED / NOT CERTIFIED                                                                          |
|            |                                                                                                                               |
| SCREEN 17 | INDEPENDENT RE-VERIFICATION                                                                                                     |
|            |                                                                                                                               |
|            | Candidate Patch #2                                                                                                             |
|            |        |                                                                                                                      |
|            |        +-> same locked verification conditions                                                                                |
|            |        |                                                                                                                      |
|            |        v                                                                                                                      |
|            | Before Repair                | After Repair                                                                                  |
|            | ----------------------------|----------------------------                                                                  |
|            | Tenant isolation: FAIL      | PASS                                                                                           |
|            | Ghost #221: FAIL            | PASS                                                                                           |
|            | Adversarial tenant switch: FAIL | PASS                                                                                        |
|            | Password login: PASS        | PASS                                                                                           |
|            | Session compatibility: PASS | PASS                                                                                           |
|            |                                                                                                                               |
|            | Critical behavior restored                                                                                                     |
|            | Re-verification complete                                                                                                       |
|            |                                                                                                                               |
| SCREEN 18 | FAILURE ARCHAEOLOGY & FUTURE MEMORY                                                                                            |
|            |                                                                                                                               |
|            | Failure F-183                                                                                                                   |
|            | Trigger -> Authentication provider migration                                                                                   |
|            | Observed -> Session refresh bypassed tenant authorization                                                                        |
|            | Affected behavior -> Tenant isolation                                                                                           |
|            | Detection -> Ghost #221 + Adversarial scenario #14                                                                             |
|            | Severity -> CRITICAL                                                                                                            |
|            |                                                                                                                               |
|            | Preserve Failure                                                                                                                 |
|            |      -> persistent evidence                                                                                                      |
|            |      -> historical scenario remains attached                                                                                     |
|            |      -> associated with AUTH-017                                                                                                 |
|            |      -> reusable future behavioral memory                                                                                        |
|            |                                                                                                                               |
| SCREEN 19 | FINAL INTENT ALIGNMENT                                                                                                          |
|            |                                                                                                                               |
|            | Passkey addition -> explained                                                                                                   |
|            | Provider replacement -> explained                                                                                               |
|            | Password login -> preserved                                                                                                     |
|            | Session compatibility -> preserved                                                                                              |
|            | Authorization semantics -> preserved                                                                                             |
|            | Latency +6.2% -> within limit                                                                                                   |
|            | Unexplained changes -> 0                                                                                                        |
|            | Critical unauthorized changes -> 0                                                                                              |
|            |                                                                                                                               |
|            | CERTIFICATION ELIGIBLE                                                                                                          |
|            |                                                                                                                               |
| SCREEN 20 | CHANGE CERTIFICATE                                                                                                              |
|            |                                                                                                                               |
|            | CERTIFIED                                                                                                                       |
|            |                                                                                                                               |
|            | IDENTITY                                                                                                                        |
|            | Change #184 | Commit 8f2a1e7                                                                                                     |
|            |                                                                                                                               |
|            | BEHAVIOR                                                                                                                       |
|            | Protected behaviors 32 / 32 | Unintended deltas 0                                                                             |
|            |                                                                                                                               |
|            | VERIFICATION                                                                                                                   |
|            | Historical scenarios 8 | Metamorphic checks 7 | Mutation coverage 93% | Critical violations 0                           |
|            |                                                                                                                               |
|            | INTEGRITY                                                                                                                      |
|            | Environment hash | Dependency state LOCKED | Certificate hash SHA256: 8f21...91ab                                             |
|            | Evidence status = VERIFIED                                                                                                      |
|            |                                                                                                                               |
|            | PROVENANCE                                                                                                                     |
|            | Certificate -> Claim -> Behavioral Delta -> Experiment -> Execution Trace -> Code / Environment                             |
|            |                                                                                                                               |
|            | CERTIFICATE OUTPUT                                                                                                              |
|            | Evidence-bound, machine-verifiable certification artifact                                                                       |
|                                                                                                                                          |
| SCREEN 21 | CONTINUOUS BEHAVIORAL EVOLUTION                                                                                                 |
|            |                                                                                                                               |
|            | Historical Memory                                                                                                               |
|            |        |                                                                                                                        |
|            |        v                                                                                                                        |
|            | Behavioral Constitution                                                                                                        |
|            |        |                                                                                                                        |
|            |        v                                                                                                                        |
|            | Human Intent                                                                                                                    |
|            |        |                                                                                                                        |
|            |        v                                                                                                                        |
|            | Verified Change                                                                                                                 |
|            |        |                                                                                                                        |
|            |        v                                                                                                                        |
|            | New Behavioral Evidence                                                                                                        |
|            |        |                                                                                                                        |
|            |        v                                                                                                                        |
|            | Future Evolution                                                                                                                |
|            |                                                                                                                               |
|            | Certified change -> Merge                                                                                                      |
|            |                 -> supported merged software state                                                                            |
|            |                 -> certificate remains attached                                                                               |
|            |                 -> preserved failure + verification evidence remain in behavioral memory                                    |
|            |                                                                                                                               |
|            | CERTIFY OUTPUT                                                                                                                  |
|            | Certified Software Change + Expanded Behavioral Memory                                                                         |
+------------------------------------------------------------------------------------------------------------------------------------------+


| CORE DATA / TRUST FLOW                                                                                                                   |
|------------------------------------------------------------------------------------------------------------------------------------------|
| HISTORICAL MEMORY                                                                                                                        |
| source + Git + runtime + tests + incidents + dependencies + Ghosts                                                                      |
|        |                                                                                                                                 |
|        v                                                                                                                                 |
| EVIDENCE-BACKED BEHAVIORAL KNOWLEDGE                                                                                                    |
|        |                                                                                                                                 |
|        v                                                                                                                                 |
| BEHAVIORAL CONSTITUTION                                                                                                                  |
| governed claims + authority + confidence + protected state                                                                               |
|        |                                                                                                                                 |
|        v                                                                                                                                 |
| HUMAN INTENT                                                                                                                            |
| Intent Ledger #184 -> LOCKED                                                                                                             |
|        |                                                                                                                                 |
|        v                                                                                                                                 |
| SEMANTIC IMPACT MAP                                                                                                                      |
| behavioral relationships + code + functions + dependencies + data flows + risk + Ghosts                                                |
|        |                                                                                                                                 |
|        v                                                                                                                                 |
| VERIFICATION PLAN                                                                                                                        |
| required independent verification contract -> LOCKED                                                                                    |
|        |                                                                                                                                 |
|        v                                                                                                                                 |
| CODING AGENT                                                                                                                            |
|        |                                                                                                                                 |
|        v                                                                                                                                 |
| CANDIDATE PATCH #1                                                                                                                       |
|        |                                                                                                                                 |
|        |------------------------------ TRUST BOUNDARY ------------------------------|                                             |
|        |                                                                         |                                             |
|        v                                                                         v                                             |
| DEVELOPMENT PLANE                                                        INDEPENDENT VERIFICATION PLANE                                  |
| Coding Agent                                                             Static Analysis                                                 |
| Candidate Patch                                                          Differential Execution                                          |
| NOT CERTIFIED                                                            Historical Ghosts                                               |
|                                                                           Metamorphic Checks                                              |
|                                                                           Adversarial Scenarios                                           |
|                                                                           Mutation Testing                                                |
|                                                                                 |                                                       |
|                                                                                 v                                                       |
|                                                                              EVIDENCE                                                     |
|                                                                                 |                                                       |
|                                                                                 v                                                       |
|                                                                          CLAIM-LEVEL FUSION                                                |
|                                                                                 |                                                       |
|                                                                                 v                                                       |
|                                                                      BEHAVIORAL DELTA                                                     |
|                                                                                 |                                                       |
|                                                                                 v                                                       |
|                                                                      INTENT ALIGNMENT                                                      |
|                                                                                 |                                                       |
|                                                     +---------------------------+---------------------------+                             |
|                                                     |                                                       |                             |
|                                                     v                                                       v                             |
|                                               AUTHORIZED                                            UNAUTHORIZED                           |
|                                                                                                         |                                   |
|                                                                                                         v                                   |
|                                                                                                 REPAIR REQUIRED                            |
|                                                                                                         |                                   |
|                                                                                                         v                                   |
|                                                                                                  Coding Agent                             |
|                                                                                                         |                                   |
|                                                                                                         v                                   |
|                                                                                                  CANDIDATE PATCH #2                         |
|                                                                                                         |                                   |
|                                                                                                         v                                   |
|                                                                                              INDEPENDENT RE-VERIFICATION                   |
|                                                                                                         |                                   |
|                                                                                                         v                                   |
|                                                                                               FINAL INTENT ALIGNMENT                        |
|                                                                                                         |                                   |
|                                                                                                         v                                   |
|                                                                                                  CERTIFICATION ELIGIBLE                    |
|                                                                                                         |                                   |
|                                                                                                         v                                   |
|                                                                                                 CHANGE CERTIFICATE                          |
|                                                                                                         |                                   |
|                                                                                                         v                                   |
|                                                                                                     MERGE                                    |
|                                                                                                         |                                   |
|                                                                                                         v                                   |
|                                                                                          EXPANDED BEHAVIORAL MEMORY                         |
|                                                                                                         |                                   |
|                                                                                                         +-------------> FUTURE EVOLUTION    |
+------------------------------------------------------------------------------------------------------------------------------------------+


| IMMUTABLE / OWNED STATE MODEL                                                                                                            |
|------------------------------------------------------------------------------------------------------------------------------------------|
| Behavioral Constitution | owns governance state        | LOCKED before downstream change analysis                                      |
| Intent Ledger            | owns human intent          | LOCKED after Confirm Intent                                                     |
| Semantic Impact Map      | owns semantic impact      | FROZEN before verification planning                                             |
| Verification Plan        | owns verification contract| LOCKED before Coding Agent is invoked                                            |
| Candidate Patch          | owns development output   | UNVERIFIED / NOT CERTIFIED                                                      |
| Independent Verification | owns investigation        | produces independent evidence                                                   |
| Behavioral Delta         | owns observed difference  | distinct from verification                                                      |
| Certificate              | owns certification state  | binds implementation + environment + dependencies + verification + behavior    |
| Failure F-183             | preserved historical evidence | never overwritten by successful repair                                      |
+------------------------------------------------------------------------------------------------------------------------------------------+


| CONTEXTUAL VIEW ARCHITECTURE                                                                                                             |
|------------------------------------------------------------------------------------------------------------------------------------------|
| Evidence Inspector            -> source / Git / runtime / incident / tests / related claim                                             |
| Claim Inspector               -> claim / authority / confidence / status / evidence / affected software / verification               |
| Historical vs Intent Inspector-> what happened / what should happen / conflicts                                                       |
| Conflict Review Modal         -> historical behavior / current intent / authority / proposed classification                         |
| Ghost Inspector               -> event / input / state / dependencies / configuration / feature flags / environment / replay        |
| Execution Trace Drawer        -> old path / new path / outcomes / root behavioral difference                                          |
| Semantic Relationship Inspector-> upstream/downstream behavior / dependencies / protected behavior / historical risk / Ghosts       |
| Verification Module Detail    -> module-specific cases/results                                                                       |
| Mutation Detail               -> mutation / detection state / relevant mechanism                                                     |
| Behavioral Change Inspector   -> baseline / new path / evidence / affected claim                                                     |
| Unauthorized Decision Inspector-> claim / intent / observed behavior / evidence / severity                                            |
| Repair Evidence Inspector     -> triggering evidence inside repair package                                                           |
| Certificate Evidence Drawer   -> certificate -> claim -> delta -> experiment -> execution -> code/environment                        |
|                                                                                                                                          |
| ALL ARE CONTEXTUAL — NONE BECOMES A NEW PRIMARY PAGE                                                                                     |
+------------------------------------------------------------------------------------------------------------------------------------------+


| DEFINING LOGIC                                                                                                                           |
|------------------------------------------------------------------------------------------------------------------------------------------|
| HISTORY        -> what the software has historically done                                                                                |
| CONSTITUTION   -> what behavior is governed                                                                                              |
| INTENT         -> what the human wants changed and preserved                                                                              |
| EVIDENCE       -> what independent investigation actually establishes                                                                    |
| CERTIFICATE    -> what has ultimately been proven                                                                                         |
|                                                                                                                                          |
| PRIMARY PRODUCT EQUATION                                                                                                                  |
| HISTORY -> GOVERNANCE -> INTENT -> IMPACT -> VERIFICATION -> CHANGE -> EVIDENCE -> ALIGNMENT -> CERTIFICATION -> MEMORY               |
|                                                                                                                                          |
| TRUST RULE                                                                                                                               |
| Candidate -> Independent Investigation -> Evidence -> Intent Alignment -> Certification                                                 |
| NEVER: Candidate -> Certified                                                                                                             |
|                                                                                                                                          |
| EVIDENCE STATE                                                                                                                           |
| Collected -> Linked -> Interpreted -> Claim-Level Assessment                                                                             |
|                                                                                                                                          |
| FAILURE STATE                                                                                                                            |
| Failed -> Repaired                                                                                                                       |
| while original failure remains Preserved Historical Evidence                                                                             |
|                                                                                                                                          |
| CERTIFICATION STATE                                                                                                                      |
| Eligible -> Certified -> Machine-Verifiable -> Active                                                                                     |
|                                                                                                                                          |
| FINAL LOOP                                                                                                                               |
| Discover behavior -> Govern behavior -> Define intent -> Analyze impact -> Lock verification -> Develop -> Independently verify          |
| -> Fuse evidence -> Determine behavioral delta -> Align with intent -> Repair -> Re-verify -> Certify -> Preserve memory -> Evolve again |
|                                                                                                                                          |
| FINAL SYSTEM STATEMENT                                                                                                                   |
| The Coding Agent can propose the change. It cannot decide by itself that the change is safe.                                          |
| Evidence establishes what changed. Intent establishes what was allowed. Independent verification establishes what can be trusted.      |
+------------------------------------------------------------------------------------------------------------------------------------------+

+==============================================================================================================================+
|                                      SOFTWARE EVOLUTION INTELLIGENCE SYSTEM                                                  |
|                                                                                                                              |
|                  Evidence-first behavioral understanding + governed change + independent verification                       |
+==============================================================================================================================+

                                                    +----------------------+
                                                    |        USER          |
                                                    | Human intent / review|
                                                    +----------+-----------+
                                                               |
                                                               v
+------------------------------------------------------------------------------------------------------------------------------+
|                                         APPLICATION / ORCHESTRATION LAYER                                                    |
|------------------------------------------------------------------------------------------------------------------------------|
|                                                                                                                              |
|  +------------------+     +------------------+     +------------------+     +------------------+                            |
|  | Software         | --> | Behavioral       | --> | Behavioral       | --> | Change           |                            |
|  | Archaeology      |     | Knowledge        |     | Constitution     |     | Definition      |                            |
|  |                  |     | Model            |     |                  |     | + Intent Ledger |                            |
|  +------------------+     +------------------+     +------------------+     +------------------+                            |
|          |                         |                        |                         |                                      |
|          |                         |                        |                         v                                      |
|          |                         |                        |                +------------------+                            |
|          |                         |                        +--------------> | Semantic Impact  |                            |
|          |                         |                                         | Analysis         |                            |
|          |                         |                                         +--------+---------+                            |
|          |                         |                                                  |                                      |
|          |                         |                                                  v                                      |
|          |                         |                                         +------------------+                            |
|          |                         +---------------------------------------> | Verification    |                            |
|          |                                                                   | Contract / Lock |                            |
|          |                                                                   +--------+---------+                            |
|          |                                                                            |                                      |
|          |                                                                            v                                      |
|          |                                                                   +------------------+                            |
|          |                                                                   | Coding Agent     |                            |
|          |                                                                   | Development Plane|                            |
|          |                                                                   +--------+---------+                            |
|          |                                                                            |                                      |
|          |                                                                            v                                      |
|          |                                                                   +------------------+                            |
|          |                                                                   | Candidate Patch  |                            |
|          |                                                                   | #1              |                            |
|          |                                                                   +--------+---------+                            |
|          |                                                                            |                                      |
+----------|----------------------------------------------------------------------------|-------------------------------------+
           |                                                                            |
           |                                                                            | TRUST BOUNDARY
           |                                                                            |
           |                                                                            v
+------------------------------------------------------------------------------------------------------------------------------+
|                                      INDEPENDENT VERIFICATION PLANE                                                          |
|                                                                                                                              |
|                                  +------------------------------------------+                                              |
|                                  |     INDEPENDENT VERIFICATION LAB         |                                              |
|                                  |                                          |                                              |
|                                  |  Candidate Patch #1                      |                                              |
|                                  |  Verification Plan — LOCKED             |                                              |
|                                  |  Behavioral Constitution v1.0           |                                              |
|                                  |                                          |                                              |
|                                  |              +----------------+        |                                              |
|                                  |              | Verification    |        |                                              |
|                                  |              | Control Center  |        |                                              |
|                                  |              +--------+-------+        |                                              |
|                                  |                       |                |                                              |
|                                  |        +--------------+--------------+ |                                              |
|                                  |        |              |              | |                                              |
|                                  |        v              v              v |                                              |
|                                  |  +-----------+  +-----------+  +-----------+                                         |
|                                  |  | Static    |  |Differential| | Historical|                                         |
|                                  |  | Analysis  |  | Execution  | | Ghosts    |                                         |
|                                  |  +-----------+  +-----------+  +-----------+                                         |
|                                  |        |              |              |                                                    |
|                                  |        +--------------+--------------+                                                    |
|                                  |                       |                                                                   |
|                                  |        +--------------+--------------+                                                    |
|                                  |        |              |              |                                                    |
|                                  |        v              v              v                                                    |
|                                  |  +-----------+  +-----------+  +-----------+                                           |
|                                  |  |Metamorphic |  |Adversarial| | Mutation  |                                           |
|                                  |  |  Checks   |  | Scenarios | | Testing   |                                           |
|                                  |  +-----------+  +-----------+  +-----------+                                           |
|                                  |                       |                                                                   |
|                                  |                       v                                                                   |
|                                  |             +----------------------+                                                      |
|                                  |             | Evidence Collection  |                                                      |
|                                  |             +----------+-----------+                                                      |
|                                  +------------------------|-----------------------------------------------------------------+
|                                                           |
|                                                           v
+------------------------------------------------------------------------------------------------------------------------------+
|                                           EVIDENCE / REASONING LAYER                                                          |
|------------------------------------------------------------------------------------------------------------------------------|
|                                                                                                                              |
|                              +-----------------------------+                                                                 |
|                              |      Claim Evidence         |                                                                 |
|                              |          & Fusion           |                                                                 |
|                              +-------------+---------------+                                                                 |
|                                            |                                                                                 |
|                         +------------------+------------------+                                                              |
|                         |                  |                  |                                                              |
|                         v                  v                  v                                                              |
|                  Authority           Relevance           Provenance                                                            |
|                  Severity            Confidence           Evidence type                                                      |
|                         |                  |                  |                                                              |
|                         +------------------+------------------+                                                              |
|                                            |                                                                                 |
|                                            v                                                                                 |
|                                 +------------------------+                                                                    |
|                                 | Claim-Level Assessment |                                                                    |
|                                 +-----------+------------+                                                                    |
|                                             |                                                                                  |
|                                  +----------+----------+                                                                       |
|                                  |                     |                                                                       |
|                                  v                     v                                                                       |
|                              SUPPORTING           CONTRADICTING                                                                 |
|                              EVIDENCE              EVIDENCE                                                                      |
|                                  |                     |                                                                       |
|                                  +----------+----------+                                                                       |
|                                             |                                                                                 |
|                                             v                                                                                 |
|                                  +------------------------+                                                                    |
|                                  | Behavioral Delta       |                                                                    |
|                                  | What actually changed |                                                                    |
|                                  +-----------+------------+                                                                    |
|                                              |                                                                                |
|                                              v                                                                                |
|                                  +------------------------+                                                                    |
|                                  | Intent Alignment       |                                                                    |
|                                  | Was it authorized?     |                                                                    |
|                                  +-----------+------------+                                                                    |
|                                              |                                                                                |
|                              +---------------+---------------+                                                                |
|                              |                               |                                                                |
|                              v                               v                                                                |
|                          AUTHORIZED                    UNEXPLAINED / UNAUTHORIZED                                               |
|                                                              |                                                                |
+--------------------------------------------------------------|-----------------------------------------------------------------+
                                                               |
                                                               v
+------------------------------------------------------------------------------------------------------------------------------+
|                                               REPAIR / TRUST RECOVERY                                                        |
|------------------------------------------------------------------------------------------------------------------------------|
|                                                                                                                              |
|                                      +-----------------------------+                                                         |
|                                      |      Certification Decision |                                                         |
|                                      +-------------+---------------+                                                         |
|                                                    |                                                                            |
|                                                    v                                                                            |
|                                           +----------------+                                                                    |
|                                           | REPAIR REQUIRED|                                                                    |
|                                           +--------+-------+                                                                    |
|                                                    |                                                                            |
|                                                    v                                                                            |
|                                      +-----------------------------+                                                         |
|                                      | Failure / Repair Package   |                                                         |
|                                      |                           |                                                         |
|                                      | Failure F-183             |                                                         |
|                                      | Expected behavior         |                                                         |
|                                      | Observed behavior         |                                                         |
|                                      | Protected claim AUTH-017 |                                                         |
|                                      | Evidence                  |                                                         |
|                                      | Suspected path            |                                                         |
|                                      | Required outcome          |                                                         |
|                                      +-------------+---------------+                                                         |
|                                                    |                                                                            |
|                                                    v                                                                            |
|                                      +-----------------------------+                                                         |
|                                      | Coding Agent — Repair     |                                                         |
|                                      | Candidate Patch #2        |                                                         |
|                                      +-------------+---------------+                                                         |
|                                                    |                                                                            |
|                                                    v                                                                            |
|                                      +-----------------------------+                                                         |
|                                      | Independent Re-Verification|                                                        |
|                                      | Same locked conditions    |                                                         |
|                                      +-------------+---------------+                                                         |
|                                                    |                                                                            |
|                                                    v                                                                            |
|                                      +-----------------------------+                                                         |
|                                      | Before / After Evidence   |                                                         |
|                                      | FAIL -> PASS              |                                                         |
|                                      +-------------+---------------+                                                         |
|                                                    |                                                                            |
|                                                    v                                                                            |
|                                      +-----------------------------+                                                         |
|                                      | Final Intent Alignment    |                                                         |
|                                      | Unexplained changes = 0   |                                                         |
|                                      | Unauthorized changes = 0  |                                                         |
|                                      +-------------+---------------+                                                         |
|                                                    |                                                                            |
|                                                    v                                                                            |
|                                      +-----------------------------+                                                         |
|                                      |     CHANGE CERTIFICATE     |                                                         |
|                                      |                            |                                                         |
|                                      | Change                      |                                                         |
|                                      | Commit                      |                                                         |
|                                      | Protected behaviors         |                                                         |
|                                      | Verification evidence      |                                                         |
|                                      | Environment                |                                                         |
|                                      | Dependency state           |                                                         |
|                                      | Certificate identity       |                                                         |
|                                      +-------------+--------------+                                                         |
|                                                    |                                                                            |
|                                                    v                                                                            |
|                                               CERTIFIED                                                                        |
|                                                    |                                                                            |
|                                                    v                                                                            |
|                                                 MERGE                                                                          |
+----------------------------------------------------|-------------------------------------------------------------------------+
                                                     |
                                                     v
+------------------------------------------------------------------------------------------------------------------------------+
|                                            BEHAVIORAL MEMORY / KNOWLEDGE                                                     |
|------------------------------------------------------------------------------------------------------------------------------|
|                                                                                                                              |
|  +----------------------+                                                                                                    |
|  | Historical Memory    |<---------------------------------------------------------------------------------------------+    |
|  |                      |                                                                                              |    |
|  | Source code          |                                                                                              |    |
|  | Git history          |                                                                                              |    |
|  | Runtime observations |                                                                                              |    |
|  | Tests                |                                                                                              |    |
|  | Incidents            |                                                                                              |    |
|  | Dependencies         |                                                                                              |    |
|  | Ghosts               |                                                                                              |    |
|  +----------+-----------+                                                                                              |    |
|             |                                                                                                           |    |
|             v                                                                                                           |    |
|  +----------------------+       +----------------------+       +----------------------+                                 |    |
|  | Behavioral Findings  | ----> | Behavioral Knowledge | ----> | Behavioral           |                                 |    |
|  | Behaviors            |       | / Knowledge Graph   |       | Constitution         |                                 |    |
|  | Invariants           |       |                      |       | Protected claims     |                                 |    |
|  | Risk zones           |       | Behavior relationships|      | Authority            |                                 |    |
|  | Couplings            |       | Evidence relationships|      | Confidence           |                                 |    |
|  +----------------------+       +----------------------+       +----------+-----------+                                 |    |
|                                                                            |                                             |    |
|                                                                            v                                             |    |
|                                                                  Future Change Context                                     |    |
|                                                                            |                                             |    |
|                                                                            +---------------------------------------------+    |
|                                                                                                                          |    |
|  +----------------------+       +----------------------+       +----------------------+                                 |    |
|  | Failure F-183        | ----> | Ghost #221           | ----> | Future verification |---------------------------------+    |
|  | Preserved failure    |       | Historical scenario  |       | / behavioral memory  |                                      |
|  +----------------------+       +----------------------+       +----------------------+                                      |
|                                                                                                                              |
+------------------------------------------------------------------------------------------------------------------------------+


+==============================================================================================================================+
|                                             CORE ARCHITECTURAL RELATIONSHIPS                                                  |
|==============================================================================================================================|
|                                                                                                                              |
|  SOFTWARE REALITY                                                                                                            |
|  Source + Git + Runtime + Tests + Incidents + Dependencies                                                                  |
|                              |                                                                                               |
|                              v                                                                                               |
|  SOFTWARE ARCHAEOLOGY                                                                                                        |
|                              |                                                                                               |
|                              v                                                                                               |
|  EVIDENCE-BACKED BEHAVIORAL MEMORY                                                                                           |
|                              |                                                                                               |
|                              v                                                                                               |
|  BEHAVIORAL KNOWLEDGE GRAPH                                                                                                  |
|                              |                                                                                               |
|                              v                                                                                               |
|  BEHAVIORAL CONSTITUTION                                                                                                     |
|                              |                                                                                               |
|                              +----------------------------+                                                                  |
|                                                           |                                                                  |
|                                                           v                                                                  |
|                                                    HUMAN INTENT                                                               |
|                                                           |                                                                  |
|                                                           v                                                                  |
|                                                   INTENT LEDGER                                                               |
|                                                           |                                                                  |
|                                                           v                                                                  |
|                                                  SEMANTIC IMPACT                                                             |
|                                                           |                                                                  |
|                                                           v                                                                  |
|                                                VERIFICATION CONTRACT                                                        |
|                                                           |                                                                  |
|                                                           v                                                                  |
|                                                     CODING AGENT                                                              |
|                                                           |                                                                  |
|                                                           v                                                                  |
|                                                  CANDIDATE PATCH                                                             |
|                                                           |                                                                  |
|                                         +-----------------+-----------------+                                                |
|                                         |                                   |                                                |
|                                         v                                   X                                                |
|                              INDEPENDENT VERIFICATION                  AGENT CONTROL                                        |
|                                         |                                   |                                                |
|                                         v                                   |                                                |
|                                      EVIDENCE                              BLOCKED                                             |
|                                         |                                                                            |
|                                         v                                                                            |
|                                CLAIM EVIDENCE FUSION                                                          |
|                                         |                                                                            |
|                                         v                                                                            |
|                                  BEHAVIORAL DELTA                                                              |
|                                         |                                                                            |
|                                         v                                                                            |
|                                  INTENT ALIGNMENT                                                             |
|                                         |                                                                            |
|                           +-------------+-------------+                                                       |
|                           |                           |                                                       |
|                           v                           v                                                       |
|                      AUTHORIZED               UNAUTHORIZED                                                   |
|                                                       |                                                       |
|                                                       v                                                       |
|                                               EVIDENCE-DRIVEN REPAIR                                           |
|                                                       |                                                       |
|                                                       v                                                       |
|                                             CANDIDATE PATCH #2                                                |
|                                                       |                                                       |
|                                                       v                                                       |
|                                          INDEPENDENT RE-VERIFICATION                                         |
|                                                       |                                                       |
|                                                       v                                                       |
|                                              FINAL ALIGNMENT                                                |
|                                                       |                                                       |
|                                                       v                                                       |
|                                              CHANGE CERTIFICATE                                              |
|                                                       |                                                       |
|                                                       v                                                       |
|                                                     MERGE                                                    |
|                                                       |                                                       |
|                                                       v                                                       |
|                                          EXPANDED BEHAVIORAL MEMORY                                           |
|                                                       |                                                       |
|                                                       +--------------------> FUTURE EVOLUTION                |
|                                                                                                                              |
+==============================================================================================================================+


+------------------------------------------------------------------------------------------------------------------------------+
|                                             TRUST / DATA INTEGRITY RULES                                                      |
|------------------------------------------------------------------------------------------------------------------------------|
|                                                                                                                              |
|  HISTORICAL MEMORY       !=       INTENT                                                                                     |
|  AUTHORITY               !=       CONFIDENCE                                                                                  |
|  VERIFICATION            !=       BEHAVIORAL DELTA                                                                            |
|  BEHAVIORAL DELTA        !=       INTENT ALIGNMENT                                                                            |
|  CANDIDATE               !=       CERTIFIED                                                                                   |
|  FAILURE                 !=       DELETION                                                                                    |
|                                                                                                                              |
|  LOCKED OBJECTS                                                                                                              |
|  Behavioral Constitution                                                                                                     |
|  Intent Ledger                                                                                                               |
|  Semantic Impact Map                                                                                                          |
|  Verification Plan                                                                                                           |
|                                                                                                                              |
|  PRESERVED FAILURE                                                                                                           |
|  Candidate Patch #1 failure -> F-183 -> Ghost #221 -> permanent behavioral evidence                                        |
|                                                                                                                              |
|  CERTIFICATION PROVENANCE                                                                                                    |
|  Certificate -> Claim -> Behavioral Delta -> Experiment -> Execution Trace -> Code / Environment                            |
|                                                                                                                              |
|  FINAL PRODUCT STATE                                                                                                         |
|  Certified Software Change + Expanded Behavioral Memory                                                                      |
+------------------------------------------------------------------------------------------------------------------------------+