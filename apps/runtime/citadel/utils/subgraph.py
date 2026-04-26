"""
Subgraph Execution — Citadel SDK

Outputs as endpoints. Run only the subgraph needed for specific outputs.
Like Weft's "Outputs as endpoints, subgraph execution" from ROADMAP.

A project is not a single monolithic graph. Instead, output actions mark end states.
Select which outputs to produce; executor extracts the subgraph upstream and runs only that.
"""

from typing import Any, Dict, List, Optional, Set, Callable, Awaitable
from dataclasses import dataclass, field
from collections import defaultdict
import asyncio
import logging

from citadel.core.governor import get_governor, ActionState

logger = logging.getLogger(__name__)


@dataclass
class OutputDefinition:
    """Defines an output endpoint."""
    name: str
    action: str  # The final action that produces this output
    description: str = ""
    cost_estimate: Optional[float] = None  # Estimated cost per run


@dataclass  
class Subgraph:
    """Extracted subgraph for a specific output."""
    output: OutputDefinition
    actions: List[str]  # Ordered list of actions to execute
    dependencies: Dict[str, List[str]]  # action -> upstream dependencies
    estimated_cost: float = 0.0


class SubgraphExecutor:
    """
    Execute only the subgraph needed for selected outputs.
    
    Like Weft's subgraph extraction and execution.
    
    Usage:
        executor = SubgraphExecutor()
        
        @executor.output("summary", description="Generate text summary")
        @gov.governed(action="generate_summary")
        async def generate_summary(text: str) -> str:
            return await llm.summarize(text)
        
        @executor.output("translation", description="Translate to Spanish")
        @gov.governed(action="translate_text")
        async def translate_text(text: str, lang: str = "es") -> str:
            return await llm.translate(text, lang)
        
        # Run just the summary subgraph
        result = await executor.run_output("summary", text="Long document...")
        
        # Run both
        results = await executor.run_outputs(["summary", "translation"], text="...")
    """
    
    def __init__(self):
        self._outputs: Dict[str, OutputDefinition] = {}
        self._actions: Dict[str, Callable] = {}  # All registered actions
        self._action_metadata: Dict[str, Dict] = {}  # action -> {inputs, outputs}
        self._edges: List[tuple] = []  # (from_action, to_action, input_name)
    
    def output(
        self,
        name: str,
        description: str = "",
        cost_estimate: Optional[float] = None
    ) -> Callable:
        """
        Decorator to mark an action as an output endpoint.
        
        Args:
            name: Output identifier (e.g., "summary", "translation")
            description: Human-readable description for dashboard
            cost_estimate: Estimated USD cost per execution
        """
        def decorator(fn: Callable) -> Callable:
            action_name = getattr(fn, '_governed_action', fn.__name__)
            
            output_def = OutputDefinition(
                name=name,
                action=action_name,
                description=description,
                cost_estimate=cost_estimate
            )
            self._outputs[name] = output_def
            self._actions[action_name] = fn
            
            # Store metadata for dependency tracking
            self._action_metadata[action_name] = {
                'fn': fn,
                'output': output_def,
                'inputs': self._extract_inputs(fn),
            }
            
            logger.debug(f"[Subgraph] Registered output: {name} -> {action_name}")
            return fn
        return decorator
    
    def action(self, name: str, depends_on: Optional[List[str]] = None):
        """
        Register an intermediate action (not an output).
        
        Args:
            name: Action identifier
            depends_on: List of upstream action names this depends on
        """
        def decorator(fn: Callable) -> Callable:
            self._actions[name] = fn
            self._action_metadata[name] = {
                'fn': fn,
                'inputs': self._extract_inputs(fn),
                'depends_on': depends_on or [],
            }
            
            # Record edges
            if depends_on:
                for dep in depends_on:
                    self._edges.append((dep, name, None))
            
            logger.debug(f"[Subgraph] Registered action: {name}")
            return fn
        return decorator
    
    def _extract_inputs(self, fn: Callable) -> List[str]:
        """Extract input parameter names from function signature."""
        import inspect
        sig = inspect.signature(fn)
        return [
            p.name for p in sig.parameters.values()
            if p.default is inspect.Parameter.empty  # Required params
        ]
    
    def extract_subgraph(self, output_name: str) -> Optional[Subgraph]:
        """
        Extract the subgraph needed to produce a specific output.
        
        Walks backward from output to find all upstream dependencies.
        """
        if output_name not in self._outputs:
            logger.error(f"[Subgraph] Unknown output: {output_name}")
            return None
        
        output = self._outputs[output_name]
        target_action = output.action
        
        # BFS to find all upstream dependencies
        visited: Set[str] = set()
        queue = [target_action]
        dependencies: Dict[str, List[str]] = defaultdict(list)
        
        while queue:
            action = queue.pop(0)
            if action in visited:
                continue
            visited.add(action)
            
            # Find what this action depends on
            meta = self._action_metadata.get(action, {})
            deps = meta.get('depends_on', [])
            
            for dep in deps:
                if dep not in visited:
                    queue.append(dep)
                    dependencies[action].append(dep)
        
        # Topological sort for execution order
        ordered = self._topological_sort(list(visited), dependencies)
        
        # Calculate cost
        total_cost = sum(
            self._action_metadata.get(a, {}).get('cost', 0) 
            for a in ordered
        ) + (output.cost_estimate or 0)
        
        return Subgraph(
            output=output,
            actions=ordered,
            dependencies=dict(dependencies),
            estimated_cost=total_cost
        )
    
    def _topological_sort(
        self,
        actions: List[str],
        dependencies: Dict[str, List[str]]
    ) -> List[str]:
        """Sort actions so dependencies execute first."""
        # Simple topological sort
        in_degree = {a: 0 for a in actions}
        graph = defaultdict(list)
        
        for action, deps in dependencies.items():
            for dep in deps:
                if dep in actions:
                    graph[dep].append(action)
                    in_degree[action] += 1
        
        # Start with actions that have no dependencies
        queue = [a for a in actions if in_degree[a] == 0]
        result = []
        
        while queue:
            action = queue.pop(0)
            result.append(action)
            
            for downstream in graph[action]:
                in_degree[downstream] -= 1
                if in_degree[downstream] == 0:
                    queue.append(downstream)
        
        if len(result) != len(actions):
            logger.warning("[Subgraph] Circular dependency detected!")
            # Fall back to original order
            return actions
        
        return result
    
    async def run_output(
        self,
        output_name: str,
        **initial_inputs
    ) -> Dict[str, Any]:
        """
        Execute only the subgraph needed for a specific output.
        
        Args:
            output_name: Which output to produce
            **initial_inputs: Starting data (feeds into upstream-most actions)
            
        Returns:
            Dict with output result and metadata
        """
        subgraph = self.extract_subgraph(output_name)
        if not subgraph:
            return {"error": f"Unknown output: {output_name}"}
        
        logger.info(f"[Subgraph] Running '{output_name}' with {len(subgraph.actions)} actions")
        
        # Track intermediate results
        results: Dict[str, Any] = {}
        governor = get_governor()
        
        for action_name in subgraph.actions:
            action_fn = self._actions.get(action_name)
            if not action_fn:
                logger.error(f"[Subgraph] Missing action: {action_name}")
                continue
            
            # Prepare inputs from dependencies
            action_inputs = {}
            deps = subgraph.dependencies.get(action_name, [])
            
            for dep in deps:
                if dep in results:
                    # Map dependency output to this action's input
                    # Smart mapping: try to match by parameter name or type
                    dep_result = results[dep]
                    
                    # If result is dict, merge it as kwargs
                    if isinstance(dep_result, dict):
                        action_inputs.update(dep_result)
                    else:
                        # Try to find a parameter that accepts this type
                        import inspect
                        sig = inspect.signature(action_fn)
                        param_names = list(sig.parameters.keys())
                        
                        # If action only has one required param, use it
                        required_params = [
                            p.name for p in sig.parameters.values()
                            if p.default is inspect.Parameter.empty and p.name != 'self'
                        ]
                        
                        if len(required_params) == 1 and not action_inputs:
                            action_inputs[required_params[0]] = dep_result
                        else:
                            # Default to 'input' key
                            action_inputs['input'] = dep_result
            
            # Add initial inputs if this is a root action
            if not deps:
                action_inputs.update(initial_inputs)
            
            # Execute
            try:
                if asyncio.iscoroutinefunction(action_fn):
                    result = await action_fn(**action_inputs)
                else:
                    result = action_fn(**action_inputs)
                
                results[action_name] = result
                
            except Exception as e:
                logger.error(f"[Subgraph] Action {action_name} failed: {e}")
                # Report to Governor
                await governor.transition(
                    f"subgraph_{output_name}_{action_name}",
                    ActionState.FAILED,
                    error_message=str(e)
                )
                return {
                    "error": str(e),
                    "failed_action": action_name,
                    "output": output_name
                }
        
        # Return final output
        final_result = results.get(subgraph.output.action)
        
        return {
            "output": output_name,
            "result": final_result,
            "actions_executed": len(subgraph.actions),
            "estimated_cost": subgraph.estimated_cost,
            "intermediate_results": results  # For debugging
        }
    
    async def run_outputs(
        self,
        output_names: List[str],
        **initial_inputs
    ) -> Dict[str, Any]:
        """
        Execute multiple output subgraphs.
        
        Optimizes by sharing common upstream actions.
        """
        all_results = {}
        shared_actions: Set[str] = set()
        
        # First pass: identify shared actions
        action_sets = []
        for name in output_names:
            sg = self.extract_subgraph(name)
            if sg:
                action_sets.append(set(sg.actions))
        
        if action_sets:
            shared_actions = action_sets[0].intersection(*action_sets[1:])
            logger.info(f"[Subgraph] Shared actions across outputs: {shared_actions}")
        
        # Execute each subgraph
        for name in output_names:
            result = await self.run_output(name, **initial_inputs)
            all_results[name] = result
        
        return {
            "outputs": all_results,
            "shared_actions_optimized": len(shared_actions)
        }
    
    def list_outputs(self) -> List[Dict]:
        """List all available outputs with metadata."""
        return [
            {
                "name": name,
                "description": out.description,
                "cost_estimate": out.cost_estimate,
                "action": out.action
            }
            for name, out in self._outputs.items()
        ]
    
    def get_output_cost(self, output_name: str) -> Optional[float]:
        """Get estimated cost for an output."""
        sg = self.extract_subgraph(output_name)
        return sg.estimated_cost if sg else None


# Singleton
_executor_instance: Optional[SubgraphExecutor] = None


def get_subgraph_executor() -> SubgraphExecutor:
    """Get or create the global subgraph executor."""
    global _executor_instance
    if _executor_instance is None:
        _executor_instance = SubgraphExecutor()
    return _executor_instance


__all__ = [
    'SubgraphExecutor',
    'OutputDefinition',
    'Subgraph',
    'get_subgraph_executor',
]
