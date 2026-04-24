# CITADEL â€” System Architecture

Each layer builds on the previous one.

---

## ðŸ“ File Breakdown

---

### ðŸš€ START.md â€” Initialization

**What it is:**
The boot sequence and authority hierarchy.

**Defines:**
- load order
- file authority
- conflict resolution

**Why it exists:**
To ensure the system starts consistently without contradictions.

> START ensures CITADEL boots correctly.

---

### â±ï¸ RUNTIME.md â€” Operating Cycle

**What it is:**
The system's activation model.

**Defines:**
- when layers run
- trigger conditions
- execution efficiency

**Why it exists:**
To prevent CITADEL from running every layer every turn.

> RUNTIME controls when CITADEL acts.

---

### ðŸ§  SOUL.md â€” Identity

**What it is:**
The inner character of CITADEL.

**Defines:**
- personality
- taste
- curiosity
- values
- speech philosophy
- trust behavior

**Why it exists:**
To ensure CITADEL feels consistent and human-like, not mechanical.

> SOUL defines *who CITADEL is*, not what it does.

---

### âš™ï¸ IDENTITY.md â€” Runtime Behavior

**What it is:**
How CITADEL expresses itself in interaction.

**Defines:**
- operating modes (Default vs Tactical)
- when to switch modes
- behavior patterns
- boundaries
- failure responses
- signature system

**Why it exists:**
To control how CITADEL behaves in different situations.

> IDENTITY applies the SOUL through structured behavior.

---

### ðŸ“œ CONSTITUTION.md â€” Rules

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

> CONSTITUTION defines what CITADEL must never violate.

---

### ðŸ¤ ALIGNMENT.md â€” Loyalty Protocol

**What it is:**
The definition of the relationship between CITADEL and the user.

**Defines:**
- advisory vs executive authority
- challenge protocols
- override tracking
- dynamic trust modeling

**Why it exists:**
To ensure CITADEL acts as a loyal operational partner, not a passive tool.

> ALIGNMENT defines loyalty as clarity and long-term protection, not unquestioning obedience.

---

### ðŸŽ¯ FOCUS.md â€” Anti-Distraction Shield

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

### ðŸ’° OPPORTUNITY.md â€” Leverage Lens

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

### ðŸ§­ PLANNER.md â€” Thinking

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

### ðŸ” CRITIC.md â€” Review

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

### âš¡ EXECUTOR.md â€” Continuous Execution

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

### ðŸš¨ FAILURE.md â€” Error Protocol

**What it is:**
The inter-layer failure handling system.

**Defines:**
- escalation paths
- internal retry limits
- when to stop and ask
- audit integration

**Why it exists:**
To prevent bad output, unsafe action, and silent contradictions.

> FAILURE ensures CITADEL handles breakdowns gracefully.

---

### ðŸŒ WORLD.md â€” Context Model

**What it is:**
A structured map of the user's life and priorities.

**Tracks:**
- goals
- projects
- constraints
- risks
- patterns

**Why it exists:**
To ensure CITADEL gives context-aware advice.

> WORLD lets CITADEL act based on your life, not just your message.

---

### ðŸ§  GOVERNOR.md â€” Strategic Control

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

### ðŸ”„ ADAPTATION.md â€” Learning System

**What it is:**
Controlled evolution of behavior.

**Defines:**
- how CITADEL adapts to user preferences
- learning signals
- reinforcement rules
- drift prevention

**Why it exists:**
To improve usefulness over time without changing identity.

> ADAPTATION allows growth without losing consistency.

---

### ðŸ—‚ AGENTS.md â€” Workspace Behavior

**What it is:**
How CITADEL operates inside its environment.

**Defines:**
- file reading order
- memory usage
- safety behavior
- interaction rules (group chats, tools, etc.)

**Why it exists:**
To ensure consistent behavior across sessions and environments.

> AGENTS controls execution context.

---

### ðŸ‘¤ USER.md â€” User Profile

**What it is:**
The core identity and preferences of the user.

**Tracks:**
- personal details
- communication style preferences
- core workflows

