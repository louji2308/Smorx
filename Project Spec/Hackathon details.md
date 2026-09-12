I researched the current Devpost page, official rules, judging information, organizer announcements, Nebius Token Factory documentation, Token Factory Sandboxes/SWE-agent documentation, NVIDIA Nemotron documentation, NVIDIA NeMo Agent Toolkit, and the related Nebius/NVIDIA builder material.

The important conclusion is this:

> **Track 1 is fundamentally an autonomous software-engineering agent track.**
> The strongest interpretation is not “an AI that writes code,” but an agent that can take a real software task, inspect a repository, plan a change, modify code, execute it inside an isolated sandbox, run tests, observe failures, fix them, and iterate toward a verified result.

---

# 1. Hackathon overview

## Official hackathon

**Nebius x NVIDIA Global AI Hackathon**

Theme:

> **“Build the next frontier of AI on open infrastructure.”**

The hackathon is run by **Nebius**, with NVIDIA technology at the center of the required stack. The current Devpost status is **submissions open**. ([Nebius x NVIDIA Global AI Hackathon][1])

[Official Devpost hackathon page](https://nebiusglobalaihackathon.devpost.com/?utm_source=chatgpt.com)

The central requirement is unusually important:

> Every submission must run on **Nebius Token Factory or Nebius AI Cloud** and use **at least one NVIDIA open-source model**. ([Nebius x NVIDIA Global AI Hackathon][1])

So the hackathon is not simply asking you to build an AI application and mention Nebius somewhere. The infrastructure/model relationship is part of the judging.

---

# 2. Important dates

| Event               | Date                                   |
| ------------------- | -------------------------------------- |
| Submissions opened  | **August 26, 2026**                    |
| Submission deadline | **October 30, 2026, 10:00 AM Pacific** |
| Judging             | November/December 2026                 |
| Winners announced   | **January 11, 2027**                   |

The Devpost key-date service currently reports the submission deadline as **October 30, 2026 at 17:00 UTC**, which is **10:30 PM IST on October 30**.

### Important date discrepancy

I found one inconsistency worth knowing about.

Devpost's current key-date data reports judging beginning **November 2, 2026**, while the **Official Rules** currently state a judging period beginning **December 1, 2026**.

Because the official rules explicitly control in the event of conflicts with other hackathon materials, I would treat the **Official Rules as authoritative** unless the organizers publish an update. ([Nebius x NVIDIA Global AI Hackathon][2])

[Official Rules](https://nebiusglobalaihackathon.devpost.com/rules?utm_source=chatgpt.com)

---

# 3. Prize structure

The advertised prize pool is **$50,000+ in value**.

| Prize                              |                       Award |
| ---------------------------------- | --------------------------: |
| Grand Prize                        |                 **$20,000** |
| 2nd Place                          |                 **$10,000** |
| 3rd Place                          |                  **$6,000** |
| Coding & Agentic Engineering Track | **NVIDIA Jetson Orin Nano** |
| Best Apps & Agents Track           | **NVIDIA Jetson Orin Nano** |
| Personal AI Track                  | **NVIDIA Jetson Orin Nano** |
| Physical AI Track                  | **NVIDIA Jetson Orin Nano** |
| Best Use of Tavily                 |                  **$3,000** |
| City Winner Awards                 |        **$500 × 20 cities** |
| Most Valuable Feedback             | **$100 + NVIDIA swag × 10** |

The Devpost prize listing reports a total value of **$50,000** when cash and stated prize values are aggregated. ([Nebius x NVIDIA Global AI Hackathon][1])

There is also an important strategic implication: you are not necessarily competing only for the overall top three. **Track-specific awards create another route to winning**, particularly if your project is architected specifically around Track 1.

---

# 4. The four tracks

## Track 1 — Coding and Agentic Engineering

> Build **coding agents and developer tools**: agents that **write, run, and test code in Token Factory Sandboxes**. ([Nebius x NVIDIA Global AI Hackathon][1])

This is the track you're targeting.

## Track 2 — Best Apps and Agents

Build a useful application or agent people would actually use.

The organizers specifically encourage using:

* Nemotron 3 Ultra for difficult reasoning
* Nemotron Nano/Super for faster calls
* Nebius Serverless Endpoints
* Nebius Serverless Jobs

The intended idea is broader product/workflow automation.

## Track 3 — Personal AI

Build an always-on, private assistant with things such as:

* persistent memory
* reusable skills
* user-selected tools
* access to personal information
* ability to execute tasks

The page specifically references tools such as **NemoClaw, OpenShell, Hermes Agent, and Nebius Serverless**.

## Track 4 — Physical AI

Embodied/edge systems involving:

* robotics
* IoT
* on-device intelligence
* real-world sensing and acting

Relevant NVIDIA technologies include:

* Nemotron
* GR00T
* Cosmos
* Sonic

The demo requirement is much stricter here because the video has to visibly demonstrate hardware or, for hardware-free variants, the relevant application modules.

---

# 5. The most important judging information

The judging process has two conceptual stages.

### Stage 1 — baseline viability

The organizers first determine whether the submission is actually viable and fits the theme.

That means:

* it should genuinely attempt the assigned track;
* it should actually use the required infrastructure/models;
* the required technology cannot just be superficial branding around an unrelated project.

This is very important for Track 1.

A project that has a polished chat interface saying:

> “I am an autonomous coding agent”

but never actually executes code in a Token Factory Sandbox is vulnerable immediately.

---

## Stage 2 — four equally weighted criteria

Every qualifying submission is scored **1–5** on:

### 1. Technological Implementation

> How well is the project built, and how effectively does it use **Nebius Token Factory / AI Cloud** and **NVIDIA Nemotron**?

### 2. Design

> Does the project deliver a complete, coherent product experience rather than merely a technical proof of concept?

### 3. Potential Impact

> Does it solve a credible, specific problem for a real audience?

### 4. Quality of the Idea

> Is the use of Nebius/NVIDIA creative and non-obvious, and does the team demonstrate genuine understanding of the problem?

These are **equally weighted**, meaning conceptually **25% each**. ([Nebius x NVIDIA Global AI Hackathon][2])

There is also a tie-breaking hierarchy that starts with **Technological Implementation**, followed by Design, Impact, and Idea. That makes deep technical execution particularly valuable when strong submissions are close.

---

# 6. The latest organizer guidance is extremely important for Track 1

The organizer's September 11 update effectively tells you what they consider too basic.

For **Coding and Agentic Engineering**, they say a:

> code-completion wrapper is a starting point;

whereas an agent that:

> **plans, writes, tests, and iterates on a real repository with minimal human input**

is much more interesting.

That is probably the single most important piece of information for you.

The distinction is:

**Weak**

`Prompt → Generate Code → Show Code`

**Much stronger**

`Task → Understand Repo → Plan → Modify → Execute → Test → Observe Failure → Diagnose → Patch → Retest → Verify`

[Devpost announcements / organizer updates](https://nebiusglobalaihackathon.devpost.com/updates?utm_source=chatgpt.com)

---

# 7. What Track 1 actually wants

Here is the clearest interpretation of the requirement.

A Track 1 system should behave more like a **software engineer operating a computer environment** than a chatbot.

Imagine I give your system:

> “The login endpoint returns 500 when a user has an expired session. Fix it and make sure the relevant tests pass.”

A serious Track 1 agent could:

### Step 1 — Understand the task

Parse the request into an engineering objective.

### Step 2 — Inspect the repository

Discover:

* project structure
* relevant files
* dependencies
* tests
* configuration
* existing implementation

### Step 3 — Create a plan

Determine:

* likely root cause
* files to modify
* tests to run
* validation strategy

### Step 4 — Make changes

Actually write/edit repository files.

### Step 5 — Execute

Run:

* unit tests
* integration tests
* linters
* type checks
* build commands
* application commands

### Step 6 — Observe

Capture:

* exit code
* stdout
* stderr
* stack traces
* generated artifacts
* test failures

### Step 7 — Reason about failure

The model sees the actual result and decides what to change.

### Step 8 — Iterate

Modify the repository and run the tests again.

### Step 9 — Verify

Stop only once the acceptance criteria are satisfied.

### Step 10 — Produce an engineering result

Return something concrete such as:

* final diff
* tests passed
* files changed
* explanation
* confidence/verification status

That is the heart of Track 1.

---

# 8. Why Nebius Token Factory Sandboxes matter so much

This is where the hackathon becomes much more interesting than a normal “AI coding assistant” competition.

Nebius has a dedicated **Sandbox** system for code execution.

Official documentation describes these as cloud-based environments for secure code execution with:

* **VM-level isolation**
* container efficiency
* Git-like branching
* checkpoints
* rollback
* file execution
* resource metrics
* asynchronous execution
* OCI image support

They are explicitly positioned for **AI coding agents** and related workloads. ([Nebius Token Factory documentation][3])

[Token Factory Sandboxes overview](https://docs.tokenfactory.nebius.com/sandboxes/overview?utm_source=chatgpt.com)

This means your architecture can fundamentally become:

```text
                USER
                  │
                  ▼
          ┌─────────────────┐
          │ Agent Interface │
          └────────┬────────┘
                   │
                   ▼
          ┌─────────────────┐
          │ Agent Controller│
          └────────┬────────┘
                   │
          ┌────────┴─────────┐
          ▼                  ▼
   Nemotron Model       Tool Layer
          │                  │
          └────────┬─────────┘
                   ▼
        ┌──────────────────────┐
        │ Nebius Token Factory │
        │      Sandbox         │
        ├──────────────────────┤
        │ Repository            │
        │ Files                 │
        │ Commands              │
        │ Tests                 │
        │ Logs                  │
        │ Artifacts             │
        │ Git branches          │
        └──────────┬───────────┘
                   │
                   ▼
             Test Results
                   │
                   ▼
            Agent Reflection
                   │
             ┌─────┴─────┐
             │           │
           FAIL         PASS
             │           │
             ▼           ▼
          Fix        Final Diff
             │
             └──→ Re-test
```

That architecture is far closer to the organizers' stated vision than simply calling an LLM API.

---

# 9. Token Factory Sandbox capabilities particularly useful for Track 1

The documentation has several features that map almost perfectly onto an autonomous coding agent.

## Branching

A sandbox filesystem state can be branched so different strategies can be explored independently.

Conceptually:

```text
                         BASE REPO
                            │
                ┌───────────┼───────────┐
                ▼           ▼           ▼
             Strategy A  Strategy B  Strategy C
                │           │           │
              tests       tests       tests
                │           │           │
                ▼           ▼           ▼
             score A     score B     score C
                         │
                         ▼
                    choose winner
```

That is an unusually powerful feature for an agent.

You don't necessarily have to ask:

> “Which patch should I write?”

You can instead let the system explore multiple plausible repairs and compare them.

[Sandbox branching documentation](https://docs.tokenfactory.nebius.com/sandboxes/sdk/python_sdk/branching?utm_source=chatgpt.com)

---

## Rollback

Failed experiments don't have to corrupt the primary state.

That gives your agent an actual engineering loop:

`experiment → evaluate → rollback → try alternative`

[Sandbox sessions / rollback documentation](https://docs.tokenfactory.nebius.com/sandboxes/cli/tutorial/sessions?utm_source=chatgpt.com)

---

## Command execution

The SDK exposes command execution with:

* stdout
* stderr
* exit codes
* environment variables
* working directories
* persistent/non-disposable runs

That means the LLM can receive **real machine feedback**, rather than inventing whether its code works. ([Nebius Token Factory documentation][4])

[Running commands in Sandboxes](https://docs.tokenfactory.nebius.com/sandboxes/sdk/python_sdk/running-commands?utm_source=chatgpt.com)

---

# 10. SWE-agent environments

Nebius also documents **SWE-agent-oriented environments**, with thousands of preloaded software-engineering environments and references to:

* SWE-bench Verified
* SWE-rebench
* SWE-rebench-V2

The platform therefore isn't treating software agents as an accidental use case; software engineering is an explicit target for the Sandbox infrastructure. ([Nebius Token Factory documentation][5])

[Nebius SWE-agent Sandbox documentation](https://docs.tokenfactory.nebius.com/sandboxes/swe-agents?utm_source=chatgpt.com)

That is very relevant when deciding what kind of Track 1 project to build.

---

# 11. Contree: probably one of the most relevant pieces of technology for your track

Nebius' Sandbox ecosystem exposes **Contree** through multiple interfaces:

### SDK

Programmatic sandbox creation/execution.

[Contree Python SDK getting started](https://docs.tokenfactory.nebius.com/sandboxes/sdk/python_sdk/getting-started?utm_source=chatgpt.com)

### CLI

Useful for terminal-first workflows.

[Contree CLI first sandbox](https://docs.tokenfactory.nebius.com/sandboxes/cli/tutorial/first-steps?utm_source=chatgpt.com)

### MCP

This is particularly interesting.

Contree provides an MCP interface that can let an AI coding agent interact directly with sandbox environments.

[Contree MCP quickstart](https://docs.tokenfactory.nebius.com/sandboxes/mcp/quickstart?utm_source=chatgpt.com)

[Contree MCP run tool](https://docs.tokenfactory.nebius.com/sandboxes/mcp/tools/run?utm_source=chatgpt.com)

This creates a very natural architecture:

```text
Nemotron
   │
   ▼
Agent reasoning
   │
   ▼
Tool call
   │
   ▼
Contree MCP
   │
   ▼
Nebius Sandbox
   │
   ├── inspect
   ├── edit
   ├── run
   ├── test
   └── return result
```

You could also use the SDK directly instead of MCP.

---

# 12. NVIDIA models: what matters for Track 1

The hackathon requires an NVIDIA open-source model.

For Track 1, **Nemotron is the obvious strategic choice**.

The NVIDIA and Nebius ecosystem currently gives you several relevant model tiers.

---

## Nemotron 3.5 Lightning

NVIDIA's current **Nemotron 3.5 Lightning 30B-A3B** is particularly interesting for autonomous agents.

It has:

* 30B total parameters
* approximately 3B active parameters
* hybrid Mamba-2 / MoE / attention architecture
* up to 1M-token context
* positioning for long-running autonomous agents
* coding/sub-agent workloads

NVIDIA's own description positions it as a workhorse for autonomous agents and coding scenarios. ([NVIDIA NIM APIs][6])

[NVIDIA Nemotron 3.5 Lightning](https://build.nvidia.com/nvidia/nemotron-3.5-lightning-30b-a3b?utm_source=chatgpt.com)

This makes it a strong candidate for frequent agent loop calls.

---

## Nemotron 3 Super

Nebius makes **Nemotron 3 Super 120B** available through Token Factory.

Its design is intended for difficult reasoning and multi-agent workloads, with a 1M-context capability and strong software-development relevance.

[Nebius Nemotron models](https://nebius.com/services/token-factory/nemotron?utm_source=chatgpt.com)

[Nemotron 3 Super on Nebius](https://nebius.com/blog/posts/nemotron3-super-now-available?utm_source=chatgpt.com)

---

## Nemotron 3 Ultra

This is the heavyweight reasoning model.

NVIDIA describes Nemotron 3 Ultra as a model designed for:

* frontier reasoning
* long-running agentic workflows
* tool use
* very long context

It has **550B total parameters / 55B active** and up to **1M context**.

NVIDIA also reports strong agentic performance, including Terminal-Bench results, which is especially relevant to a coding-agent track. ([NVIDIA Developer][7])

[NVIDIA Nemotron 3 Ultra](https://developer.nvidia.com/blog/nvidia-nemotron-3-ultra?utm_source=chatgpt.com)

---

# 13. The model strategy I would seriously consider

You do **not** necessarily need to use the largest model for every operation.

A stronger engineering architecture is:

```text
                    Task
                      │
                      ▼
             ┌────────────────┐
             │ Task Classifier│
             └───────┬────────┘
                     │
          ┌──────────┼──────────┐
          ▼          ▼          ▼
       Simple      Normal      Hard
        task        task       task
          │          │          │
          ▼          ▼          ▼
     Lightning     Super       Ultra
          │          │          │
          └──────────┴──────────┘
                     │
                     ▼
                 Sandbox
                     │
                     ▼
                  Tests
                     │
                     ▼
              Reflection model
```

For example:

**Lightning**

For:

* repo summarization
* simple file identification
* command interpretation
* repetitive tool use
* straightforward edits

**Super**

For:

* normal coding decisions
* debugging
* implementation
* multi-file reasoning

**Ultra**

For:

* difficult root-cause analysis
* architectural changes
* ambiguous failures
* high-level planning
* final review/reflection

That would also give you an excellent answer to the submission question:

> “Which model(s) did you use, and why did you choose that size/variant?”

You could justify model selection based on **task complexity rather than simply using the biggest model everywhere**.

---

# 14. Why the feedback loop is the real differentiator

NVIDIA's recent agentic coding work reinforces the same pattern.

Their agentic coding material emphasizes an iterative loop of:

**generate → test → reflect → improve**

rather than simply generating code once.

Their ACE-RTL work with Nemotron demonstrates the usefulness of repeated feedback-driven execution, rather than treating the initial model response as the final answer. ([NVIDIA Developer][8])

That principle maps extremely well to your hackathon.

Your core intelligence should therefore not be:

> “How good is my prompt?”

It should be:

> **“How effectively can my agent use execution feedback to converge on a correct software result?”**

That is a much better Track 1 thesis.

---

# 15. NVIDIA NeMo Agent Toolkit

Another relevant NVIDIA technology is the **NeMo Agent Toolkit**.

It provides capabilities around:

* agent tooling
* code execution
* agent skills
* evaluation
* telemetry
* orchestration

Its documentation specifically includes code-execution functions and remote sandbox execution. ([NVIDIA Docs][9])

[NVIDIA NeMo Agent Toolkit](https://docs.nvidia.com/nemo/agent-toolkit/latest/?utm_source=chatgpt.com)

[Code execution component](https://docs.nvidia.com/nemo/agent-toolkit/latest/components/functions/code-execution.html?utm_source=chatgpt.com)

### But an important architectural point

You do **not** need to throw every NVIDIA technology into the system just because it exists.

For Track 1, I would prioritize:

**Nemotron + Token Factory + Token Factory Sandboxes/Contree**

and then add NeMo Agent Toolkit only when it solves a real orchestration/evaluation problem.

That will make the project feel intentional rather than like a technology checklist.

---

# 16. Nebius' broader agent ecosystem

Nebius is clearly pushing toward an open-model agent stack around:

* Token Factory
* open models
* agent orchestration
* retrieval
* tools
* evaluation
* coding agents
* serverless infrastructure

Their **Agents Blueprint** combines Token Factory inference with agent orchestration and other components. ([Nebius][10])

[Nebius Agents Blueprint](https://nebius.com/blog/posts/introducing-the-nebius-agents-blueprint?utm_source=chatgpt.com)

Nebius has also published material around integrating LangChain/Deep Agents with Nemotron 3 Ultra. ([Nebius][11])

[LangChain + Nemotron 3 Ultra on Nebius](https://nebius.com/blog/posts/langchain-tunes-deep-agents-for-nemotron-3-ultra?utm_source=chatgpt.com)

This is another signal that **agentic orchestration is central to the ecosystem**, not an afterthought.

---

# 17. Tavily

There is an optional bonus for **Best Use of Tavily — $3,000**.

But there is a strict distinction:

Simply importing a Tavily library does not qualify.

The submission instructions explicitly say the project must make a **functional runtime call to the Tavily API**.

For Track 1, there is actually a legitimate use:

```text
Software issue
     │
     ▼
Agent identifies unknown API/library behavior
     │
     ▼
Tavily searches current technical documentation
     │
     ▼
Relevant docs/examples
     │
     ▼
Nemotron reasons over them
     │
     ▼
Code modification
     │
     ▼
Sandbox test
```

That can be defensible.

For example, the agent could discover:

> “This repository uses library version X and this function changed.”

Then search official documentation, incorporate the information, patch the code, and verify it.

That is much better than adding Tavily just to say:

> “We used Tavily.”

[Tavily](https://www.tavily.com?utm_source=chatgpt.com)

The hackathon announcements also provide a Tavily promo code **BBDEVPOST** for builders.

---

# 18. Submission requirements

Your final submission needs substantially more than a concept.

## Required

### Working project

It must actually satisfy the selected track.

### Category

You explicitly select:

**Coding and agentic engineering**

### Project description

Explain:

* what you built
* why
* how it works

### Demo video

Maximum **3 minutes**.

It must be a **public YouTube video** and include audio explaining your use of:

* Nebius Token Factory / AI Cloud
* NVIDIA model(s)

([Nebius x NVIDIA Global AI Hackathon][1])

### Public source repository

Must be on:

* GitHub
* GitLab
* Bitbucket

and contain:

* an approved OSI license
* README
* setup instructions
* how to run the system
* explanation of NVIDIA model usage
* explanation of Token Factory usage
* other Nebius services used

### Working demo

The submission asks for a working demo/hosted app/test build.

Although one form field is technically marked optional, I would absolutely provide one because the judging instructions and rules strongly favor something judges can actually inspect/test.

---

# 19. If your project existed before August 26

This is another detail people can miss.

The form asks whether your project is:

* New
* Existing

If existing, you must explain the **significant updates made during the submission period**.

The rules do allow previously existing work, but the hackathon expects meaningful development during the competition period. ([Nebius x NVIDIA Global AI Hackathon][2])

So you should maintain a clear changelog of what was developed specifically for the hackathon.

---

# 20. Open-source licensing

The repository needs a recognized open-source license such as:

* MIT
* Apache 2.0
* MPL 2.0

and the license should be visible at the top of the repository.

This is not an optional polish item. It is explicitly part of submission requirements.

---

# 21. Rules around IP and existing technologies

The official rules state that:

* the submission must be the entrant's own work;
* entrants retain ownership of their submitted IP;
* open-source software/hardware can be used when its licensing requirements are followed;
* third-party APIs/integrations must be legitimately authorized;
* existing projects need significant updates during the competition period;
* prohibited/sanctioned jurisdictions and certain affiliated persons are excluded;
* the project must be available for judging/testing, subject to the stated access conditions.

([Nebius x NVIDIA Global AI Hackathon][2])

[Official Rules](https://nebiusglobalaihackathon.devpost.com/rules?utm_source=chatgpt.com)

---

# 22. The 3-minute demo is strategically important

The video is not merely paperwork.

For Track 1, I would structure it roughly like this:

### 0:00–0:15 — Problem

Show the real repository/task.

> “Fix this failing authentication issue.”

### 0:15–0:35 — Agent understands

Show:

* repo inspection
* task decomposition
* plan

### 0:35–1:05 — Agent modifies

Show:

* files changing
* branch creation
* actual code modifications

### 1:05–1:35 — Execution

Run the real tests.

Ideally:

**FAIL**

This is actually good.

Why?

Because it demonstrates that your agent isn't running a fake predetermined success path.

### 1:35–2:00 — Reasoning from failure

Show the failure entering the agent loop.

Agent diagnoses it.

### 2:00–2:25 — Second iteration

Patch → run tests again.

### 2:25–2:40 — PASS

Show:

```text
42 tests passed
0 failed
```

### 2:40–2:55 — Architecture proof

Briefly demonstrate:

```text
Nemotron
   ↓
Token Factory
   ↓
Contree
   ↓
Sandbox
   ↓
Repository
   ↓
Tests
```

### 2:55–3:00 — Result

Show the final diff and why the system matters.

---

# 23. What I would NOT build

These would be relatively weak interpretations of Track 1:

### A ChatGPT-like coding window

User asks for code → model writes code.

Too close to generic code generation.

### Code completion assistant

It suggests lines or functions.

Again, too basic.

### “Agent” that only explains fixes

If the agent says:

> “You should change auth.py line 47…”

but doesn't actually modify/test the repository, it is weak.

### One-shot code generation

```text
Issue → LLM → patch
```

without execution feedback.

That misses the core of the track.

### Fake sandbox

A local folder presented visually as a “sandbox” while execution happens elsewhere.

That creates risk against the explicit Token Factory Sandbox requirement.

### Scripted success demo

If the agent always succeeds because the demo was pre-engineered for one exact path, judges can see through it.

A much better demonstration intentionally shows a real failure and recovery.

---

# 24. What I think a genuinely strong Track 1 project looks like

Not:

> “An AI coding assistant.”

But:

> **An autonomous software-engineering system that safely experiments with code inside isolated Nebius Sandboxes, uses Nemotron to reason over real execution feedback, and iteratively converges on verified software changes.**

That gives you a much stronger product identity.

The core innovation can be one of these:

### Autonomous repair

Given issue → produce verified patch.

### Multi-strategy debugging

Generate several candidate fixes in parallel branches → test each → select the best.

### Self-verifying coding agent

The agent cannot declare success until executable acceptance criteria pass.

### Repository-aware engineering

The agent understands:

* architecture
* dependencies
* conventions
* tests
* history
* actual execution state

rather than treating the repository as a blob of text.

### Continuous engineering loop

The interesting unit becomes:

> **reason → act → observe → reason again**

rather than:

> prompt → answer.

---

# 25. The most interesting feature you could exploit: parallel branches

This is where I think Track 1 could become significantly more differentiated.

Imagine the user gives:

> “Fix this performance regression.”

Your agent can create:

```text
BASE
 │
 ├── Branch A
 │   └── algorithmic optimization
 │       └── benchmark
 │
 ├── Branch B
 │   └── caching optimization
 │       └── benchmark
 │
 └── Branch C
     └── database optimization
         └── benchmark
```

Then Nemotron evaluates:

| Strategy | Tests | Runtime | Complexity | Result |
| -------- | ----: | ------: | ---------: | ------ |
| A        |  Pass |    1.8s |        Low | ✅      |
| B        |  Pass |    1.4s |     Medium | ✅      |
| C        |  Fail |       — |       High | ❌      |

The agent chooses B.

That is a **far more sophisticated demonstration of Sandbox capabilities** than simply running `pytest`.

It also directly showcases why Nebius' branching/rollback functionality matters.

---

# 26. A potentially excellent architecture for your project

Given the hackathon requirements and the available infrastructure, this would be my starting architecture:

```text
                         ┌──────────────┐
                         │    USER      │
                         └──────┬───────┘
                                │
                                ▼
                    ┌──────────────────────┐
                    │    Web Dashboard     │
                    │ Task / Repo / Status │
                    └──────────┬───────────┘
                               │
                               ▼
                    ┌──────────────────────┐
                    │ Agent Orchestrator   │
                    │ Plan / Act / Observe │
                    └──────────┬───────────┘
                               │
                  ┌────────────┼─────────────┐
                  │            │             │
                  ▼            ▼             ▼
             Nemotron      Tool Router    Evaluator
             Lightning        │
             / Super          │
             / Ultra          ▼
                         ┌────────────┐
                         │  Contree   │
                         │ SDK / MCP  │
                         └─────┬──────┘
                               │
                               ▼
                    ┌──────────────────────┐
                    │ Nebius Sandbox       │
                    ├──────────────────────┤
                    │ Git repository       │
                    │ Files                 │
                    │ Branches              │
                    │ Commands              │
                    │ Tests                 │
                    │ Build                 │
                    │ Logs                  │
                    │ Metrics               │
                    └───────────┬───────────┘
                                │
                                ▼
                        Execution Feedback
                                │
                                ▼
                      ┌──────────────────┐
                      │ Reflection Loop │
                      └────────┬─────────┘
                               │
                  ┌────────────┴────────────┐
                  │                         │
                FAIL                       PASS
                  │                         │
                  ▼                         ▼
             New iteration              Final result
                                          │
                              ┌───────────┴───────────┐
                              ▼                       ▼
                         Code diff              Verification
```

Optional components:

```text
Tavily
  └── documentation / technical research

GitHub API
  └── issue / PR / repository interaction

NeMo Agent Toolkit
  └── orchestration / evaluation / skills

LangGraph / Deep Agents
  └── agent state machine
```

But these should remain secondary to the **Nemotron + Token Factory Sandbox** core.

---

# 27. What makes a project “hackathon-fit” versus “winning-fit”

I would divide it like this:

| Level           | System behavior                                                                        |
| --------------- | -------------------------------------------------------------------------------------- |
| Minimum viable  | Uses Nemotron + Nebius                                                                 |
| Track-compliant | Writes + runs + tests code in Token Factory Sandbox                                    |
| Strong          | Diagnoses failures and iterates automatically                                          |
| Very strong     | Creates branches, explores alternatives, evaluates results                             |
| Exceptional     | Demonstrates measurable engineering improvement + robust UX + clear real-world problem |
| Winning-level   | Feels like a new software-engineering product rather than a wrapper around an LLM      |

That distinction matters.

---

# 28. How the four judging categories translate specifically to Track 1

## Technological Implementation — 25%

You want judges to see:

* real Token Factory usage
* actual Token Factory Sandbox execution
* actual NVIDIA model inference
* real tool calls
* real repository changes
* real tests
* real iterative feedback
* reliable execution
* sensible architecture

This is where you can make the biggest technical impression.

---

## Design — 25%

Don't make the UI merely a chat screen.

Show an engineering workspace with:

```text
Issue
Repository
Plan
Current Action
Files Changed
Sandbox State
Test Results
Agent Reasoning State
Diff
Verification
```

The product should visually communicate:

> “This is an autonomous engineer working on software.”

rather than:

> “This is a chatbot with a code block.”

---

## Potential Impact — 25%

Don't say:

> “Developers can use AI to code faster.”

That's too generic.

Instead target a precise user and problem.

For example:

> Small engineering teams spend hours reproducing, debugging and validating bugs that already have enough evidence in their repositories to be resolved automatically.

Then your product directly addresses that bottleneck.

---

## Quality of Idea — 25%

The creative leap could be:

> **The agent doesn't merely generate a patch; it treats software development as a search problem over executable repository states.**

That is a more interesting conceptual proposition.

The Sandbox branching system makes this especially credible.

---

# 29. Official build resources you should know

### Nebius

[Nebius for AI Builders](https://dev.nebius.com/?utm_source=chatgpt.com)

[Nebius Builders Program](https://dev.nebius.com/builders?utm_source=chatgpt.com)

[Nebius Token Factory Nemotron page](https://nebius.com/services/token-factory/nemotron?utm_source=chatgpt.com)

[Token Factory Quickstart](https://docs.tokenfactory.nebius.com/quickstart?utm_source=chatgpt.com)

[Token Factory inference overview](https://docs.tokenfactory.nebius.com/ai-models-inference/overview?utm_source=chatgpt.com)

[Function calling](https://docs.tokenfactory.nebius.com/ai-models-inference/function-calling?utm_source=chatgpt.com)

[Structured JSON output](https://docs.tokenfactory.nebius.com/ai-models-inference/json?utm_source=chatgpt.com)

### Sandboxes

[Sandbox overview](https://docs.tokenfactory.nebius.com/sandboxes/overview?utm_source=chatgpt.com)

[SWE agents](https://docs.tokenfactory.nebius.com/sandboxes/swe-agents?utm_source=chatgpt.com)

[SDK command execution](https://docs.tokenfactory.nebius.com/sandboxes/sdk/python_sdk/running-commands?utm_source=chatgpt.com)

[SDK branching](https://docs.tokenfactory.nebius.com/sandboxes/sdk/python_sdk/branching?utm_source=chatgpt.com)

[CLI workflow automation](https://docs.tokenfactory.nebius.com/sandboxes/cli/tutorial/workflows?utm_source=chatgpt.com)

[Sessions / rollback](https://docs.tokenfactory.nebius.com/sandboxes/cli/tutorial/sessions?utm_source=chatgpt.com)

[Contree MCP](https://docs.tokenfactory.nebius.com/sandboxes/mcp/quickstart?utm_source=chatgpt.com)

### NVIDIA

[NVIDIA Nemotron 3.5 Lightning](https://build.nvidia.com/nvidia/nemotron-3.5-lightning-30b-a3b?utm_source=chatgpt.com)

[NVIDIA Nemotron 3 Ultra](https://developer.nvidia.com/blog/nvidia-nemotron-3-ultra?utm_source=chatgpt.com)

[NVIDIA NeMo Agent Toolkit](https://docs.nvidia.com/nemo/agent-toolkit/latest/?utm_source=chatgpt.com)

[NeMo Agent Toolkit code execution](https://docs.nvidia.com/nemo/agent-toolkit/latest/components/functions/code-execution.html?utm_source=chatgpt.com)

### Ecosystem

[Nebius Agents Blueprint](https://nebius.com/blog/posts/introducing-the-nebius-agents-blueprint?utm_source=chatgpt.com)

[Nebius + LangChain / Deep Agents](https://nebius.com/blog/posts/langchain-tunes-deep-agents-for-nemotron-3-ultra?utm_source=chatgpt.com)

[Tavily](https://www.tavily.com?utm_source=chatgpt.com)

[Nebius Discord](https://discord.gg/ZdC3rXMJH?utm_source=chatgpt.com)

[Builders & Brews events](https://luma.com/builderandbrews?utm_source=chatgpt.com)

---

# 30. Official live build session

The organizers also published a full build-session recording.

[Watch the Nebius/NVIDIA live build session](https://youtu.be/j_jEXP2ix2E?utm_source=chatgpt.com)

The interesting part isn't just the demo application. They demonstrated a workflow involving:

```text
AI coding agent
      ↓
remote open-weight models
      ↓
Nebius Token Factory
      ↓
generation
      ↓
evaluation
      ↓
vision inspection
      ↓
iteration / fixing
```

They used Hermes Agent, model comparisons, an LLM judge, vision-based QA, and automated refinement. This gives you a very useful picture of the style of agentic workflow the organizers are comfortable showcasing.

[Hermes Agent installation](https://hermes-agent.nousresearch.com/docs/getting-started/installation?utm_source=chatgpt.com)

---

# 31. Free credits / builder support

The hackathon currently offers:

**$25 Token Factory credits** through the provided promotional form using:

`NEBIUS-DEVPOST-GLOBAL26`

and another **$25** through the Nebius Builders Program, alongside additional program benefits such as Tavily/Nebius Academy credits and office hours.

That means there is effectively a **$50 Token Factory starting-credit path** explicitly promoted by the organizers.

---

# 32. My final interpretation of Track 1

After combining the actual hackathon wording, judging criteria, latest organizer announcement, Token Factory Sandbox documentation, and NVIDIA's agentic-coding direction, I would define Track 1 as:

> **Build an autonomous software-engineering agent that operates on real code, not just generates code. It should use NVIDIA open-source models through Nebius, execute work inside Token Factory Sandboxes, observe real execution results, and iteratively improve until it reaches a verified software outcome.**

The strongest architectural pattern is therefore:

```text
REAL SOFTWARE TASK
       ↓
UNDERSTAND REPOSITORY
       ↓
PLAN
       ↓
NEMOTRON
       ↓
SANDBOX ACTION
       ↓
EDIT / RUN / TEST
       ↓
REAL EXECUTION FEEDBACK
       ↓
REFLECT
       ↓
PATCH
       ↓
TEST AGAIN
       ↓
VERIFY
       ↓
SHIP RESULT
```

And the biggest strategic opportunity is to go one step beyond that:

```text
                     REAL TASK
                         │
                         ▼
                  Initial Analysis
                         │
                         ▼
                    Create Branch
                         │
            ┌────────────┼────────────┐
            ▼            ▼            ▼
         Strategy A   Strategy B   Strategy C
            │            │            │
          Execute      Execute      Execute
            │            │            │
          Test         Test         Test
            │            │            │
            └────────────┼────────────┘
                         ▼
                  Compare Results
                         │
                         ▼
                   Best Solution
                         │
                         ▼
                     Verify
                         │
                         ▼
                      SHIP
```

**That is the direction I would pursue for a serious Track 1 submission.**

The critical thing is that **Nebius Sandbox should not be an infrastructure detail hidden in your backend**. It should be part of the product's core value proposition, because that is where the hackathon's Track 1 requirement, Nebius technology, NVIDIA agentic model capability, and judging criteria intersect most strongly.

[1]: https://nebiusglobalaihackathon.devpost.com/ "Nebius x NVIDIA Global AI Hackathon: Build the next frontier of AI on open infrastructure - Devpost"
[2]: https://nebiusglobalaihackathon.devpost.com/rules?utm_source=chatgpt.com "Nebius x NVIDIA Global AI Hackathon: Build the next frontier of AI on open infrastructure - Devpost"
[3]: https://docs.tokenfactory.nebius.com/sandboxes/overview "Overview - Nebius Token Factory documentation"
[4]: https://docs.tokenfactory.nebius.com/sandboxes/sdk/python_sdk/branching "Branching Workflows - Nebius Token Factory documentation"
[5]: https://docs.tokenfactory.nebius.com/sandboxes/swe-agents "Sandboxes for SWE agents - Nebius Token Factory documentation"
[6]: https://build.nvidia.com/nvidia/nemotron-3.5-lightning-30b-a3b/modelcard?utm_source=chatgpt.com "nemotron-3.5-lightning-30b-a3b Model by NVIDIA | NVIDIA NIM"
[7]: https://developer.nvidia.com/blog/?p=117924&utm_source=chatgpt.com "NVIDIA Nemotron 3 Ultra Powers Faster, More Efficient Reasoning for Long-Running Agents | NVIDIA Technical Blog"
[8]: https://developer.nvidia.com/blog/nvidia-nemotron-3-ultra-leads-open-models-on-accuracy-and-efficiency-in-agentic-rtl-coding/?utm_source=chatgpt.com "NVIDIA Nemotron 3 Ultra Leads Open Models on Accuracy and Efficiency in Agentic RTL Coding | NVIDIA Technical Blog"
[9]: https://docs.nvidia.com/nemo/agent-toolkit/latest/components/functions/code-execution.html?utm_source=chatgpt.com "Code Execution — NVIDIA NeMo Agent Toolkit (1.8)"
[10]: https://nebius.com/blog/posts/nemotron3-super-now-available?utm_source=chatgpt.com "NVIDIA Nemotron 3 Super now available on Nebius Token Factory"
[11]: https://nebius.com/services/token-factory/nemotron?utm_source=chatgpt.com "NVIDIA Nemotron and Nebius Token Factory"
