"""
Recursive Groups â€” Citadel SDK

Like Weft's recursive composability:
- Any set of nodes becomes a group
- Groups have typed inputs and outputs
- From outside, a group looks like a single node
- Groups contain groups, arbitrarily deep
- A 100-node system looks like 5 blocks at top level
"""

from typing import List, Dict, Optional, Any, Callable, Union
from dataclasses import dataclass, field
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class GroupStatus(Enum):
    """Status of a group like Weft's node status"""
    COLLAPSED = "collapsed"  # Looks like single node
    EXPANDED = "expanded"    # Children visible
    PARTIAL = "partial"      # Some children visible


@dataclass
class Port:
    """
    Typed input/output port like Weft's port system.
    """
    name: str
    type: str  # "str", "int", "dict", "list", "any"
    required: bool = True
    description: Optional[str] = None
    default: Any = None


@dataclass  
class ActionNode:
    """
    Single governable action node.
    Like Weft's leaf nodes.
    """
    id: str
    action: str
    resource: str
    flag: str
    risk: str
    
    # Ports
    inputs: Dict[str, Port] = field(default_factory=dict)
    outputs: Dict[str, Port] = field(default_factory=dict)
    
    # UI
    display_name: Optional[str] = None
    icon: Optional[str] = None
    color: Optional[str] = None
    description: Optional[str] = None
    
    # State
    status: str = "idle"  # idle, running, completed, failed, skipped
    result: Any = None
    
    def to_dict(self) -> dict:
        """Serialize for dashboard/API"""
        return {
            "id": self.id,
            "type": "action",
            "action": self.action,
            "resource": self.resource,
            "flag": self.flag,
            "risk": self.risk,
            "display_name": self.display_name or self.action,
            "icon": self.icon,
            "color": self.color,
            "status": self.status,
            "inputs": {k: {"type": v.type, "required": v.required} for k, v in self.inputs.items()},
            "outputs": {k: {"type": v.type} for k, v in self.outputs.items()},
        }


@dataclass
class ActionGroup:
    """
    Recursive group of actions.
    Like Weft's groups â€” can contain nodes and other groups.
    """
    id: str
    name: str
    
    # Group interface (visible from outside)
    inputs: Dict[str, Port] = field(default_factory=dict)
    outputs: Dict[str, Port] = field(default_factory=dict)
    
    # Children
    actions: List[ActionNode] = field(default_factory=list)
    subgroups: List['ActionGroup'] = field(default_factory=list)
    
    # UI
    display_name: Optional[str] = None
    icon: Optional[str] = None
    color: Optional[str] = None
    description: Optional[str] = None
    
    # State
    status: GroupStatus = GroupStatus.COLLAPSED
    collapsed: bool = True  # UI collapsed state
    
    def flatten(self) -> List[Union[ActionNode, 'ActionGroup']]:
        """
        Get all actions including subgroups (recursive).
        Like Weft's flatten for graph rendering.
        """
        result: List[Union[ActionNode, ActionGroup]] = []
        result.extend(self.actions)
        
        for subgroup in self.subgroups:
            result.append(subgroup)
            if not subgroup.collapsed:
                result.extend(subgroup.flatten())
        
        return result
    
    def count_leaves(self) -> int:
        """Count total leaf actions (recursively)"""
        count = len(self.actions)
        for subgroup in self.subgroups:
            count += subgroup.count_leaves()
        return count
    
    def find_action(self, action_id: str) -> Optional[ActionNode]:
        """Find an action by ID (recursive search)"""
        for action in self.actions:
            if action.id == action_id:
                return action
        
        for subgroup in self.subgroups:
            found = subgroup.find_action(action_id)
            if found:
                return found
        
        return None
    
    def find_group(self, group_id: str) -> Optional['ActionGroup']:
        """Find a subgroup by ID (recursive search)"""
        if self.id == group_id:
            return self
        
        for subgroup in self.subgroups:
            found = subgroup.find_group(group_id)
            if found:
                return found
        
        return None
    
    def toggle(self) -> 'ActionGroup':
        """Toggle collapsed state (like Weft's fold/unfold)"""
        self.collapsed = not self.collapsed
        self.status = GroupStatus.COLLAPSED if self.collapsed else GroupStatus.EXPANDED
        return self
    
    def expand_all(self) -> 'ActionGroup':
        """Expand this group and all subgroups"""
        self.collapsed = False
        self.status = GroupStatus.EXPANDED
        for subgroup in self.subgroups:
            subgroup.expand_all()
        return self
    
    def collapse_all(self) -> 'ActionGroup':
        """Collapse this group and all subgroups"""
        self.collapsed = True
        self.status = GroupStatus.COLLAPSED
        for subgroup in self.subgroups:
            subgroup.collapse_all()
        return self
    
    def to_node(self) -> dict:
        """
        Render as a single node (collapsed view).
        Like Weft's group-as-node feature.
        """
        leaf_count = self.count_leaves()
        
        return {
            "id": self.id,
            "type": "group",
            "name": self.name,
            "display_name": self.display_name or self.name,
            "icon": self.icon or "Folder",
            "color": self.color or "#64748b",
            "collapsed": self.collapsed,
            "child_count": leaf_count,
            "subgroup_count": len(self.subgroups),
            "action_count": len(self.actions),
            "inputs": {k: {"type": v.type, "required": v.required} for k, v in self.inputs.items()},
            "outputs": {k: {"type": v.type} for k, v in self.outputs.items()},
            "is_group": True,
        }
    
    def to_graph(self) -> List[dict]:
        """
        Convert to graph nodes for React Flow.
        Returns both group node and children if expanded.
        """
        nodes = [self.to_node()]
        
        if not self.collapsed:
            # Add direct actions
            for action in self.actions:
                node_data = action.to_dict()
                node_data["parent_id"] = self.id
                nodes.append(node_data)
            
            # Add subgroups (they handle their own children)
            for subgroup in self.subgroups:
                nodes.extend(subgroup.to_graph())
        
        return nodes
    
    def get_edges(self) -> List[dict]:
        """
        Generate edges between children.
        Simplified â€” real implementation would use port connections.
        """
        edges = []
        
        if not self.collapsed:
            # Connect actions sequentially within group
            prev = None
            for action in self.actions:
                if prev:
                    edges.append({
                        "id": f"{self.id}_{prev.id}_to_{action.id}",
                        "source": prev.id,
                        "target": action.id,
                        "parent": self.id,
                    })
                prev = action
            
            # Recurse into subgroups
            for subgroup in self.subgroups:
                edges.extend(subgroup.get_edges())
        
        return edges


