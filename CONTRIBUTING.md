# Contributing to Ghost

Thanks for your interest in contributing to Ghost! This guide will help you get started.

## Ways to Contribute

- **Report bugs** -- Open an issue with steps to reproduce
- **Suggest packages to monitor** -- Email paul@validia.ai or open an issue
- **Improve detection** -- Tune the agent's prompts, add new tools, reduce false positives
- **Add registry support** -- Help us monitor more ecosystems (Cargo, Go modules, Maven, RubyGems)
- **Improve the UI** -- Frontend enhancements, accessibility, mobile improvements
- **Write tests** -- We need them!
- **Documentation** -- Fix typos, improve explanations, add examples

## Getting Started

### 1. Fork and Clone

```bash
git clone https://github.com/YOUR_USERNAME/versatility-labs.git ghost
cd ghost
```

### 2. Set Up Local Development

**Backend (Docker):**

```bash
cp .env.example .env
# Edit .env: add OPENAI_API_KEY, set DATABASE_URL

docker-compose up --build
```

**Frontend (native):**

```bash
cd frontend
npm install
npm run dev
```

**Seed packages:**

```bash
docker exec ghost-backend-1 python -m seed
```

The app will be running at:
- Frontend: http://localhost:3000
- Backend API: http://localhost:8000
- API docs: http://localhost:8000/docs

### 3. Run the MCP Server (optional)

```bash
cd mcp
npm install
claude mcp add ghost node -- $(pwd)/index.js
```

## Project Structure

| Directory | What it does |
|-----------|-------------|
| `backend/app/services/analysis/agent.py` | The security agent -- tools and instructions |
| `backend/app/services/analysis/pipeline.py` | Analysis orchestrator |
| `backend/app/services/registry/` | npm, PyPI, GitHub polling clients |
| `backend/app/services/ingestion.py` | Poll coordinator |
| `backend/app/routers/` | API endpoints |
| `frontend/src/app/` | Next.js pages |
| `frontend/src/components/` | React components |
| `mcp/index.js` | MCP server for AI coding tools |

## Making Changes

### Backend

The backend is Python 3.12 + FastAPI. Key areas:

**Adding a new agent tool** (`backend/app/services/analysis/agent.py`):
1. Define an async function with `@function_tool`
2. Add it to the `security_agent` tools list
3. Update `AGENT_INSTRUCTIONS` to tell the agent when to use it

**Adding a new registry** (e.g., Cargo, Maven):
1. Create `backend/app/services/registry/cargo.py` implementing `RegistryClient`
2. Add it to the client map in `ingestion.py`
3. Update `dependency_analysis.py` to extract deps from the new manifest format

**Improving detection accuracy**:
- Edit `AGENT_INSTRUCTIONS` in `agent.py` -- this is the system prompt
- Add patterns to `scan_for_suspicious_patterns` in `agent.py`
- Tune scoring guidance in the instructions

### Frontend

The frontend is Next.js 14 + TailwindCSS. Dark/light mode supported.

- Pages are in `frontend/src/app/`
- Components in `frontend/src/components/`
- API client in `frontend/src/lib/api.ts`
- Types in `frontend/src/lib/types.ts`

### MCP Server

The MCP server is a single Node.js file (`mcp/index.js`). To add a new tool:

1. Add a `server.tool()` call with name, description, schema, and handler
2. The handler calls the Ghost API and formats the response

## Code Style

**Backend:**
- Python 3.12, type hints everywhere
- Ruff for linting (`ruff check .`)
- Async/await for all I/O

**Frontend:**
- TypeScript strict mode
- TailwindCSS for styling (no CSS modules)
- Use `cn()` utility for conditional classes

## Submitting a Pull Request

1. Create a feature branch: `git checkout -b my-feature`
2. Make your changes
3. Test locally (backend + frontend running)
4. Commit with a clear message
5. Push and open a PR against `main`

### PR Guidelines

- Keep PRs focused -- one feature or fix per PR
- Include context on what the change does and why
- If changing detection logic, include before/after examples
- If adding a tool, show sample agent output

## Areas We Need Help

### High Priority
- **Test suite** -- Unit and integration tests for the backend
- **Go module lookup** -- The agent can't investigate Go dependencies yet
- **Cargo/crates.io support** -- New registry client
- **Rate limiting** -- Public API rate limiting
- **Webhook retries** -- Retry failed Slack/webhook deliveries

### Nice to Have
- RSS feed for analyses
- Email alert channel
- Browser extension that checks packages on npmjs.com/pypi.org
- GitHub Action that runs Ghost on PR dependency changes
- Historical trend charts on the dashboard

## Questions?

- Open an issue on GitHub
- Email paul@validia.ai
- Join [FrontierSec on Slack](https://join.slack.com/t/frontiersec/shared_invite/zt-3s0tfehvr-Qjqa1w8ITe7O7zZcd_23ag)
