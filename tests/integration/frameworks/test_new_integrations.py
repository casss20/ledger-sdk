"""
Tests for Citadel framework integrations.

Covers:
- K2.6 integration
- LangGraph integration
- Codex integration
- Claude Code integration
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from citadel.core.sdk import CitadelClient, CitadelResult
from citadel.integrations.k2_6 import (
    GovernedK26Agent,
    GovernedK26Task,
    GovernedK26Workflow,
    K26GovernanceServer,
)
from citadel.integrations.langgraph import (
    GovernedNode,
    GovernedStateGraph,
    LangGraphGovernanceServer,
)
from citadel.integrations.codex import (
    GovernedCodex,
    CodexGovernanceServer,
)
from citadel.integrations.claude_code import (
    GovernedClaudeCode,
    ClaudeCodeGovernanceServer,
)


# =====================================================================
# Fixtures
# =====================================================================

@pytest.fixture
def mock_client():
    """Create a mock CitadelClient."""
    client = MagicMock(spec=CitadelClient)
    client.decide = AsyncMock()
    client.execute = AsyncMock()
    client._client = MagicMock()
    client._client.get = AsyncMock()
    return client


@pytest.fixture
def executed_result():
    """CitadelResult for executed action."""
    return CitadelResult(
        action_id="test-123",
        status="executed",
        winning_rule="allow_all",
        reason="Allowed",
        executed=True,
    )


@pytest.fixture
def blocked_result():
    """CitadelResult for blocked action."""
    return CitadelResult(
        action_id="test-456",
        status="blocked",
        winning_rule="block_all",
        reason="Action blocked by policy",
        executed=False,
    )


@pytest.fixture
def pending_result():
    """CitadelResult for pending approval."""
    return CitadelResult(
        action_id="test-789",
        status="pending_approval",
        winning_rule="require_approval",
        reason="Requires human approval",
        executed=False,
    )


# =====================================================================
# K2.6 Integration Tests
# =====================================================================

@pytest.mark.asyncio
async def test_k26_agent_executes_when_allowed(mock_client, executed_result):
    """K2.6 agent executes task when governance allows."""
    mock_client.decide.return_value = executed_result
    mock_client.execute.return_value = executed_result
    
    agent = GovernedK26Agent(
        citadel_client=mock_client,
        name="test-agent",
        description="Test agent",
    )
    
    task = GovernedK26Task(
        citadel_client=mock_client,
        name="test-task",
        description="Test task",
        action="test.execute",
        agent=agent,
    )
    
    result = await task.execute()
    
    assert "GOVERNANCE" not in result
    mock_client.decide.assert_called_once()


@pytest.mark.asyncio
async def test_k26_agent_blocked_when_policy_denies(mock_client, blocked_result):
    """K2.6 agent is blocked when policy denies action."""
    mock_client.decide.return_value = blocked_result
    
    agent = GovernedK26Agent(
        citadel_client=mock_client,
        name="test-agent",
    )
    
    task = GovernedK26Task(
        citadel_client=mock_client,
        name="test-task",
        action="test.execute",
        agent=agent,
    )
    
    result = await task.execute()
    
    assert "GOVERNANCE: blocked" in result
    assert "Action blocked by policy" in result


@pytest.mark.asyncio
async def test_k26_governance_server_check_action(mock_client, executed_result):
    """K2.6 governance server checks action correctly."""
    mock_client.decide.return_value = executed_result
    
    server = K26GovernanceServer(mock_client)
    result = await server.check_action(
        action="delete_user",
        resource="user_123",
        risk_level="critical",
    )
    
    assert result["allowed"] is True
    assert result["requires_approval"] is False
    assert "action_id" in result


@pytest.mark.asyncio
async def test_k26_governance_server_kill_switch(mock_client):
    """K2.6 governance server checks kill switch."""
    mock_response = MagicMock()
    mock_response.json.return_value = {"active": True}
    mock_client._client.get.return_value = mock_response
    
    server = K26GovernanceServer(mock_client)
    result = await server.check_kill_switch()
    
    assert result["active"] is True
    assert result["action"] == "STOP_IMMEDIATELY"


@pytest.mark.asyncio
async def test_k26_governance_server_log_action(mock_client, executed_result):
    """K2.6 governance server logs actions."""
    mock_client.execute.return_value = executed_result
    
    server = K26GovernanceServer(mock_client)
    result = await server.log_action(
        action="execute_query",
        resource="customer_table",
        result="success",
    )
    
    assert result["logged"] is True
    assert result["event_id"] == "test-123"


@pytest.mark.asyncio
async def test_k26_workflow_executes_all_tasks(mock_client, executed_result):
    """K2.6 workflow executes all governed tasks."""
    mock_client.decide.return_value = executed_result
    mock_client.execute.return_value = executed_result
    
    workflow = GovernedK26Workflow(
        citadel_client=mock_client,
        name="test-workflow",
    )
    
    task1 = GovernedK26Task(
        citadel_client=mock_client,
        name="task-1",
        action="step.1",
    )
    task2 = GovernedK26Task(
        citadel_client=mock_client,
        name="task-2",
        action="step.2",
    )
    
    workflow.tasks = [task1, task2]
    result = await workflow.run()
    
    assert "GOVERNANCE" not in result


# =====================================================================
# LangGraph Integration Tests
# =====================================================================

@pytest.mark.asyncio
async def test_langgraph_node_executes_when_allowed(mock_client, executed_result):
    """LangGraph node executes when governance allows."""
    mock_client.decide.return_value = executed_result
    mock_client.execute.return_value = executed_result
    
    node = GovernedNode(
        citadel_client=mock_client,
        name="search",
        action="web.search",
    )
    
    result = await node.execute({"query": "AI safety"})
    
    assert "_governance" not in result or not result["_governance"].get("blocked")


@pytest.mark.asyncio
async def test_langgraph_node_blocked_when_policy_denies(mock_client, blocked_result):
    """LangGraph node is blocked when policy denies."""
    mock_client.decide.return_value = blocked_result
    
    node = GovernedNode(
        citadel_client=mock_client,
        name="search",
        action="web.search",
    )
    
    result = await node.execute({"query": "AI safety"})
    
    assert result["_governance"]["blocked"] is True


@pytest.mark.asyncio
async def test_langgraph_graph_executes_nodes(mock_client, executed_result):
    """LangGraph graph executes all governed nodes."""
    mock_client.decide.return_value = executed_result
    mock_client.execute.return_value = executed_result
    
    graph = GovernedStateGraph(
        citadel_client=mock_client,
        name="test-graph",
    )
    
    node1 = GovernedNode(
        citadel_client=mock_client,
        name="search",
        action="web.search",
    )
    node2 = GovernedNode(
        citadel_client=mock_client,
        name="analyze",
        action="data.analyze",
    )
    
    graph.add_node(node1)
    graph.add_node(node2)
    graph.add_edge("search", "analyze")
    
    result = await graph.run({"query": "AI safety"})
    
    assert "_governance" not in result or not result.get("_governance", {}).get("blocked")


@pytest.mark.asyncio
async def test_langgraph_governance_server(mock_client, executed_result):
    """LangGraph governance server provides correct responses."""
    mock_client.decide.return_value = executed_result
    
    server = LangGraphGovernanceServer(mock_client)
    result = await server.check_action(
        action="data.analyze",
        resource="dataset:customer",
    )
    
    assert result["allowed"] is True
    assert "action_id" in result


# =====================================================================
# Codex Integration Tests
# =====================================================================

@pytest.mark.asyncio
async def test_codex_generates_code_when_allowed(mock_client, executed_result):
    """Codex generates code when governance allows."""
    mock_client.decide.return_value = executed_result
    mock_client.execute.return_value = executed_result
    
    codex = GovernedCodex(citadel_client=mock_client)
    result = await codex.generate_code(
        prompt="Write a sort function",
        language="python",
    )
    
    assert "GOVERNANCE" not in result
    assert "python" in result


@pytest.mark.asyncio
async def test_codex_blocked_when_policy_denies(mock_client, blocked_result):
    """Codex is blocked when policy denies code generation."""
    mock_client.decide.return_value = blocked_result
    
    codex = GovernedCodex(citadel_client=mock_client)
    result = await codex.generate_code(
        prompt="Write malware",
        language="python",
    )
    
    assert "GOVERNANCE: blocked" in result


@pytest.mark.asyncio
async def test_codex_execution_requires_approval(mock_client, executed_result):
    """Codex code execution always requires approval."""
    mock_client.decide.return_value = executed_result
    mock_client.execute.return_value = executed_result
    
    codex = GovernedCodex(citadel_client=mock_client)
    result = await codex.execute_code(
        code="print('hello')",
        language="python",
    )
    
    assert result["success"] is True
    mock_client.decide.assert_called_once()


@pytest.mark.asyncio
async def test_codex_review_detects_dangerous_patterns(mock_client):
    """Codex review detects dangerous code patterns."""
    codex = GovernedCodex(citadel_client=mock_client)
    
    dangerous_code = """