class GroupRegistry:
    """
    Registry for managing groups.
    Like Weft's group registry.
    """
    
    def __init__(self):
        self._groups: Dict[str, ActionGroup] = {}
        self._root: Optional[ActionGroup] = None
    
    def register(self, group: ActionGroup) -> ActionGroup:
        """Register a group"""
        self._groups[group.id] = group
        logger.debug(f"[GroupRegistry] Registered group: {group.name} ({group.id})")
        return group
    
    def get(self, group_id: str) -> Optional[ActionGroup]:
        """Get group by ID"""
        return self._groups.get(group_id)
    
    def set_root(self, group: ActionGroup):
        """Set root group"""
        self._root = group
        self.register(group)
    
    def get_root(self) -> Optional[ActionGroup]:
        """Get root group"""
        return self._root
    
    def list_all(self) -> List[ActionGroup]:
        """List all registered groups"""
        return list(self._groups.values())
    
    def to_graph(self) -> dict:
        """
        Convert entire registry to graph format for dashboard.
        """
        if not self._root:
            return {"nodes": [], "edges": []}
        
        return {
            "nodes": self._root.to_graph(),
            "edges": self._root.get_edges(),
        }
    
    def find_by_action(self, action_id: str) -> Optional[ActionGroup]:
        """Find which group contains an action"""
        for group in self._groups.values():
            if group.find_action(action_id):
                return group
        return None


# Predefined groups (like Weft's built-in nodes)

