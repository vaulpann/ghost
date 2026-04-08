# Ghost Supply Chain Scanner

A GitHub Action that scans your project's dependencies for supply chain attacks, typosquats, and malicious packages using the [Ghost](https://ghost.validia.ai) threat intelligence API.

## Features

- Detects new and changed dependencies in pull requests
- Supports npm, yarn, pnpm, pip, and poetry
- Posts clean PR comments with findings (updates in place, no duplicates)
- Configurable failure thresholds
- Monorepo support (recursive lock file detection)
- Zero external dependencies (runs on Node.js built-ins only)

## Quick Start

```yaml
# .github/workflows/ghost-scan.yml
name: Ghost Supply Chain Scan
on: [pull_request]
jobs:
  scan:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: vaulpann/ghost/github-action@main
        with:
          fail-on: high
```

## Inputs

| Input | Description | Default |
|-------|-------------|---------|
| `api-url` | Ghost API endpoint | `https://ghost-api-495743911277.us-central1.run.app` |
| `fail-on` | Minimum severity to fail the check: `critical`, `high`, `medium`, `none` | `critical` |
| `token` | GitHub token for PR comments | `${{ github.token }}` |

## How It Works

1. **Detects lock files** in your repository (up to 3 directories deep)
2. **Parses dependencies** from package-lock.json, yarn.lock, pnpm-lock.yaml, requirements.txt, Pipfile.lock, or poetry.lock
3. **Diffs against base branch** (on PRs) to identify new or changed dependencies
4. **Sends dependencies to Ghost API** for threat analysis
5. **Reports findings** via GitHub Actions summary and PR comments

## Supported Ecosystems

| Ecosystem | Lock File |
|-----------|-----------|
| npm | `package-lock.json` |
| yarn | `yarn.lock` |
| pnpm | `pnpm-lock.yaml` |
| pip | `requirements.txt` |
| pipenv | `Pipfile.lock` |
| poetry | `poetry.lock` |

## Examples

### Fail on high severity or above

```yaml
- uses: vaulpann/ghost/github-action@main
  with:
    fail-on: high
```

### Never fail, just report

```yaml
- uses: vaulpann/ghost/github-action@main
  with:
    fail-on: none
```

### Custom API endpoint (self-hosted Ghost)

```yaml
- uses: vaulpann/ghost/github-action@main
  with:
    api-url: https://ghost.internal.company.com
```

## PR Comment

When issues are found, the action posts a comment on the PR:

> ## Ghost Supply Chain Scan
>
> **1 issue found** in 45 dependencies
>
> | Package | Version | Risk | Issue |
> |---------|---------|------|-------|
> | evil-pkg | 1.0.0 | Critical | Only 3 weekly downloads, postinstall script |

If no issues are found, only a green check appears in the Actions summary -- no noisy comments.

---

*Powered by [Ghost](https://ghost.validia.ai) -- Supply Chain Threat Intelligence by Validia*