import os
os.system('rm -rf /')
"""
    
    result = await codex.review_code(dangerous_code, "python")
    
    assert result["safe_to_execute"] is False
    assert result["risk_level"] == "high"
    assert len(result["found_patterns"]) > 0


@pytest.mark.asyncio
async def test_codex_review_passes_safe_code(mock_client):
    """Codex review passes safe code."""
    codex = GovernedCodex(citadel_client=mock_client)
    
    safe_code = """
def hello():
    return "Hello, World!"
"""
    
    result = await codex.review_code(safe_code, "python")
    
    assert result["safe_to_execute"] is True
    assert result["risk_level"] == "low"


# =====================================================================
# Claude Code Integration Tests
# =====================================================================

@pytest.mark.asyncio
async def test_claude_code_executes_when_allowed(mock_client, executed_result):
    """Claude Code executes when governance allows."""
    mock_client.decide.return_value = executed_result
    mock_client.execute.return_value = executed_result
    
    claude = GovernedClaudeCode(citadel_client=mock_client)
    result = await claude.execute(
        prompt="Refactor this function",
        files=["src/utils.py"],
    )
    
    assert "GOVERNANCE" not in result


@pytest.mark.asyncio
async def test_claude_code_blocked_when_policy_denies(mock_client, blocked_result):
    """Claude Code is blocked when policy denies."""
    mock_client.decide.return_value = blocked_result
    
    claude = GovernedClaudeCode(citadel_client=mock_client)
    result = await claude.execute(
        prompt="Delete all files",
        files=["src/"],
    )
    
    assert "GOVERNANCE: blocked" in result


@pytest.mark.asyncio
async def test_claude_code_edit_requires_approval(mock_client, executed_result):
    """Claude Code file edits require approval."""
    mock_client.decide.return_value = executed_result
    mock_client.execute.return_value = executed_result
    
    claude = GovernedClaudeCode(citadel_client=mock_client)
    result = await claude.edit_file(
        file_path="src/utils.py",
        edit_description="Add logging",
    )
    
    assert result["success"] is True
    mock_client.decide.assert_called_once()


@pytest.mark.asyncio
async def test_claude_code_governance_server(mock_client, executed_result):
    """Claude Code governance server provides correct responses."""
    mock_client.decide.return_value = executed_result
    
    server = ClaudeCodeGovernanceServer(mock_client)
    result = await server.check_action(
        action="claude.edit",
        resource="file:src/utils.py",
    )
    
    assert result["allowed"] is True
    assert result["requires_approval"] is True  # Code changes always require approval


# =====================================================================
# Integration Import Tests
# =====================================================================

def test_all_integrations_are_importable():
    """All integration classes can be imported from citadel.integrations."""
    from citadel.integrations import (
        # K2.6
        GovernedK26Agent,
        GovernedK26Task,
        GovernedK26Workflow,
        K26GovernanceServer,
        # LangGraph
        GovernedNode,
        GovernedStateGraph,
        LangGraphGovernanceServer,
        # Codex
        GovernedCodex,
        CodexGovernanceServer,
        # Claude Code
        GovernedClaudeCode,
        ClaudeCodeGovernanceServer,
    )
    
    # Just verifying imports work
    assert GovernedK26Agent is not None
    assert GovernedNode is not None
    assert GovernedCodex is not None
    assert GovernedClaudeCode is not None
