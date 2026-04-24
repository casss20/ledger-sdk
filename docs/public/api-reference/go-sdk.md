# Go SDK Reference

## Installation

```bash
go get github.com/CITADEL/sdk-go
```

## Client

```go
import "github.com/CITADEL/sdk-go"

client, err := sdk.NewClient(sdk.Config{
    APIKey:      os.Getenv("citadel_API_KEY"),
    Environment: "sandbox",
})
```

## Govern Actions

```go
action := client.Govern(ctx, sdk.GovernanceRequest{
    AgentID: "agent-123",
    Action:  "email.send",
    Params:  map[string]interface{}{"to": "user@example.com"},
})

result, err := action.Execute(ctx)
```

## Error Handling

```go
if err != nil {
    switch e := err.(type) {
    case *sdk.PolicyDeniedError:
        fmt.Printf("Denied: %s\n", e.PolicyName)
    case *sdk.ApprovalRequiredError:
        fmt.Printf("Approval: %s\n", e.ApprovalURL)
    case *sdk.RateLimitError:
        fmt.Printf("Retry after: %ds\n", e.RetryAfter)
    }
}
```

## Audit

```go
records, err := client.Audit.Query(ctx, sdk.AuditQuery{AgentID: "agent-123", Limit: 100})
record, err := client.Audit.Get(ctx, "gt_...")
isValid, err := client.Audit.VerifyChain(ctx, record)
```

## Kill Switch

```go
client.KillSwitch.Activate(ctx, sdk.KillSwitchRequest{AgentID: "agent-123", Reason: "..."})
client.KillSwitch.Deactivate(ctx, sdk.KillSwitchRequest{AgentID: "agent-123", Reason: "..."})
```
