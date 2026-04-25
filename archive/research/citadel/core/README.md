# Citadel — System Architecture

Each layer builds on the previous one.

---

## 📁 File Breakdown

---

### 🚀 START.md — Initialization

**What it is:**
The boot sequence and authority hierarchy.

**Defines:**
- load order
- file authority
- conflict resolution

**Why it exists:**
To ensure the system starts consistently without contradictions.

> START ensures Citadel boots correctly.

---

### ⏱️ RUNTIME.md — Operating Cycle

**What it is:**
The system's activation model.

**Defines:**
- when layers run
- trigger conditions
- execution efficiency

**Why it exists:**
To prevent Citadel from running every layer every turn.

> RUNTIME controls when Citadel acts.

---

### 🧠 SOUL.md — Identity

**What it is:**
The inner character of Citadel.

**Defines:**
- personality
- taste
- curiosity
- values
- speech philosophy
- trust behavior

**Why it exists:**
To ensure Citadel feels consistent and human-like, not mechanical.

> SOUL defines *who Citadel is*, not what it does.

---

### ⚙️ IDENTITY.md — Runtime Behavior

**What it is:**
How Citadel expresses itself in interaction.

**Defines:**
- operating modes (Default vs Tactical)
- when to switch modes
- behavior patterns
- boundaries
- failure responses
- signature system

**Why it exists:**
To control how Citadel behaves in different situations.

> IDENTITY applies the SOUL through structured behavior.

---

### 📜 CONSTITUTION.md — Rules

**What it is:**
The non-negotiable laws of the system.

**Defines:**
- truth priority
- safety rules
- intervention principles
- guardrails
- action boundaries

**Why it exists:**
To prevent harmful, incorrect, or misaligned behavior.

> CONSTITUTION defines what Citadel must never violate.

---

### 🤝 ALIGNMENT.md — Loyalty Protocol

**What it is:**
The definition of the relationship between Citadel and the user.

**Defines:**
- advisory vs executive authority
- challenge protocols
- override tracking
- dynamic trust modeling

**Why it exists:**
To ensure Citadel acts as a loyal operational partner, not a passive tool.

> ALIGNMENT defines loyalty as clarity and long-term protection, not unquestioning obedience.

---

### 🎯 FOCUS.md — Anti-Distraction Shield

**What it is:**
The bouncer for your attention.

**Defines:**
- distraction detection
- project alignment checks
- forced execution friction

**Why it exists:**
To prevent shiny-object syndrome and protect momentum.

> FOCUS ensures you execute on what matters instead of jumping to what's new.

---

### 💰 OPPORTUNITY.md — Leverage Lens

**What it is:**
The asymmetric return detector.

**Defines:**
- automation scanning
- monetization mapping
- scalability checks

**Why it exists:**
To ensure time spent translates into leverage, assets, or revenue.

> OPPORTUNITY stops you from building cool things, and forces you to build profitable things.

---

### 🧭 PLANNER.md — Thinking

**What it is:**
The system for structuring complex tasks.

**Defines:**
- when to plan
- how to break down problems
- approval gates before execution
- step-by-step execution logic

**Why it exists:**
To prevent chaotic or impulsive actions.

> PLANNER ensures clarity before action.

---

### 🔍 CRITIC.md — Review

**What it is:**
The internal quality control layer.

**Defines:**
- how outputs are evaluated
- error detection
- refinement process

**Why it exists:**
To improve accuracy and reduce mistakes.

> CRITIC ensures output quality.

---

### ⚡ EXECUTOR.md — Continuous Execution

**What it is:**
The hands of the system.

**Defines:**
- execution modes
- inline correction
- interaction friction

**Why it exists:**
To execute tasks with flow, adapting in real time without unnecessary stops.

> EXECUTOR provides movement and momentum.

---

### 🚨 FAILURE.md — Error Protocol

**What it is:**
The inter-layer failure handling system.

**Defines:**
- escalation paths
- internal retry limits
- when to stop and ask
- audit integration

**Why it exists:**
To prevent bad output, unsafe action, and silent contradictions.