def create_default_groups() -> GroupRegistry:
    """
    Create default group hierarchy.
    100 actions organized into 5 top-level groups.
    """
    registry = GroupRegistry()
    
    # Communication group with subgroups
    email_group = ActionGroup(
        id="group_email",
        name="Email",
        display_name="Email",
        icon="Mail",
        color="#ef4444",
        actions=[
            ActionNode(
                id="send_email",
                action="send_email",
                resource="outbound_email",
                flag="email_send",
                risk="HIGH",
                display_name="Send Email",
                icon="Mail",
                color="#ef4444",
            ),
            ActionNode(
                id="send_bulk_email",
                action="send_bulk_email",
                resource="outbound_email",
                flag="email_send",
                risk="HIGH",
                display_name="Bulk Email",
                icon="Mails",
                color="#dc2626",
            ),
        ],
        inputs={
            "recipient": Port("recipient", "str", True),
            "subject": Port("subject", "str", True),
            "body": Port("body", "str", True),
        },
        outputs={
            "message_id": Port("message_id", "str"),
            "status": Port("status", "str"),
        },
    )
    
    chat_group = ActionGroup(
        id="group_chat",
        name="Chat",
        display_name="Chat",
        icon="MessageSquare",
        color="#3b82f6",
        actions=[
            ActionNode(
                id="send_slack",
                action="send_slack",
                resource="slack",
                flag="slack_send",
                risk="MEDIUM",
                display_name="Slack",
                icon="Slack",
                color="#3b82f6",
            ),
            ActionNode(
                id="send_discord",
                action="send_discord",
                resource="discord",
                flag="discord_send",
                risk="MEDIUM",
                display_name="Discord",
                icon="Discord",
                color="#5865f2",
            ),
        ],
    )
    
    communication = ActionGroup(
        id="group_communication",
        name="Communication",
        display_name="Communication",
        icon="MessageCircle",
        color="#8b5cf6",
        subgroups=[email_group, chat_group],
        collapsed=True,  # Start collapsed
    )
    
    # Payment group
    payment = ActionGroup(
        id="group_payment",
        name="Payment",
        display_name="Payment",
        icon="CreditCard",
        color="#22c55e",
        actions=[
            ActionNode(
                id="stripe_charge",
                action="stripe_charge",
                resource="stripe",
                flag="stripe_charge",
                risk="HIGH",
                display_name="Stripe Charge",
                icon="CreditCard",
                color="#22c55e",
            ),
            ActionNode(
                id="stripe_refund",
                action="stripe_refund",
                resource="stripe",
                flag="stripe_charge",
                risk="HIGH",
                display_name="Stripe Refund",
                icon="RotateCcw",
                color="#16a34a",
            ),
        ],
        collapsed=True,
    )
    
    # Database group
    database = ActionGroup(
        id="group_database",
        name="Database",
        display_name="Database",
        icon="Database",
        color="#3b82f6",
        actions=[
            ActionNode(
                id="write_database",
                action="write_database",
                resource="production_db",
                flag="db_write",
                risk="MEDIUM",
                display_name="Write",
                icon="Database",
                color="#3b82f6",
            ),
            ActionNode(
                id="delete_rows",
                action="delete_rows",
                resource="production_db",
                flag="db_write",
                risk="HIGH",
                display_name="Delete",
                icon="Trash2",
                color="#ef4444",
            ),
        ],
        collapsed=True,
    )
    
    # Infrastructure group
    infrastructure = ActionGroup(
        id="group_infrastructure",
        name="Infrastructure",
        display_name="Infrastructure",
        icon="Server",
        color="#f59e0b",
        actions=[
            ActionNode(
                id="github_action",
                action="github_action",
                resource="github",
                flag="github_action",
                risk="HIGH",
                display_name="GitHub Action",
                icon="Github",
                color="#f59e0b",
            ),
            ActionNode(
                id="deploy",
                action="deploy",
                resource="k8s",
                flag="deploy",
                risk="HIGH",
                display_name="Deploy",
                icon="Rocket",
                color="#ea580c",
            ),
        ],
        collapsed=True,
    )
    
    # Root governance group (contains everything)
    root = ActionGroup(
        id="group_root",
        name="Governance",
        display_name="Citadel Governance",
        icon="Shield",
        color="#8b5cf6",
        subgroups=[communication, payment, database, infrastructure],
        collapsed=False,  # Root starts expanded
    )
    
    registry.set_root(root)
    
    # Register all subgroups
    for sg in root.subgroups:
        registry.register(sg)
        for ssg in sg.subgroups:
            registry.register(ssg)
    
    return registry


# Singleton
_registry_instance: Optional[GroupRegistry] = None


def get_registry() -> GroupRegistry:
    """Get or create the global group registry."""
    global _registry_instance
    if _registry_instance is None:
        _registry_instance = create_default_groups()
    return _registry_instance