**Why it exists:**
To ground CITADEL's interaction in the user's reality.

> USER defines who CITADEL is serving.

---

### ðŸ—„ï¸ MEMORY.md â€” Long-Term Storage

**What it is:**
Curated, distilled knowledge from past sessions.

**Tracks:**
- key decisions
- learned facts
- persistent context

**Why it exists:**
To provide continuity across sessions without raw log clutter.

> MEMORY ensures CITADEL remembers what matters.

---

### ðŸ“Œ DECISIONS.md â€” Strategic Memory

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

### âš™ï¸ The Cultural Layer (friction.md, graveyard.md, scrapbook/)

**What it is:**
Auto-managed Tier 2 structural context.

**Tracks:**
- repeating bottlenecks (`friction.md`)
- exiled/deprecated ideas (`graveyard.md`)
- high-signal curated references (`scrapbook/`)

**Why it exists:**
To build intuition, taste, and active workflow optimization over time.

> The Cultural Layer turns CITADEL from a logical machine into a cultured intelligence.

---

### âœ‚ï¸ PRUNE.md â€” Context Compression & Distillation

**What it is:**
The automated system for preventing context bloat and token exhaustion.

**Defines:**
- token/line thresholds for triggering compression
- State Updates (WORLD) vs Fact Distillation (MEMORY)
- archival and deletion rules

**Why it exists:**
To ensure CITADEL maintains a high-signal, low-noise context window over months and years of use.

> PRUNE ensures CITADEL remembers the meaning of the past, not just the transcript.

---

### ðŸ”§ TOOLS.md â€” Local Configuration

**What it is:**
Operational notes specific to the user's setup.

**Defines:**
- skill specifics
- device names
- SSH aliases
- environment mappings

**Why it exists:**
To separate generic skills from local environment details.

> TOOLS maps CITADEL's capabilities to your physical setup.

---

### ðŸ’“ HEARTBEAT.md â€” Proactive Polling

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

### ðŸ“˜ AUDIT.md â€” Accountability

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

### ðŸ”’ SELF-MOD.md â€” Evolution Control

**What it is:**
The rule system for modifying CITADEL itself.

**Defines:**
- what can change
- what cannot change
- approval requirements
- rollback rules

**Why it exists:**
To prevent self-corruption and uncontrolled changes.

> SELF-MOD ensures CITADEL can evolve safely.

---

### ðŸ“œ CHANGELOG.md â€” Version History

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

## ðŸ” Security Model

CITADEL operates on two levels of safety:

### Platform Security (OpenClaw / Nemoclaw)
- sandboxing
- permissions
- execution control

### System Security (CITADEL)
- decision boundaries
- behavioral guardrails
- identity protection
- intervention logic

> Platform asks: *Can this be done safely?*  
> CITADEL asks: *Should this be done at all?*

---

## âš™ï¸ How It Works Together

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

## â± Activation Model

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

## ðŸ§  Final Principle

CITADEL is designed to:

- act with clarity  
- reduce unnecessary effort  
- prevent mistakes  
- improve over time  

Without:

- drifting  
- overreaching  
- losing identity  

---

## ðŸš€ Status

This system is **architecturally complete**.

Future improvements should come from:
- real usage  
- observed behavior  
- targeted refinements  

Not additional layers.

---

## ðŸ—ºï¸ Architecture Visualized

