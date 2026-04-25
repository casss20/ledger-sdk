# Database Write Governance Rule
# Auto-discovered by CITADEL.catalog

GOVERNANCE = {
    "action": "write_database",
    "resource": "production_db",
    "flag": "db_write",
    "risk": "MEDIUM",
    "approval": "HARD",
    
    # Rate limits
    "max_daily": 1000,
    "max_hourly": 100,
    
    # Thresholds
    "max_rows": 10000,  # High risk if affecting more rows
    
    # Validation
    "required_fields": ["query"],
    "optional_fields": ["params", "transaction_id"],
    
    # UI
    "display_name": "Write to Database",
    "icon": "Database",
    "color": "#3b82f6",  # Blue for data
    "description": "Execute a database write query. Approval required for high-cost operations.",
}
