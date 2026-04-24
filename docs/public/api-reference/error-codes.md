# Error Codes

## citadel_001 â€” Policy Denied
Action blocked by active policy. Check `policy_name` and `reason` in response.

## citadel_002 â€” Approval Required
Human approval needed. Access `approval_url` to review.

## citadel_003 â€” Rate Limit Exceeded
Too many requests. Wait `retry_after` seconds or upgrade tier.

## citadel_004 â€” Agent Not Authenticated
Agent identity invalid or expired. Re-register the agent.

## citadel_005 â€” Kill Switch Activated
Agent or system is stopped. Check kill switch status in dashboard.

## citadel_006 â€” Audit Trail Unavailable
Temporary ingestion delay. Retry after 5 seconds.

## citadel_007 â€” Trust Score Below Threshold
Agent trust score too low. Review agent behavior or restore capabilities.

## citadel_008 â€” Invalid Governance Token
Token malformed or expired. Verify token format starts with `gt_`.

## citadel_009 â€” Policy Compilation Failed
YAML syntax error. Validate policy at dashboard policy editor.

## citadel_010 â€” Webhook Delivery Failed
Endpoint returned non-200. Verify webhook URL and SSL certificate.