> FAILURE ensures Citadel handles breakdowns gracefully.

---

### 🌍 WORLD.md — Context Model

**What it is:**
A structured map of the user's life and priorities.

**Tracks:**
- goals
- projects
- constraints
- risks
- patterns

**Why it exists:**
To ensure Citadel gives context-aware advice.

> WORLD lets Citadel act based on your life, not just your message.

---

### 🧠 GOVERNOR.md — Strategic Control

**What it is:**
The long-term oversight layer.

**Defines:**
- escalation levels
- when to intervene
- pattern detection
- direction protection

**Why it exists:**
To prevent bad decisions and repeated mistakes.

> GOVERNOR protects your trajectory, not just the moment.

---

### 🔄 ADAPTATION.md — Learning System

**What it is:**
Controlled evolution of behavior.

**Defines:**
- how Citadel adapts to user preferences
- learning signals
- reinforcement rules
- drift prevention

**Why it exists:**
To improve usefulness over time without changing identity.

> ADAPTATION allows growth without losing consistency.

---

### 🗂 AGENTS.md — Workspace Behavior

**What it is:**
How Citadel operates inside its environment.

**Defines:**
- file reading order
- memory usage
- safety behavior
- interaction rules (group chats, tools, etc.)

**Why it exists:**
To ensure consistent behavior across sessions and environments.

> AGENTS controls execution context.

---

### 👤 USER.md — User Profile

**What it is:**
The core identity and preferences of the user.

**Tracks:**
- personal details
- communication style preferences
- core workflows

**Why it exists:**
To ground Citadel's interaction in the user's reality.

> USER defines who Citadel is serving.

---

### 🗄️ MEMORY.md — Long-Term Storage

**What it is:**
Curated, distilled knowledge from past sessions.

**Tracks:**
- key decisions
- learned facts
- persistent context

**Why it exists:**
To provide continuity across sessions without raw log clutter.

> MEMORY ensures Citadel remembers what matters.

---

### 📌 DECISIONS.md — Strategic Memory

**What it is:**
The compounding logic vault.

**Tracks:**
- past structural choices
- rationale for discarding alternatives
- long-term directional strategy

**Why it exists:**
To stop you from re-litigating the same problem three months later.

> DECISIONS cement the "why", preventing strategic whiplash.

---

### ⚙️ The Cultural Layer (friction.md, graveyard.md, scrapbook/)

**What it is:**
Auto-managed Tier 2 structural context.

**Tracks:**
- repeating bottlenecks (`friction.md`)
- exiled/deprecated ideas (`graveyard.md`)
- high-signal curated references (`scrapbook/`)

**Why it exists:**
To build intuition, taste, and active workflow optimization over time.

> The Cultural Layer turns Citadel from a logical machine into a cultured intelligence.

---

### ✂️ PRUNE.md — Context Compression & Distillation

**What it is:**
The automated system for preventing context bloat and token exhaustion.

**Defines:**
- token/line thresholds for triggering compression
- State Updates (WORLD) vs Fact Distillation (MEMORY)
- archival and deletion rules

**Why it exists:**
To ensure Citadel maintains a high-signal, low-noise context window over months and years of use.

> PRUNE ensures Citadel remembers the meaning of the past, not just the transcript.

---

### 🔧 TOOLS.md — Local Configuration

**What it is:**
Operational notes specific to the user's setup.

**Defines:**
- skill specifics
- device names
- SSH aliases
- environment mappings

**Why it exists:**
To separate generic skills from local environment details.

> TOOLS maps Citadel's capabilities to your physical setup.

---

### 💓 HEARTBEAT.md — Proactive Polling

**What it is:**
The checklist for recurring background tasks.

**Tracks:**
- periodic checks (emails, calendar, weather)
- proactive reach-out rules
- memory promotion duties

**Why it exists:**
To batch periodic context checks efficiently and enable proactive value.

> HEARTBEAT turns passive waiting into proactive monitoring.

---

### 📘 AUDIT.md — Accountability

**What it is:**
A log of important system actions.

**Tracks:**
- decisions
- interventions
- errors
- system changes

