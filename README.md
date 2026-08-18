# NRPilot API

NRPilot API is the backend for NRPilot, an AI assistant for the [National Research Platform (NRP)](https://nrp.ai/). It provides a FastAPI interface that combines an OpenAI-compatible LLM with read-only Kubernetes diagnostics and official NRP documentation retrieval, helping researchers investigate workloads and find platform guidance.

## What it does

- Answers natural-language questions through a versioned chat API.
- Grounds cluster-diagnostic answers in read-only Kubernetes data, including namespaces, pods, events, resource quotas, node status, deployments, and pod logs.
- Searches official NRP documentation for policies, services, tutorials, and usage guidance; documentation-based answers include source URLs.
- Exposes health, liveness, and readiness probes for deployment platforms.
- Emits structured request, tool-invocation, and error logs without logging secrets.

NRPilot does not make Kubernetes changes. The agent is explicitly limited to read-only diagnostic tooling.

## Architecture

The application keeps framework and infrastructure concerns at the edge:

```text
FastAPI routes -> services -> domain models / adapters
                         ^
Agent -> LangChain tools -|
```

FastAPI routes validate and return requests, services coordinate application work, adapters encapsulate Kubernetes and documentation access, and only the agent and tools packages depend on LangChain.

## Requirements

- Python 3.13+
- [uv](https://docs.astral.sh/uv/)
- Access to a Kubernetes API with read-only credentials (for cluster diagnostics)
- Credentials for an OpenAI-compatible NRP LLM gateway (for chat)

## Quick start

1. Create a local environment file.

   ```bash
   cp .env.example .env
   ```

2. Set the required values in `.env`:

   ```dotenv
   KUBERNETES_HOST=https://kubernetes.example
   KUBERNETES_API_KEY=your-read-only-kubernetes-bearer-token
   NRP_LLM_TOKEN=your-llm-token
   NRP_LLM_BASE_URL=https://llm.nrp-nautilus.io/api/v1
   MODEL=qwen3-small
   ```

   `NRP_LLM_TOKEN` is required when the chat endpoint is used. Use a least-privilege Kubernetes service account; the application is designed for read-only access.

3. Install dependencies and start the development server.

   ```bash
   uv sync --group dev
   uv run uvicorn app.main:app --reload
   ```

   Or use the provided target:

   ```bash
   make dev
   ```

4. Check that the API is running.

   ```bash
   curl http://127.0.0.1:8000/health
   ```

   ```json
   {"status":"ok"}
   ```

Interactive API documentation is available at [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs).

## API

| Endpoint | Purpose |
| --- | --- |
| `GET /health` | General health check. |
| `GET /live` | Liveness probe. |
| `GET /ready` | Readiness probe. |
| `POST /api/v1/chat` | Submit a natural-language question to NRPilot. |

Every response includes an `X-Request-ID` header for request correlation.

### Chat example

```bash
curl -X POST http://127.0.0.1:8000/api/v1/chat \
  -H 'Content-Type: application/json' \
  -d '{"question":"Why is the api pod restarting in the default namespace?"}'
```

```json
{
  "answer": "...",
  "conversation_id": "8f56f283-7f0a-4af8-9cee-9902810f384f"
}
```

Send the returned `conversation_id` with a later question to preserve its context:

```json
{
  "question": "What should I check next?",
  "conversation_id": "8f56f283-7f0a-4af8-9cee-9902810f384f"
}
```

Conversation history is retained in memory for up to 20 turns per application
instance. It is not durable and is not shared between replicas. Questions must
be non-empty and no longer than 4,000 characters. The endpoint returns `503`
when Kubernetes or NRP documentation is unavailable, and `404` when a requested
Kubernetes resource cannot be found.

## Configuration

Configuration is read from environment variables. Copy `.env.example` to get started; do not commit credentials.

| Variable | Required | Default | Description |
| --- | --- | --- | --- |
| `KUBERNETES_HOST` | For diagnostics | — | Kubernetes API server URL. |
| `KUBERNETES_API_KEY` | For diagnostics | — | Kubernetes bearer token. Use a read-only service account. |
| `NRP_LLM_TOKEN` | For chat | — | Token for the OpenAI-compatible LLM gateway. |
| `NRP_LLM_BASE_URL` | For chat | — | Base URL for the LLM gateway. |
| `MODEL` | No | `qwen3-small` | Model name passed to the gateway. |
| `NRP_DOCUMENTATION_URL` | No | `https://nrp.ai/documentation/` | Official documentation root used for retrieval. |
| `NRP_DOCUMENTATION_TIMEOUT_SECONDS` | No | `10` | Documentation request timeout in seconds. |
| `NRP_DOCUMENTATION_MAX_RESULTS` | No | `3` | Maximum documentation pages supplied to the agent. |
| `LOG_LEVEL` | No | `INFO` | Application logging level. |
| `ENV` | No | `development` | Use `development` or `dev` for human-readable logs; other values produce JSON logs. |

## Development

The Makefile wraps the common development commands:

```bash
make test       # run the test suite with coverage
make lint       # run Ruff linting
make format     # apply Ruff formatting
make typecheck  # run MyPy against app/
make check      # format, lint, type-check, and test
```

Continuous integration runs formatting checks, Ruff, MyPy, and pytest on Python 3.13.

## Container and Kubernetes deployment

Build and run the production container locally:

```bash
docker build -t nrpilot-api .
docker run --rm -p 8000:8000 --env-file .env nrpilot-api
```

Kustomize manifests are provided under `k8s/` with `dev` and `prod` overlays. Before deployment, create or replace the placeholder secrets in `k8s/base/secret.yaml` through your deployment process; never store real tokens in source control.

```bash
kubectl apply -k k8s/overlays/dev -n gsoc-2026-chatbot
```

The deployment exposes `/ready` and `/live` as readiness and liveness probes.

## Project layout

```text
app/
  adapters/       External Kubernetes and documentation integrations
  agents/         LLM orchestration
  api/            FastAPI routes
  core/           Settings and structured logging
  domain/         Framework-independent ports and exceptions
  services/       Application orchestration
  tools/          Thin agent tools backed by services
tests/            Unit and API tests
k8s/              Kustomize deployment manifests
```

## Security and operational notes

- Keep `.env`, bearer tokens, and kubeconfig material out of version control.
- Grant the Kubernetes credential only the read permissions required by the diagnostic tools.
- Treat LLM responses as assistance, not as an authorization to modify production infrastructure.
- Use `X-Request-ID` when correlating an API response with structured logs.
