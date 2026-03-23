from __future__ import annotations

import os
from contextlib import asynccontextmanager
from typing import Optional, Dict

from fastapi import FastAPI
from pydantic import BaseModel

from agent.graph import get_graph, run_agent_async


class InvokeRequest(BaseModel):
    query: str


class InvokeResponse(BaseModel):
    output: str



@asynccontextmanager
async def lifespan(app: FastAPI):
    # Warm up the graph on startup (loads MCP tools once)
    await get_graph()
    yield

app = FastAPI(title="LangGraph MCP Host API", version="1.0", lifespan=lifespan)

@app.get("/ok")
def ok() -> Dict[str, str]:
    return {"status": "ok"}


@app.post("/invoke", response_model=InvokeResponse)
async def invoke(req: InvokeRequest) -> InvokeResponse:
    print(f"Received query: {req.query}")
    output = await run_agent_async(req.query)
    return InvokeResponse(output=output)


if __name__ == "__main__":
    # uvicorn server:app --host 0.0.0.0 --port 8080
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", "8000")))