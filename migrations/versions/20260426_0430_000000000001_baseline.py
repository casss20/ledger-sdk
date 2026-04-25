"""Citadel baseline — initial schema from db/schema.sql

Revision ID: 000000000001
Revises: 
Create Date: 2026-04-26 04:30:00.000000+00:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '000000000001'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Apply the full Citadel schema from db/schema.sql."""
    # Read and execute the canonical schema file
    with open('db/schema.sql', 'r') as f:
        sql = f.read()
    
    # Execute each statement (split on ';' is naive but works for this schema)
    # Better: use connection.execute with text()
    from sqlalchemy import text
    conn = op.get_bind()
    
    # Execute the full SQL as a single script
    # PostgreSQL supports multi-statement execution
    conn.execute(text(sql))


def downgrade() -> None:
    """Drop all Citadel tables (destructive)."""
    # Order matters: drop dependent tables first
    tables = [
        'execution_results',
        'audit_events',
        'approvals',
        'decisions',
        'actions',
        'capabilities',
        'kill_switches',
        'policy_snapshots',
        'policies',
        'actors',
        'billing_usage_records',
        'billing_subscriptions',
        'billing_customers',
    ]
    
    from sqlalchemy import text
    conn = op.get_bind()
    
    for table in tables:
        conn.execute(text(f'DROP TABLE IF EXISTS {table} CASCADE'))
    
    # Drop custom types
    types = [
        'actor_type_enum',
        'actor_status_enum',
        'policy_status_enum',
        'scope_type_enum',
        'approval_status_enum',
        'decision_status_enum',
    ]
    for t in types:
        conn.execute(text(f'DROP TYPE IF EXISTS {t} CASCADE'))