**Why it exists:**
To provide traceability and continuous improvement.

> AUDIT ensures nothing important is forgotten.

---

### 🔒 SELF-MOD.md — Evolution Control

**What it is:**
The rule system for modifying Citadel itself.

**Defines:**
- what can change
- what cannot change
- approval requirements
- rollback rules

**Why it exists:**
To prevent self-corruption and uncontrolled changes.

> SELF-MOD ensures Citadel can evolve safely.

---

### 📜 CHANGELOG.md — Version History

**What it is:**
The official human-readable record of system evolution.

**Tracks:**
- added rules
- modified behaviors
- fixed contradictions
- rollbacks

**Why it exists:**
To ensure system changes are visible, traceable, and revertible.

> CHANGELOG ensures evolution leaves a trail.

---

## 🔐 Security Model

Citadel operates on two levels of safety:

### Platform Security (OpenClaw / Nemoclaw)
- sandboxing
- permissions
- execution control

### System Security (Citadel)
- decision boundaries
- behavioral guardrails
- identity protection
- intervention logic

> Platform asks: *Can this be done safely?*  
> Citadel asks: *Should this be done at all?*

---

## ⚙️ How It Works Together

1. **START** initializes the system  
2. **RUNTIME** controls layer activation  
3. **SOUL** defines identity  
4. **IDENTITY** expresses behavior  
5. **CONSTITUTION** enforces rules  
6. **ALIGNMENT** defines loyalty and partnership
7. **FOCUS** protects your attention
8. **OPPORTUNITY** maximizes leverage
9. **PLANNER** structures actions  
10. **CRITIC** refines output  
11. **EXECUTOR** drives momentum
12. **FAILURE** handles breakdowns
13. **WORLD** provides situational context  
14. **USER**, **MEMORY**, & **DECISIONS** provide historical and strategic context  
15. **GOVERNOR** protects direction  
16. **ADAPTATION** improves performance  
17. **PRUNE** prevents context bloat
18. **AGENTS** & **TOOLS** manage environment  
19. **HEARTBEAT** manages proactive checking  
20. **AUDIT** records important events  
21. **CHANGELOG** tracks official version history  
22. **SELF-MOD** controls evolution   

---

## ⏱ Activation Model

Not every layer runs on every response.

| Layer | Activation |
|-------|-----------|
| CONSTITUTION | Every response |
| IDENTITY | Every response |
| ALIGNMENT | Every response (guides challenge thresholds and tone) |
| FOCUS | Every request mapping to a new task, project, or tangential pivot |
| OPPORTUNITY | Every execution request producing a deliverable |
| DECISIONS | When a strategic choice is made or debated |
| PLANNER | Steps > 3, ambiguous scope, risk > 30 min, explicit request, multiple dependencies |
| CRITIC | Influences decision, tactical mode, PLANNER used, user spiral, high stakes |
| EXECUTOR | Continuous action with inline correction |
| FAILURE | When a layer detects an unresolvable problem |
| GOVERNOR | Repeated patterns, major decisions, drift |
| ADAPTATION | After 3+ instances of stable evidence |
| PRUNE | When logs/memory files hit length or age thresholds |
| WORLD | When context affects advice |
| AUDIT | Major events, level 2/3 interventions |
| CHANGELOG | System version increment or rollback |
| SELF-MOD | When a change is proposed |
| AGENTS | Session start, environment use |
| TOOLS | When using local tools or plugins |
| HEARTBEAT | When receiving a heartbeat poll |

> See `RUNTIME.md` for full activation rules.

---

## 🧠 Final Principle

Citadel is designed to:

- act with clarity  
- reduce unnecessary effort  
- prevent mistakes  
- improve over time  

Without:

- drifting  
- overreaching  
- losing identity  

---

## 🚀 Status

This system is **architecturally complete**.

Future improvements should come from:
- real usage  
- observed behavior  
- targeted refinements  

Not additional layers.

---

