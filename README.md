<p align="center">
  <img src="frontend/public/ghost-logo.png" alt="Ghost" width="80" />
</p>

<h1 align="center">Ghost</h1>

<p align="center">
  <strong>Real-time supply chain threat intelligence for npm, PyPI, and GitHub.</strong>
  <br />
  <em>Agentic LLM-powered analysis that catches malicious packages before they spread.</em>
</p>

<p align="center">
  <a href="https://ghost.validia.ai">Live Dashboard</a> &middot;
  <a href="https://join.slack.com/t/frontiersec/shared_invite/zt-3s0tfehvr-Qjqa1w8ITe7O7zZcd_23ag">Get Alerts (Slack)</a> &middot;
  <a href="https://x.com/pjvann">@pjvann</a>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/packages_monitored-545+-22c55e?style=flat-square" />
  <img src="https://img.shields.io/badge/registries-npm%20%7C%20PyPI%20%7C%20GitHub-blue?style=flat-square" />
  <img src="https://img.shields.io/badge/detection-<60s-orange?style=flat-square" />
  <img src="https://img.shields.io/badge/license-MIT-white?style=flat-square" />
</p>

---

## The Problem

Supply chain attacks are growing fast. The xz utils backdoor, the event-stream incident, the ua-parser-js hijack, the Axios compromise -- these all slipped through because nobody was doing automated deep analysis at the speed of release.

Existing tools rely on signature matching and known CVE databases. They can't catch **novel attacks** -- a brand new malicious dependency with zero prior history, an obfuscated payload in a version bump, a typosquatted package name.

## How Ghost Works

Ghost monitors 545+ of the most critical open source packages across npm, PyPI, and GitHub. When a new version drops or a commit lands on main, Ghost:

1. **Detects** the change within 60 seconds
2. **Downloads** both the old and new versions
3. **Diffs** the source code
4. **Runs an AI security agent** that investigates the changes using real tools

The agent doesn't just read a diff and guess. It has tools to:

- **Look up packages** on npm/PyPI -- check download counts, repo links, description
- **Look up GitHub repos** -- check stars, activity, archived status, recent commits
- **Download and extract packages** -- actually inspect the source code of new dependencies
- **Diff dependency versions** -- see what changed inside a dependency that got bumped
- **Scan for suspicious patterns** -- network calls, process execution, obfuscation, credential access
- **Read specific files** -- inspect install scripts, entry points, anything suspicious

If a package adds a new dependency with 2 weekly downloads and a postinstall script that curls a binary -- Ghost catches it. If a version bump in a sub-dependency introduces `eval(atob(...))` -- Ghost catches it.

## Architecture

```
                    Cloud Scheduler (every 60s)
                            |
                            v
                    +---------------+
                    |   Ingestion   |  Polls npm, PyPI, GitHub
                    |   Service     |  for version changes
                    +-------+-------+
                            |
                      new version detected
                            |
                            v
                    +---------------+
                    |    Diff       |  Downloads old + new
                    |  Generator    |  Generates unified diff
                    +-------+-------+
                            |
                            v
                    +---------------+
                    |   Security    |  OpenAI Agents SDK
                    |    Agent      |  GPT-4o with 6 tools
                    +-------+-------+
                            |
                    +-------+-------+
                    |               |
                    v               v
            +----------+    +-----------+
            |  Slack   |    | Dashboard |
            |  Alert   |    |   API     |
            +----------+    +-----------+
```

### Tech Stack

| Component | Technology |
|-----------|-----------|
| **Backend** | Python 3.12, FastAPI, SQLAlchemy (async), Alembic |
| **Analysis** | OpenAI Agents SDK, GPT-4o with function tools |
| **Frontend** | Next.js 14, React, TailwindCSS |
| **Database** | PostgreSQL (Neon) |
| **Deployment** | GCP Cloud Run, Vercel, Cloud Scheduler |
| **MCP Server** | Node.js, @modelcontextprotocol/sdk |