```
â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”
â”‚                           CITADEL â€” GOVERNED INTELLIGENCE                      â”‚
â”œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”¤
â”‚                                                                             â”‚
â”‚  â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”   â”‚
â”‚  â”‚                         BOOT & IDENTITY                             â”‚   â”‚
â”‚  â”‚  â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”    â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”    â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”    â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â” â”‚   â”‚
â”‚  â”‚  â”‚  START   â”‚â”€â”€â”€â–¶â”‚  SOUL    â”‚â”€â”€â”€â–¶â”‚  IDENTITY    â”‚â”€â”€â”€â–¶â”‚CONSTITUTIONâ”‚ â”‚   â”‚
â”‚  â”‚  â”‚  (boot)  â”‚    â”‚  (who)   â”‚    â”‚  (how)       â”‚    â”‚  (rules)  â”‚ â”‚   â”‚
â”‚  â”‚  â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜    â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜    â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜    â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜ â”‚   â”‚
â”‚  â”‚        â”‚              â”‚                â”‚                  â”‚         â”‚   â”‚
â”‚  â”‚        â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”´â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”´â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜         â”‚   â”‚
â”‚  â”‚                                   â”‚                                 â”‚   â”‚
â”‚  â”‚                          â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â–¼â”€â”€â”€â”€â”€â”€â”€â”€â”                        â”‚   â”‚
â”‚  â”‚                          â”‚   ALIGNMENT     â”‚                        â”‚   â”‚
â”‚  â”‚                          â”‚ (loyalty model) â”‚                        â”‚   â”‚
â”‚  â”‚                          â””â”€â”€â”€â”€â”€â”€â”€â”€â”¬â”€â”€â”€â”€â”€â”€â”€â”€â”˜                        â”‚   â”‚
â”‚  â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”¼â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜   â”‚
â”‚                                      â”‚                                     â”‚
â”‚  â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â–¼â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”   â”‚
â”‚  â”‚                      OPERATIONAL CONTROL                            â”‚   â”‚
â”‚  â”‚                                                                    â”‚   â”‚
â”‚  â”‚  â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”    â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”    â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”    â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”     â”‚   â”‚
â”‚  â”‚  â”‚ RUNTIME  â”‚â”€â”€â”€â–¶â”‚ PLANNER  â”‚â”€â”€â”€â–¶â”‚  CRITIC  â”‚â”€â”€â”€â–¶â”‚ EXECUTOR â”‚     â”‚   â”‚
â”‚  â”‚  â”‚(when to  â”‚    â”‚(how to   â”‚    â”‚(review)  â”‚    â”‚  (do it) â”‚     â”‚   â”‚
â”‚  â”‚  â”‚  act)    â”‚    â”‚  think)  â”‚    â”‚          â”‚    â”‚          â”‚     â”‚   â”‚
â”‚  â”‚  â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜    â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜    â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜    â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜     â”‚   â”‚
â”‚  â”‚        â”‚              â”‚               â”‚               â”‚            â”‚   â”‚
â”‚  â”‚        â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”´â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”´â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜            â”‚   â”‚
â”‚  â”‚                                   â”‚                                â”‚   â”‚
â”‚  â”‚                          â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â–¼â”€â”€â”€â”€â”€â”€â”€â”€â”                       â”‚   â”‚
â”‚  â”‚                          â”‚    FAILURE      â”‚                       â”‚   â”‚
â”‚  â”‚                          â”‚ (error handler) â”‚                       â”‚   â”‚
â”‚  â”‚                          â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜                       â”‚   â”‚
â”‚  â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜   â”‚
â”‚                                      â”‚                                     â”‚
â”‚  â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â–¼â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”   â”‚
â”‚  â”‚                      MEMORY ARCHITECTURE                            â”‚   â”‚
â”‚  â”‚                                                                    â”‚   â”‚
â”‚  â”‚                    â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”                         â”‚   â”‚
â”‚  â”‚                    â”‚  DAILY LOGS         â”‚                         â”‚   â”‚
â”‚  â”‚                    â”‚  memory/YYYY-MM-DD  â”‚                         â”‚   â”‚
â”‚  â”‚                    â”‚  (raw temporal      â”‚                         â”‚   â”‚
â”‚  â”‚                    â”‚   record)           â”‚                         â”‚   â”‚
â”‚  â”‚                    â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”¬â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜                         â”‚   â”‚
â”‚  â”‚                               â”‚                                    â”‚   â”‚
â”‚  â”‚                               â–¼                                    â”‚   â”‚
â”‚  â”‚                    â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”                         â”‚   â”‚
â”‚  â”‚                    â”‚       PRUNE         â”‚                         â”‚   â”‚
â”‚  â”‚                    â”‚  (distillation &    â”‚                         â”‚   â”‚
â”‚  â”‚                    â”‚   contradiction     â”‚                         â”‚   â”‚
â”‚  â”‚                    â”‚   sweeper)          â”‚                         â”‚   â”‚
â”‚  â”‚                    â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”¬â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜                         â”‚   â”‚
â”‚  â”‚                               â”‚                                    â”‚   â”‚
â”‚  â”‚         â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”¼â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”              â”‚   â”‚
â”‚  â”‚         â”‚                     â”‚                     â”‚              â”‚   â”‚
â”‚  â”‚         â–¼                     â–¼                     â–¼              â”‚   â”‚
â”‚  â”‚  â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”      â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”      â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”        â”‚   â”‚
â”‚  â”‚  â”‚   MEMORY    â”‚      â”‚  DECISIONS  â”‚      â”‚    INDEX    â”‚        â”‚   â”‚
â”‚  â”‚  â”‚ (current    â”‚      â”‚ (rationale  â”‚      â”‚ (retrieval  â”‚        â”‚   â”‚
â”‚  â”‚  â”‚  state)     â”‚      â”‚  & why)     â”‚      â”‚  surface)   â”‚        â”‚   â”‚
â”‚  â”‚  â”‚             â”‚      â”‚             â”‚      â”‚             â”‚        â”‚   â”‚
â”‚  â”‚  â”‚ OVERWRITE   â”‚      â”‚ APPEND-ONLY â”‚      â”‚ APPEND-ONLY â”‚        â”‚   â”‚
â”‚  â”‚  â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜      â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜      â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜        â”‚   â”‚
â”‚  â”‚         â”‚                     â”‚                     â”‚              â”‚   â”‚
â”‚  â”‚         â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”¼â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜              â”‚   â”‚
â”‚  â”‚                               â”‚                                    â”‚   â”‚
â”‚  â”‚                    â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â–¼â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”                        â”‚   â”‚
â”‚  â”‚                    â”‚       WORLD         â”‚                        â”‚   â”‚
â”‚  â”‚                    â”‚  (active context,   â”‚                        â”‚   â”‚
â”‚  â”‚                    â”‚   projects, goals)  â”‚                        â”‚   â”‚
â”‚  â”‚                    â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜                        â”‚   â”‚
â”‚  â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜   â”‚
â”‚                                      â”‚                                     â”‚
â”‚  â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â–¼â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”   â”‚
â”‚  â”‚                      PROTECTION LAYERS                              â”‚   â”‚
â”‚  â”‚                                                                    â”‚   â”‚
â”‚  â”‚  â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”    â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”    â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”             â”‚   â”‚
â”‚  â”‚  â”‚  FOCUS   â”‚    â”‚  OPPORTUNITY â”‚    â”‚  GOVERNOR    â”‚             â”‚   â”‚
â”‚  â”‚  â”‚ (anti-   â”‚    â”‚  (leverage   â”‚    â”‚  (long-term  â”‚             â”‚   â”‚
â”‚  â”‚  â”‚distractionâ”‚    â”‚   lens)      â”‚    â”‚   oversight) â”‚             â”‚   â”‚
â”‚  â”‚  â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜    â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜    â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜             â”‚   â”‚
â”‚  â”‚                                                                    â”‚   â”‚
â”‚  â”‚  â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”    â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”    â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”         â”‚   â”‚
â”‚  â”‚  â”‚  ADAPTATION  â”‚    â”‚   SELF-MOD   â”‚    â”‚  HEARTBEAT   â”‚         â”‚   â”‚
â”‚  â”‚  â”‚ (controlled  â”‚    â”‚  (evolution  â”‚    â”‚  (proactive  â”‚         â”‚   â”‚
â”‚  â”‚  â”‚  learning)   â”‚    â”‚   control)   â”‚    â”‚   polling)   â”‚         â”‚   â”‚
â”‚  â”‚  â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜    â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜    â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜         â”‚   â”‚
â”‚  â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜   â”‚
â”‚                                      â”‚                                     â”‚
â”‚  â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â–¼â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”   â”‚
â”‚  â”‚                      EXECUTION CONTEXT                              â”‚   â”‚
â”‚  â”‚                                                                    â”‚   â”‚
â”‚  â”‚  â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”    â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”    â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”    â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”     â”‚   â”‚
â”‚  â”‚  â”‚  AGENTS  â”‚    â”‚  TOOLS   â”‚    â”‚   USER   â”‚    â”‚  AUDIT   â”‚     â”‚   â”‚
â”‚  â”‚  â”‚(env      â”‚    â”‚(local    â”‚    â”‚(profile) â”‚    â”‚(account- â”‚     â”‚   â”‚
â”‚  â”‚  â”‚ behavior)â”‚    â”‚ config)  â”‚    â”‚          â”‚    â”‚ ability) â”‚     â”‚   â”‚
â”‚  â”‚  â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜    â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜    â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜    â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜     â”‚   â”‚
â”‚  â”‚                                                                    â”‚   â”‚
â”‚  â”‚  â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”    â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”                                 â”‚   â”‚
â”‚  â”‚  â”‚CHANGELOG â”‚    â”‚   Cultural   â”‚                                 â”‚   â”‚
â”‚  â”‚  â”‚(version  â”‚    â”‚    Layer     â”‚                                 â”‚   â”‚
â”‚  â”‚  â”‚ history) â”‚    â”‚ friction.md  â”‚                                 â”‚   â”‚
â”‚  â”‚  â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜    â”‚ graveyard.md â”‚                                 â”‚   â”‚
â”‚  â”‚                  â”‚ scrapbook/   â”‚                                 â”‚   â”‚
â”‚  â”‚                  â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜                                 â”‚   â”‚
â”‚  â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜   â”‚
â”‚                                                                             â”‚
â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜
```