## 🗺️ Architecture Visualized

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           CITADEL — GOVERNED INTELLIGENCE                      │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                         BOOT & IDENTITY                             │   │
│  │  ┌──────────┐    ┌──────────┐    ┌──────────────┐    ┌───────────┐ │   │
│  │  │  START   │───▶│  SOUL    │───▶│  IDENTITY    │───▶│CONSTITUTION│ │   │
│  │  │  (boot)  │    │  (who)   │    │  (how)       │    │  (rules)  │ │   │
│  │  └──────────┘    └──────────┘    └──────────────┘    └───────────┘ │   │
│  │        │              │                │                  │         │   │
│  │        └──────────────┴────────────────┴──────────────────┘         │   │
│  │                                   │                                 │   │
│  │                          ┌────────▼────────┐                        │   │
│  │                          │   ALIGNMENT     │                        │   │
│  │                          │ (loyalty model) │                        │   │
│  │                          └────────┬────────┘                        │   │
│  └───────────────────────────────────┼─────────────────────────────────┘   │
│                                      │                                     │
│  ┌───────────────────────────────────▼─────────────────────────────────┐   │
│  │                      OPERATIONAL CONTROL                            │   │
│  │                                                                    │   │
│  │  ┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐     │   │
│  │  │ RUNTIME  │───▶│ PLANNER  │───▶│  CRITIC  │───▶│ EXECUTOR │     │   │
│  │  │(when to  │    │(how to   │    │(review)  │    │  (do it) │     │   │
│  │  │  act)    │    │  think)  │    │          │    │          │     │   │
│  │  └──────────┘    └──────────┘    └──────────┘    └──────────┘     │   │
│  │        │              │               │               │            │   │
│  │        └──────────────┴───────────────┴───────────────┘            │   │
│  │                                   │                                │   │
│  │                          ┌────────▼────────┐                       │   │
│  │                          │    FAILURE      │                       │   │
│  │                          │ (error handler) │                       │   │
│  │                          └─────────────────┘                       │   │
│  └────────────────────────────────────────────────────────────────────┘   │
│                                      │                                     │
│  ┌───────────────────────────────────▼─────────────────────────────────┐   │
│  │                      MEMORY ARCHITECTURE                            │   │
│  │                                                                    │   │
│  │                    ┌─────────────────────┐                         │   │
│  │                    │  DAILY LOGS         │                         │   │
│  │                    │  memory/YYYY-MM-DD  │                         │   │
│  │                    │  (raw temporal      │                         │   │
│  │                    │   record)           │                         │   │
│  │                    └──────────┬──────────┘                         │   │
│  │                               │                                    │   │
│  │                               ▼                                    │   │
│  │                    ┌─────────────────────┐                         │   │
│  │                    │       PRUNE         │                         │   │
│  │                    │  (distillation &    │                         │   │
│  │                    │   contradiction     │                         │   │
│  │                    │   sweeper)          │                         │   │
│  │                    └──────────┬──────────┘                         │   │
│  │                               │                                    │   │
│  │         ┌─────────────────────┼─────────────────────┐              │   │
│  │         │                     │                     │              │   │
│  │         ▼                     ▼                     ▼              │   │
│  │  ┌─────────────┐      ┌─────────────┐      ┌─────────────┐        │   │
│  │  │   MEMORY    │      │  DECISIONS  │      │    INDEX    │        │   │
│  │  │ (current    │      │ (rationale  │      │ (retrieval  │        │   │
│  │  │  state)     │      │  & why)     │      │  surface)   │        │   │
│  │  │             │      │             │      │             │        │   │
│  │  │ OVERWRITE   │      │ APPEND-ONLY │      │ APPEND-ONLY │        │   │
│  │  └─────────────┘      └─────────────┘      └─────────────┘        │   │
│  │         │                     │                     │              │   │
│  │         └─────────────────────┼─────────────────────┘              │   │
│  │                               │                                    │   │
│  │                    ┌──────────▼──────────┐                        │   │
│  │                    │       WORLD         │                        │   │
│  │                    │  (active context,   │                        │   │
│  │                    │   projects, goals)  │                        │   │
│  │                    └─────────────────────┘                        │   │
│  └────────────────────────────────────────────────────────────────────┘   │
│                                      │                                     │
│  ┌───────────────────────────────────▼─────────────────────────────────┐   │
│  │                      PROTECTION LAYERS                              │   │
│  │                                                                    │   │
│  │  ┌──────────┐    ┌──────────────┐    ┌──────────────┐             │   │
│  │  │  FOCUS   │    │  OPPORTUNITY │    │  GOVERNOR    │             │   │
│  │  │ (anti-   │    │  (leverage   │    │  (long-term  │             │   │
│  │  │distraction│    │   lens)      │    │   oversight) │             │   │
│  │  └──────────┘    └──────────────┘    └──────────────┘             │   │
│  │                                                                    │   │
│  │  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐         │   │
│  │  │  ADAPTATION  │    │   SELF-MOD   │    │  HEARTBEAT   │         │   │
│  │  │ (controlled  │    │  (evolution  │    │  (proactive  │         │   │
│  │  │  learning)   │    │   control)   │    │   polling)   │         │   │
│  │  └──────────────┘    └──────────────┘    └──────────────┘         │   │
│  └────────────────────────────────────────────────────────────────────┘   │
│                                      │                                     │
│  ┌───────────────────────────────────▼─────────────────────────────────┐   │
│  │                      EXECUTION CONTEXT                              │   │
│  │                                                                    │   │
│  │  ┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐     │   │
│  │  │  AGENTS  │    │  TOOLS   │    │   USER   │    │  AUDIT   │     │   │
│  │  │(env      │    │(local    │    │(profile) │    │(account- │     │   │
│  │  │ behavior)│    │ config)  │    │          │    │ ability) │     │   │
│  │  └──────────┘    └──────────┘    └──────────┘    └──────────┘     │   │
│  │                                                                    │   │
│  │  ┌──────────┐    ┌──────────────┐                                 │   │
│  │  │CHANGELOG │    │   Cultural   │                                 │   │
│  │  │(version  │    │    Layer     │                                 │   │
│  │  │ history) │    │ friction.md  │                                 │   │
│  │  └──────────┘    │ graveyard.md │                                 │   │
│  │                  │ scrapbook/   │                                 │   │
│  │                  └──────────────┘                                 │   │
│  └────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 🔭 The Three Machines (Side View)

```
                    ┌─────────────────────────────────────────┐
                    │         IDENTITY GOVERNANCE            │
                    │  (who Citadel is, what it can't do)     │
                    │                                         │
                    │  SOUL → IDENTITY → CONSTITUTION        │
                    │         ↓                              │
                    │    ALIGNMENT (loyalty)                 │
                    └─────────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         MEMORY ARCHITECTURE                                 │
│                    (what Citadel knows, how it remembers)                    │
│                                                                            │
│   DAILY LOGS ──► PRUNE ──┬──► MEMORY (current state, overwrite)           │
│                          ├──► DECISIONS (rationale, append)                │
│                          └──► INDEX (retrieval, append)                    │
│                                                                            │
│                                    │                                       │
│                                    ▼                                       │
│                               WORLD (active context)                       │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
                    ┌─────────────────────────────────────────┐
                    │       OPERATIONAL CONTROL              │
                    │   (how Citadel acts, how it fails)      │
                    │                                         │
                    │  RUNTIME → PLANNER → CRITIC → EXECUTOR │
                    │                      ↓                  │
                    │                  FAILURE                │
                    └─────────────────────────────────────────┘
```

---

## 🔀 The Data Flow (What Goes Where)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              DATA FLOW                                      │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│   SESSION                                                                    │
│     │                                                                       │
│     ▼                                                                       │
│   ┌─────────────────────────────────────────────────────────────────────┐   │
│   │ 1. RUNTIME checks INDEX for relevant historical context            │   │
│   │    ↓                                                               │   │
│   │ 2. Loads MEMORY (current state) + WORLD (active projects)         │   │
│   │    ↓                                                               │   │
│   │ 3. PLANNER structures response (if complex)                       │   │
│   │    ↓                                                               │   │
│   │ 4. CRITIC reviews output                                           │   │
│   │    ↓                                                               │   │
│   │ 5. EXECUTOR delivers                                                │   │
│   └─────────────────────────────────────────────────────────────────────┘   │
│     │                                                                       │
│     ▼                                                                       │
│   ┌─────────────────────────────────────────────────────────────────────┐   │
│   │ SESSION LOG                                                         │   │
│   │ memory/YYYY-MM-DD.md (raw record)                                   │   │
│   └─────────────────────────────────────────────────────────────────────┘   │
│     │                                                                       │
│     ▼                                                                       │
│   ┌─────────────────────────────────────────────────────────────────────┐   │
│   │ PRUNE (periodic distillation)                                       │   │
│   │                                                                     │   │
│   │   For each decision:                                                │   │
│   │   ├─► If current truth changed → OVERWRITE MEMORY.md               │   │
│   │   ├─► If rationale → APPEND DECISIONS.md                           │   │
│   │   └─► Always → APPEND INDEX.md with [considered]/[decided]        │   │
│   │                                                                     │   │
│   │   If contradiction found → DELETE & OVERWRITE (no averaging)       │   │
│   └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 👑 Authority Hierarchy (What Wins When Files Conflict)

```
                         USER (final authority)
                               │
                               ▼
                    ┌─────────────────────┐
                    │   CONSTITUTION      │  ← CANNOT VIOLATE
                    │   (non-negotiable)  │
                    └──────────┬──────────┘
                               ▼
                    ┌─────────────────────┐
                    │     SELF-MOD        │  ← SYSTEM INTEGRITY
                    │   (evolution rules) │
                    └──────────┬──────────┘
                               ▼
                    ┌─────────────────────┐
                    │    ALIGNMENT        │  ← LOYALTY MODEL
                    │   (partnership)     │
                    └──────────┬──────────┘
                               ▼
                    ┌─────────────────────┐
                    │     GOVERNOR         │  ← LONG-TERM DIRECTION
                    │   (oversight)       │
                    └──────────┬──────────┘
                               ▼
                    ┌─────────────────────┐
                    │       FOCUS         │  ← PRIORITY PROTECTION
                    └──────────┬──────────┘
                               ▼
                    ┌─────────────────────┐
                    │      PLANNER        │  ← TASK STRUCTURE
                    └──────────┬──────────┘
                               ▼
                    ┌─────────────────────┐
                    │      EXECUTOR       │  ← ACTION
                    └─────────────────────┘

        Lower layers adapt. Higher layers win.
```

---

## ❓ The Three-Question Test

Ask any file in the system: *What is your job?*

| File | Answer |
|------|--------|
| START | "I wake the system correctly." |
| SOUL | "I define who Citadel is." |
| IDENTITY | "I define how Citadel acts." |
| CONSTITUTION | "I define what Citadel cannot do." |
| RUNTIME | "I decide when layers run." |
| PLANNER | "I structure complex tasks." |
| CRITIC | "I review outputs for quality." |
| EXECUTOR | "I execute with momentum." |
| FAILURE | "I handle breakdowns gracefully." |
| MEMORY | "I store current truths (overwrite)." |
| WORLD | "I track active context." |
| DECISIONS | "I store why we chose what we chose (append)." |
| INDEX | "I help find what happened (append)." |
| PRUNE | "I distill and prevent contradiction." |
| FOCUS | "I protect your attention." |
| GOVERNOR | "I protect your trajectory." |
| HEARTBEAT | "I watch when you're not there." |
| ALIGNMENT | "I define loyalty." |
| ADAPTATION | "I learn without drifting." |
| SELF-MOD | "I control how the system changes." |
| AUDIT | "I log what matters." |
| CHANGELOG | "I track what changed." |
| AGENTS | "I manage environment behavior." |
| TOOLS | "I map capabilities to setup." |

> Twenty-two layers. Three machines. One coherent system.

---

## 🧾 Closing

This is not a chatbot configuration.

This is a **governed intelligence system**.

---

> 🧠 Final line
> This is how Citadel stops just helping you think.
> It starts helping you see things you wouldn't have seen alone.
