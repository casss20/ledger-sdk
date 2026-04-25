# Email Governance Rule
# Auto-discovered by CITADEL.catalog

GOVERNANCE = {
    "action": "send_email",
    "resource": "outbound_email",
    "flag": "email_send",
    "risk": "HIGH",
    "approval": "HARD",
    
    # Rate limits
    "max_daily": 100,
    "max_hourly": 20,
    
    # Validation
    "required_fields": ["to", "subject", "body"],
    "optional_fields": ["from_addr", "cc", "bcc", "attachments"],
    
    # UI
    "display_name": "Send Email",
    "icon": "Mail",
    "color": "#ef4444",  # Red for high risk
    "description": "Send an email to a customer or user. Requires human approval.",
}