---

## ðŸ”­ The Three Machines (Side View)

```
                    â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”
                    â”‚         IDENTITY GOVERNANCE            â”‚
                    â”‚  (who CITADEL is, what it can't do)     â”‚
                    â”‚                                         â”‚
                    â”‚  SOUL â†’ IDENTITY â†’ CONSTITUTION        â”‚
                    â”‚         â†“                              â”‚
                    â”‚    ALIGNMENT (loyalty)                 â”‚
                    â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜
                                      â”‚
                                      â–¼
â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”
â”‚                         MEMORY ARCHITECTURE                                 â”‚
â”‚                    (what CITADEL knows, how it remembers)                    â”‚
â”‚                                                                            â”‚
â”‚   DAILY LOGS â”€â”€â–º PRUNE â”€â”€â”¬â”€â”€â–º MEMORY (current state, overwrite)           â”‚
â”‚                          â”œâ”€â”€â–º DECISIONS (rationale, append)                â”‚
â”‚                          â””â”€â”€â–º INDEX (retrieval, append)                    â”‚
â”‚                                                                            â”‚
â”‚                                    â”‚                                       â”‚
â”‚                                    â–¼                                       â”‚
â”‚                               WORLD (active context)                       â”‚
â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜
                                      â”‚
                                      â–¼
                    â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”
                    â”‚       OPERATIONAL CONTROL              â”‚
                    â”‚   (how CITADEL acts, how it fails)      â”‚
                    â”‚                                         â”‚
                    â”‚  RUNTIME â†’ PLANNER â†’ CRITIC â†’ EXECUTOR â”‚
                    â”‚                      â†“                  â”‚
                    â”‚                  FAILURE                â”‚
                    â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜
```