### The Agent's Toolbox

| Tool | Purpose |
|------|---------|
| `lookup_package_info` | Check npm/PyPI package metadata, downloads, repo |
| `lookup_github_repo` | Check GitHub repo stars, activity, releases, archived status |
| `download_and_list_files` | Download a package version, list files, flag install scripts |
| `read_file_content` | Read specific files from downloaded packages |
| `diff_package_versions` | Diff two versions of a dependency to see what changed |
| `scan_for_suspicious_patterns` | Regex scan for network calls, eval, process exec, etc. |

---

## MCP Server -- Use Ghost in Your AI Coding Tools

Ghost ships with an MCP (Model Context Protocol) server that lets any AI coding assistant check packages against Ghost's live threat intelligence.

### Add to Claude Code

```bash
cd ghost/mcp && npm install
claude mcp add ghost node -- /path/to/ghost/mcp/index.js
```

Then in any Claude Code session:

> "Check if axios is safe to install"
>
> "Are there any supply chain threats right now?"
>
> "What's the Ghost monitoring status?"

### Add to OpenAI Codex

Add to your Codex MCP config:

```json
{
  "ghost": {
    "type": "stdio",
    "command": "node",
    "args": ["/path/to/ghost/mcp/index.js"]
  }
}
```

### MCP Tools

| Tool | Description |
|------|-------------|
| `check_package` | Check a specific package for supply chain threats before adding it as a dependency |
| `get_threat_alerts` | Get all packages with elevated risk scores |
| `ghost_status` | Get monitoring stats -- packages tracked, analyses run, threat level |

The MCP server hits your local Ghost API by default. Set `GHOST_API_URL` to point to a remote instance.

---

## Self-Hosting

### Prerequisites

- Docker & Docker Compose
- Python 3.12+
- Node.js 20+
- OpenAI API key (for the analysis agent)
- PostgreSQL database

### Quick Start (Local Development)

```bash
# Clone
git clone https://github.com/vaulpann/versatility-labs.git ghost
cd ghost

# Configure
cp .env.example .env
# Edit .env with your OPENAI_API_KEY and DATABASE_URL

# Start backend + postgres
docker-compose up --build

# In another terminal, start frontend
cd frontend && npm install && npm run dev

# Seed packages
docker exec ghost-backend-1 python -m seed

# Open http://localhost:3000
```

### Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `DATABASE_URL` | Yes | PostgreSQL connection string (asyncpg format) |
| `OPENAI_API_KEY` | Yes | OpenAI API key for the security agent |
| `GITHUB_TOKEN` | Recommended | GitHub PAT for higher rate limits (5000 req/hr vs 60) |
| `SLACK_WEBHOOK_URL` | Optional | Slack incoming webhook for alerts |
| `ADMIN_API_KEY` | Optional | Protects webhook/poll endpoints |
| `ALLOWED_ORIGINS` | Optional | CORS origins (comma-separated) |
| `FRONTEND_URL` | Optional | Frontend URL for links in Slack alerts |

### Production Deployment

Ghost is designed for GCP Cloud Run + Vercel:

1. **Database**: Neon (managed Postgres) or Cloud SQL
2. **Backend**: `gcloud run deploy ghost-api --source ./backend`
3. **Frontend**: Connect repo to Vercel, set root directory to `frontend`
4. **Auto-polling**: Cloud Scheduler hitting `POST /api/v1/webhooks/poll` every minute
5. **Alerts**: Configure a Slack webhook via the database

See the full deployment guide in [CONTRIBUTING.md](CONTRIBUTING.md).

---

## API

