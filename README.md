# MCP Resume Assistant (FastMCP + LangGraph + Streamlit)

This project is a production-style MCP demo for resume bullet rewriting.
It combines:

- `mcp-server`: a FastMCP tool server (`resume_bullet_tool`)
- `mcp-host`: a FastAPI + LangGraph agent host that calls MCP tools and Gemini
- `streamlit`: a lightweight web UI that calls the host API

The repository includes Dockerfiles and Kubernetes manifests for deployment on GKE.

## 1) Features

- Rewrite weak resume bullets into stronger, impact-oriented wording
- Return one best variant plus two alternative variants
- Score bullet quality (0-10) with specific improvement tips
- Encourage metrics and measurable outcomes without fabricating numbers
- Support role-targeted phrasing (for example, Data Engineer or Software Engineer)
- Provide end-to-end deployability with Docker and Kubernetes

## 2) Project Structure

```text
.
├── mcp-server/                 # FastMCP tool service (port 9000)
│   ├── mcp_tool_server.py
│   ├── requirements.txt
│   └── Dockerfile
├── mcp-host/                   # LangGraph + FastAPI host (port 8000)
│   ├── src/
│   │   ├── agent/graph.py
│   │   └── api/apiserver.py
│   ├── requirements.txt
│   └── Dockerfile
├── streamlit/                  # UI (port 8080 in container)
│   ├── app.py
│   ├── requirements.txt
│   └── Dockerfile
└── k8s/                        # Kubernetes manifests (namespace: extraquiz)
```

## 3) How It Works

Request flow:

1. User enters prompt in Streamlit
2. Streamlit sends `POST /invoke` to `mcp-host`
3. `mcp-host` LangGraph agent calls MCP tools from `mcp-server`
4. Agent returns rewritten bullet suggestions + score info
5. Streamlit displays JSON response

Internal service URLs in K8s:

- `mcp-server`: `http://mcp-server:9000/mcp`
- `mcp-host`: `http://mcp-host:8000`

## 4) Prerequisites

- Python 3.10+ (3.11 recommended for host/server)
- Docker
- Google Cloud SDK (`gcloud`)
- `kubectl`
- A GCP project with GKE enabled
- A valid `GOOGLE_API_KEY` (Google AI Studio / Gemini)

## 5) Local Run (Without Kubernetes)

### 4.1 Start MCP server

```bash
cd mcp-server
pip install -r requirements.txt
fastmcp run mcp_tool_server.py:mcp --transport http --host 0.0.0.0 --port 9000
```

### 4.2 Start MCP host

In a new terminal:

```bash
cd mcp-host
pip install -r requirements.txt
export GOOGLE_API_KEY="YOUR_KEY"
export MCP_TOOL_URL="http://localhost:9000/mcp"
export GEMINI_MODEL="gemini-3-flash-preview"
uvicorn api.apiserver:app --host 0.0.0.0 --port 8000 --app-dir src
```

Health check:

```bash
curl http://localhost:8000/ok
```

### 4.3 Start Streamlit UI

In a third terminal:

```bash
cd streamlit
pip install -r requirements.txt
export MCP_CLIENT_API_URL="http://localhost:8000"
streamlit run app.py --server.port 8080
```

Then open `http://localhost:8080`.

## 6) Deploy to GKE

### 5.1 Create cluster

```bash
gcloud container clusters create extraquiz \
  --machine-type e2-standard-4 \
  --num-nodes 2 \
  --zone us-central1-a \
  --cluster-version latest
```

### 5.2 Authenticate

```bash
gcloud auth login
gcloud auth configure-docker
```

### 5.3 Build and push images

Update image registry/project if needed, then run:

```bash
gcloud builds submit ./mcp-server --tag gcr.io/mcppp/mcp-server:1.0
gcloud builds submit ./mcp-host --tag gcr.io/mcppp/mcp-host:1.0
gcloud builds submit ./streamlit --tag gcr.io/mcppp/streamlit:1.0
```

### 5.4 Create namespace and secret

```bash
kubectl apply -f k8s/namespace.yaml
```

Before applying `k8s/secrets-template.yaml`, replace `GOOGLE_API_KEY` with your real key:

```bash
kubectl apply -f k8s/secrets-template.yaml
```

### 5.5 Deploy all workloads

```bash
kubectl apply -f k8s/mcp-server-deployment.yaml
kubectl apply -f k8s/mcp-server-service.yaml
kubectl apply -f k8s/mcp-host-deployment.yaml
kubectl apply -f k8s/mcp-host-service.yaml
kubectl apply -f k8s/streamlit-deployment.yaml
kubectl apply -f k8s/streamlit-service.yaml
```

### 5.6 Verify

```bash
kubectl get pods -n extraquiz
kubectl get svc -n extraquiz
```

When `streamlit` service gets an external IP (`LoadBalancer`), open it in browser.

## 7) API Reference

### Host health endpoint

- `GET /ok`
- Response:

```json
{"status":"ok"}
```

### Host invoke endpoint

- `POST /invoke`
- Request body:

```json
{"query":"Rewrite this resume bullet for a Data Engineer role: worked on ETL pipelines"}
```

- Response body:

```json
{"output":"...agent final response..."}
```

## 8) Key Environment Variables

### `mcp-host`

- `GOOGLE_API_KEY` (required)
- `MCP_TOOL_URL` (default: `http://localhost:9000/mcp`)
- `GEMINI_MODEL` (default: `gemini-3-flash-preview`)

### `streamlit`

- `MCP_CLIENT_API_URL` (default: `http://localhost:8000`)

## 9) Notes

- The tool server uses a heuristic scoring approach for bullet quality.
- If your bullet has no metrics, the system will encourage placeholders instead of fabricating numbers.
- For production use, consider adding authentication, rate limiting, centralized logging, and CI/CD.