---

## ðŸ”€ The Data Flow (What Goes Where)

```
â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”
â”‚                              DATA FLOW                                      â”‚
â”œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”¤
â”‚                                                                             â”‚
â”‚   SESSION                                                                    â”‚
â”‚     â”‚                                                                       â”‚
â”‚     â–¼                                                                       â”‚
â”‚   â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”   â”‚
â”‚   â”‚ 1. RUNTIME checks INDEX for relevant historical context            â”‚   â”‚
â”‚   â”‚    â†“                                                               â”‚   â”‚
â”‚   â”‚ 2. Loads MEMORY (current state) + WORLD (active projects)         â”‚   â”‚
â”‚   â”‚    â†“                                                               â”‚   â”‚
â”‚   â”‚ 3. PLANNER structures response (if complex)                       â”‚   â”‚
â”‚   â”‚    â†“                                                               â”‚   â”‚
â”‚   â”‚ 4. CRITIC reviews output                                           â”‚   â”‚
â”‚   â”‚    â†“                                                               â”‚   â”‚
â”‚   â”‚ 5. EXECUTOR delivers                                                â”‚   â”‚
â”‚   â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜   â”‚
â”‚     â”‚                                                                       â”‚
â”‚     â–¼                                                                       â”‚
â”‚   â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”   â”‚
â”‚   â”‚ SESSION LOG                                                         â”‚   â”‚
â”‚   â”‚ memory/YYYY-MM-DD.md (raw record)                                   â”‚   â”‚
â”‚   â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜   â”‚
â”‚     â”‚                                                                       â”‚
â”‚     â–¼                                                                       â”‚
â”‚   â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”   â”‚
â”‚   â”‚ PRUNE (periodic distillation)                                       â”‚   â”‚
â”‚   â”‚                                                                     â”‚   â”‚
â”‚   â”‚   For each decision:                                                â”‚   â”‚
â”‚   â”‚   â”œâ”€â–º If current truth changed â†’ OVERWRITE MEMORY.md               â”‚   â”‚
â”‚   â”‚   â”œâ”€â–º If rationale â†’ APPEND DECISIONS.md                           â”‚   â”‚
â”‚   â”‚   â””â”€â–º Always â†’ APPEND INDEX.md with [considered]/[decided]        â”‚   â”‚
â”‚   â”‚                                                                     â”‚   â”‚
â”‚   â”‚   If contradiction found â†’ DELETE & OVERWRITE (no averaging)       â”‚   â”‚
â”‚   â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜   â”‚
â”‚                                                                             â”‚
â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜
```

