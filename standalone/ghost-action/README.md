# Ghost Supply Chain Scan

Ghost scans pull requests for risky dependency changes. It detects new npm and Python dependencies, reviews version updates, and posts a per-package analysis summary directly on the PR.

This directory is structured to be copied into its own public repository, such as `vaulpann/ghost-action`, and published from there.

## What It Does

- Detects changed dependency lockfiles recursively in monorepos
- Scans only new or updated dependencies
- Supports npm (`package-lock.json`, `yarn.lock`, `pnpm-lock.yaml`) and Python (`requirements.txt`, `Pipfile.lock`, `poetry.lock`)
- Reviews new packages by pulling package source
- Reviews updates by diffing the previous and new package versions
- Posts a PR comment with a 1-2 sentence analysis for each changed dependency
- Fails the check only when results meet your configured severity threshold

## Usage

```yaml
name: Ghost Supply Chain Scan

on:
  pull_request:

jobs:
  scan:
    runs-on: ubuntu-latest
    permissions:
      contents: read
      pull-requests: write
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0
      - uses: vaulpann/ghost-action@v1
        with:
          fail-on: high
```

## Inputs

| Input | Description | Default |
|---|---|---|
| `api-url` | Ghost API endpoint | `https://ghost-api-495743911277.us-central1.run.app` |
| `fail-on` | Minimum severity that fails the job: `critical`, `high`, `medium`, `none` | `high` |
| `token` | GitHub token used to update PR comments | `${{ github.token }}` |

## Behavior

- If a PR does not change any supported dependency files, Ghost exits cleanly.
- If supported lockfiles changed but no dependencies changed relative to the base branch, Ghost reports `No new or changed dependencies to scan.`
- If dependencies changed, Ghost posts a PR comment with one row per changed dependency.
- Clean dependencies still get a short analysis summary so reviewers can see that code or version diff inspection actually ran.
- The job fails only when at least one result meets the `fail-on` threshold.

## Example Output

```md
## 🔍 Ghost Supply Chain Scan

0 concerns found in 2 changed dependencies

| Package | Version | Risk | Analysis |
|---------|---------|------|----------|
| lodash | 4.17.21 | 🔵 Low | The lodash package version 4.17.21 does not contain any install scripts, obfuscated code, or suspicious outbound network calls. |
| zod | 3.23.8 -> 3.25.76 | 🔵 Low | The changes in the package primarily involve updates to the license and README files, with no new install scripts, obfuscated code, or suspicious network calls. |
```

## Supported Files

- `package-lock.json`
- `yarn.lock`
- `pnpm-lock.yaml`
- `requirements.txt`
- `Pipfile.lock`
- `poetry.lock`

## Publishing

This action is intended to be published from its own repository. See [PUBLISHING.md](./PUBLISHING.md) for the exact repo layout and release steps.

## License

MIT
