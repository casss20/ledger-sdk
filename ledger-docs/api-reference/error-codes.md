# Error Codes

## LEDGER_001 — Policy Denied
Action blocked by active policy. Check `policy_name` and `reason` in response.

## LEDGER_002 — Approval Required
Human approval needed. Access `approval_url` to review.

## LEDGER_003 — Rate Limit Exceeded
Too many requests. Wait `retry_after` seconds or upgrade tier.

## LEDGER_004 — Agent Not Authenticated
Agent identity invalid or expired. Re-register the agent.

## LEDGER_005 — Kill Switch Activated
Agent or system is stopped. Check kill switch status in dashboard.

## LEDGER_006 — Audit Trail Unavailable
Temporary ingestion delay. Retry after 5 seconds.

## LEDGER_007 — Trust Score Below Threshold
Agent trust score too low. Review agent behavior or restore capabilities.

## LEDGER_008 — Invalid Governance Token
Token malformed or expired. Verify token format starts with `gt_`.

## LEDGER_009 — Policy Compilation Failed
YAML syntax error. Validate policy at dashboard policy editor.

## LEDGER_010 — Webhook Delivery Failed
Endpoint returned non-200. Verify webhook URL and SSL certificate.
