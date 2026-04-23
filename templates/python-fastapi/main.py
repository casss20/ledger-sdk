from fastapi import FastAPI, Depends, HTTPException
from pydantic import BaseModel
import ledger

# 1. Configure the Ledger SDK
ledger.configure(
    base_url="http://localhost:8000",
    api_key="your-dev-key",
    tenant_id="acme_corp"
)

app = FastAPI(title="Governed Agent API")

class QueryRequest(BaseModel):
    prompt: str
    agent_id: str

@app.post("/query")
@ledger.guard(action="agent.query", resource="llm.gpt4")
async def handle_query(request: QueryRequest):
    """
    This endpoint is automatically protected by Ledger.
    - Policy evaluation happens BEFORE the function body runs.
    - If blocked, it returns 403.
    - If approval is required, it returns 202 with a token.
    - If allowed, it executes and logs to the audit chain.
    """
    
    # Simulate agent logic
    return {
        "response": f"Processed query: {request.prompt}",
        "governance": "verified"
    }

@app.get("/health")
async def health():
    return {"status": "online"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=3000)
