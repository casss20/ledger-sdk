# Getting Started with Ledger SDK for Go

## What you'll learn

- Install Ledger SDK via go get
- Govern your first agent action
- Understand `gt_` tokens
- View actions in the dashboard
- Connect to a Go-based agent service

## Prerequisites

- Go 1.21 or higher
- A Ledger API key ([get one free](https://dashboard.ledger.dev))

---

## Step 1: Install Ledger SDK

```bash
go get github.com/ledger/sdk-go
```

Verify in `go.mod`:
```
require github.com/ledger/sdk-go v1.x.x
```

---

## Step 2: Initialize the client

```go
package main

import (
    "context"
    "fmt"
    "log"
    "os"

    "github.com/ledger/sdk-go"
)

func main() {
    ctx := context.Background()

    client, err := sdk.NewClient(sdk.Config{
        APIKey:      os.Getenv("LEDGER_API_KEY"),
        Environment: "sandbox",
    })
    if err != nil {
        log.Fatal(err)
    }

    if err := client.Ping(ctx); err != nil {
        log.Fatal(err)
    }
    fmt.Println("Connected to Ledger sandbox")
}
```

---

## Step 3: Govern your first action

```go
action := client.Govern(ctx, sdk.GovernanceRequest{
    AgentID: "email-agent-01",
    Action:  "email.send",
    Params: map[string]interface{}{
        "to":      "user@example.com",
        "subject": "Welcome",
        "body":    "Thanks for signing up!",
    },
})

result, err := action.Execute(ctx)
if err != nil {
    switch e := err.(type) {
    case *sdk.PolicyDeniedError:
        fmt.Printf("Denied by policy: %s\n", e.PolicyName)
    case *sdk.ApprovalRequiredError:
        fmt.Printf("Approval required: %s\n", e.ApprovalURL)
    default:
        log.Fatal(err)
    }
} else {
    fmt.Printf("Allowed. Token: %s\n", result.GovernanceToken)
}
```

---

## Step 4: Understanding `gt_` tokens

```go
record, err := client.Audit.Get(ctx, result.GovernanceToken)
if err != nil {
    log.Fatal(err)
}
fmt.Printf("Decision: %s, Policy: %s, Time: %s\n",
    record.Decision, record.PolicyName, record.Timestamp)
```

---

## Step 5: Connect to a Go agent service

Use middleware to intercept all tool calls:

```go
func LedgerMiddleware(client *sdk.Client, agentID string) func(next http.Handler) http.Handler {
    return func(next http.Handler) http.Handler {
        return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
            ctx := r.Context()

            // Extract action from request
            action := r.Header.Get("X-Agent-Action")
            if action != "" {
                governed := client.Govern(ctx, sdk.GovernanceRequest{
                    AgentID: agentID,
                    Action:  action,
                    Params:  extractParams(r),
                })

                if _, err := governed.Execute(ctx); err != nil {
                    http.Error(w, fmt.Sprintf("Governance: %v", err), http.StatusForbidden)
                    return
                }
            }
            next.ServeHTTP(w, r)
        })
    }
}
```

---

## Troubleshooting

### "API key invalid"
Use `ldk_test_*` for sandbox, `ldk_live_*` for production.

### "All actions denied"
Create an allow policy:
```go
client.Policies.Create(ctx, sdk.Policy{
    Name: "allow-email",
    Trigger: sdk.Trigger{Action: "email.send"},
    Enforcement: sdk.Enforcement{Type: "allow"},
})
```

---

## Next steps

- [Core Concepts: Governance Tokens](../core-concepts/governance-tokens.md)
- [Core Concepts: Policies](../core-concepts/policies.md)
- [Recipe: Database Write Protection](../recipes/database-write-protection.md)
