# Stripe Charge Governance Rule
# Auto-discovered by ledger.catalog

GOVERNANCE = {
    "action": "stripe_charge",
    "resource": "stripe",
    "flag": "stripe_charge",
    "risk": "HIGH",
    "approval": "HARD",
    
    # Rate limits
    "max_daily": 50,
    "max_hourly": 10,
    
    # Thresholds
    "max_amount": 10000.00,  # $10k limit
    
    # Validation
    "required_fields": ["amount", "customer_id"],
    "optional_fields": ["description", "metadata"],
    
    # UI
    "display_name": "Charge Customer",
    "icon": "CreditCard",
    "color": "#22c55e",  # Green for money
    "description": "Charge a customer via Stripe. Always requires approval.",
}
