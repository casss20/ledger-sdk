"""
Experimental agent runtime modules.

These modules implement an aspirational agent self-governance runtime
that is not yet wired to the kernel. They contain real logic but are
isolated while the core governance engine stabilizes.

Modules:
  - core: Constitution, Governor, Runtime, Executor (agent-level)
  - governance: Critic, Prune, AfterAction, Risk, KillSwitch, Audit, RateLimit, Capability, Durable, Alignment
  - ops: Planner, Failure, Adaptation, Opportunity
  - system: Focus
"""