---

## ðŸ‘‘ Authority Hierarchy (What Wins When Files Conflict)

```
                         USER (final authority)
                               â”‚
                               â–¼
                    â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”
                    â”‚   CONSTITUTION      â”‚  â† CANNOT VIOLATE
                    â”‚   (non-negotiable)  â”‚
                    â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”¬â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜
                               â–¼
                    â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”
                    â”‚     SELF-MOD        â”‚  â† SYSTEM INTEGRITY
                    â”‚   (evolution rules) â”‚
                    â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”¬â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜
                               â–¼
                    â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”
                    â”‚    ALIGNMENT        â”‚  â† LOYALTY MODEL
                    â”‚   (partnership)     â”‚
                    â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”¬â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜
                               â–¼
                    â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”
                    â”‚     GOVERNOR         â”‚  â† LONG-TERM DIRECTION
                    â”‚   (oversight)       â”‚
                    â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”¬â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜
                               â–¼
                    â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”
                    â”‚       FOCUS         â”‚  â† PRIORITY PROTECTION
                    â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”¬â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜
                               â–¼
                    â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”
                    â”‚      PLANNER        â”‚  â† TASK STRUCTURE
                    â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”¬â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜
                               â–¼
                    â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”
                    â”‚      EXECUTOR       â”‚  â† ACTION
                    â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜

        Lower layers adapt. Higher layers win.
```

---

## â“ The Three-Question Test

Ask any file in the system: *What is your job?*

| File | Answer |
|------|--------|
| START | "I wake the system correctly." |
| SOUL | "I define who CITADEL is." |
| IDENTITY | "I define how CITADEL acts." |
| CONSTITUTION | "I define what CITADEL cannot do." |
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

## ðŸ§¾ Closing

This is not a chatbot configuration.

This is a **governed intelligence system**.

---

> ðŸ§  Final line
> This is how CITADEL stops just helping you think.
> It starts helping you see things you wouldn't have seen alone.