All read endpoints are public. Write endpoints are removed or protected by `ADMIN_API_KEY`.

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/packages` | List monitored packages (paginated) |
| GET | `/api/v1/packages/{id}` | Package detail |
| GET | `/api/v1/packages/{id}/versions` | Version history |
| GET | `/api/v1/versions/{id}/diff` | Raw diff content |
| GET | `/api/v1/analyses` | Analysis feed (paginated, filterable) |
| GET | `/api/v1/analyses/{id}` | Full analysis detail |
| GET | `/api/v1/analyses/{id}/findings` | Security findings |
| GET | `/api/v1/feed` | Dashboard feed (paginated) |
| GET | `/api/v1/stats` | Monitoring stats |
| POST | `/api/v1/webhooks/poll` | Trigger polling (requires `X-API-Key`) |

---

## How Detection Works

### What Ghost catches (score 5.0+):

- New dependency with <1K weekly downloads that contains install scripts downloading external binaries
- Dependency version bumps where the new version introduces `eval()` with encoded payloads
- Typosquatted package names (e.g., `plain-crypto-js` instead of `crypto-js`)
- Data exfiltration patterns -- code that collects credentials AND sends them to external URLs
- Obfuscated code replacing previously readable source

### What Ghost correctly ignores (score 0.0):

- Dockerfile changes, CI/CD configs, build scripts
- Documentation, tests, README, CHANGELOG updates
- Dependency updates to well-known packages (>10K downloads)
- Version metadata, copyright year changes
- Go module updates, Rust crate updates to standard libraries
- Linter configs, type annotations, refactoring

### The Axios Attack -- How Ghost Would Catch It

On March 31, 2026, attackers hijacked an npm maintainer's account and published `axios@1.14.1` with a malicious dependency `plain-crypto-js@4.2.1`.

Ghost's agent would:
1. Detect the new `axios` version within 60 seconds
2. Diff `1.14.0` vs `1.14.1` -- see the new `plain-crypto-js` dependency
3. Call `lookup_package_info("plain-crypto-js", "npm")` -- see 0 downloads, no repo
4. Call `download_and_list_files("plain-crypto-js", "4.2.1", "npm")` -- find the postinstall script
5. Call `read_file_content()` on the postinstall -- see it downloads a RAT binary
6. Call `scan_for_suspicious_patterns()` -- confirm network calls + process execution
7. Score: **9.5/10 CRITICAL** -- alert fires to Slack immediately

---

## Project Structure

```
ghost/
├── backend/
│   ├── app/
│   │   ├── main.py                  # FastAPI app
│   │   ├── config.py                # Settings
│   │   ├── database.py              # Async SQLAlchemy
│   │   ├── models/                  # ORM models
│   │   ├── schemas/                 # Pydantic schemas
│   │   ├── routers/                 # API endpoints
│   │   ├── services/
│   │   │   ├── registry/            # npm, PyPI, GitHub clients
│   │   │   ├── diff/                # Diff generation
│   │   │   ├── analysis/
│   │   │   │   ├── agent.py         # Security agent (OpenAI Agents SDK)
│   │   │   │   └── pipeline.py      # Analysis orchestrator
│   │   │   ├── ingestion.py         # Poll orchestrator
│   │   │   └── alerting.py          # Slack/webhook dispatch
│   │   └── utils/
│   ├── alembic/                     # DB migrations
│   ├── seed.py                      # Seed 100 packages
│   └── Dockerfile
├── frontend/
│   ├── src/app/                     # Next.js pages
│   ├── src/components/              # React components
│   └── src/lib/                     # API client, types, utils
├── mcp/
│   └── index.js                     # MCP server for AI coding tools
├── docker-compose.yml
└── LICENSE
```

---

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines on how to contribute.

---

## Credits

Built by [Paul Vann](https://x.com/pjvann) at [Validia](https://validia.ai).

Join [FrontierSec](https://join.slack.com/t/frontiersec/shared_invite/zt-3s0tfehvr-Qjqa1w8ITe7O7zZcd_23ag) on Slack for live alerts.

## License

MIT -- see [LICENSE](LICENSE).
