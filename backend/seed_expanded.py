"""Expanded seed: add ~500 new packages to production (keeps existing 100)."""

import asyncio
import logging

from sqlalchemy import text, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import async_session, engine
from app.models.package import Package
from app.services.registry.npm import NpmClient
from app.services.registry.pypi import PyPIClient
from app.services.registry.github import GitHubClient

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
logger = logging.getLogger(__name__)

NPM_PACKAGES = [
    "through2", "readable-stream", "graceful-fs", "inherits", "isarray",
    "string_decoder", "safe-buffer", "process-nextick-args", "util-deprecate", "core-util-is",
    "once", "wrappy", "inflight", "path-is-absolute", "balanced-match",
    "brace-expansion", "concat-map", "minimatch", "lru-cache", "yallist",
    "ms", "supports-color", "has-flag", "color-convert", "color-name",
    "ansi-styles", "escape-string-regexp", "strip-ansi", "ansi-regex", "wrap-ansi",
    "string-width", "emoji-regex", "is-fullwidth-code-point", "strip-json-comments", "kind-of",
    "resolve", "path-parse", "is-core-module", "has", "function-bind",
    "define-properties", "object-keys", "es-abstract", "call-bind", "get-intrinsic",
    "has-symbols", "has-property-descriptors", "gopd", "side-channel", "set-function-length",
    "define-data-property", "has-proto", "object.assign", "regexp.prototype.flags", "es-to-primitive",
    "is-callable", "is-date-object", "is-symbol", "is-regex", "which",
    "isexe", "cross-spawn", "shebang-command", "shebang-regex", "path-key",
    "signal-exit", "mimic-fn", "onetime", "strip-final-newline", "npm-run-path",
    "execa", "human-signals", "merge-stream", "is-stream", "p-limit",
    "p-locate", "p-try", "yocto-queue", "locate-path", "path-exists",
    "find-up", "source-map", "source-map-js", "source-map-support", "nanoid",
    "picocolors", "postcss", "autoprefixer", "browserslist", "caniuse-lite",
    "electron-to-chromium", "node-releases", "update-browserslist-db", "acorn", "acorn-jsx",
    "esutils", "estraverse", "esrecurse", "esprima", "json5",
    "picomatch", "micromatch", "braces", "fill-range", "to-regex-range",
    "is-number", "fast-glob", "glob-parent", "fastq", "reusify",
    "run-parallel", "queue-microtask", "@nodelib/fs.stat", "@nodelib/fs.walk", "@nodelib/fs.scandir",
    "fast-deep-equal", "ajv", "uri-js", "json-schema-traverse", "punycode",
    "optionator", "levn", "type-check", "prelude-ls", "deep-is",
    "word-wrap", "flat-cache", "flatted", "keyv", "json-buffer",
    "espree", "globals", "type-fest", "esquery", "file-entry-cache",
    "imurmurhash", "natural-compare", "text-table", "@eslint/eslintrc", "@eslint/js",
    "eslint-scope", "eslint-visitor-keys", "@types/node", "@types/react", "@types/react-dom",
    "@typescript-eslint/parser", "@typescript-eslint/eslint-plugin",
    "eslint-plugin-react", "eslint-plugin-react-hooks", "eslint-plugin-import",
    "eslint-plugin-jsx-a11y", "eslint-config-prettier", "eslint-plugin-prettier",
    "@babel/core", "@babel/parser", "@babel/traverse", "@babel/generator",
    "@babel/types", "@babel/template", "@babel/helpers",
    "@babel/helper-validator-identifier", "@babel/helper-string-parser",
    "@babel/highlight", "@babel/code-frame",
    "@babel/preset-env", "@babel/preset-react", "@babel/preset-typescript",
    "@babel/plugin-transform-runtime", "@babel/runtime", "regenerator-runtime",
    "next", "@next/env", "sass", "less",
    "webpack-cli", "webpack-dev-server", "html-webpack-plugin",
    "css-loader", "style-loader", "mini-css-extract-plugin",
    "babel-loader", "ts-loader", "terser-webpack-plugin", "terser",
    "esbuild", "rollup", "@rollup/plugin-node-resolve", "@rollup/plugin-commonjs",
    "jest", "ts-jest", "mocha", "chai", "sinon", "vitest",
    "@testing-library/react", "@testing-library/jest-dom", "cypress",
]

PYPI_PACKAGES = [
    "awscli", "google-api-core", "google-auth", "google-cloud-storage", "google-cloud-core",
    "googleapis-common-protos", "protobuf", "grpcio", "grpcio-status", "grpcio-tools",
    "cachetools", "pyasn1-modules", "oauthlib", "requests-oauthlib", "google-auth-oauthlib",
    "google-auth-httplib2", "google-api-python-client", "google-cloud-bigquery",
    "google-cloud-pubsub", "google-cloud-logging",
    "azure-core", "azure-storage-blob", "azure-identity", "azure-common",
    "pyarrow", "fsspec", "s3fs", "filelock", "platformdirs",
    "importlib-metadata", "importlib-resources", "zipp", "tomli", "toml",
    "exceptiongroup", "iniconfig", "pluggy", "pyparsing", "docutils",
    "pygments", "babel", "chardet", "multidict", "yarl",
    "frozenlist", "aiosignal", "async-timeout",
    "uvloop", "httpcore", "httpx", "httplib2", "httptools",
    "h11", "anyio", "sniffio", "starlette", "uvicorn",
    "gunicorn", "celery", "kombu", "billiard", "amqp",
    "vine", "redis", "pymongo", "psycopg2-binary",
    "pymysql", "sqlparse", "alembic", "mako",
    "wrapt", "decorator", "deprecated", "tenacity",
    "backoff", "more-itertools", "toolz",
    "pytz", "tzdata", "python-dotenv",
    "pycparser", "pre-commit", "tox", "virtualenv",
    "distlib", "poetry-core", "build", "flit-core", "hatchling",
    "setuptools-scm", "twine",
    "rich", "typer", "tqdm",
    "tabulate", "wcwidth", "prompt-toolkit",
    "paramiko", "fabric", "invoke", "pynacl", "bcrypt",
    "passlib", "itsdangerous", "pyopenssl", "pycryptodome",
    "msgpack", "ujson", "orjson", "simplejson",
    "jsonschema", "jsonschema-specifications", "referencing", "rpds-py",
    "pydantic-core", "annotated-types", "email-validator", "python-multipart",
    "dnspython", "websocket-client", "websockets",
    "mock", "responses", "factory-boy", "faker",
    "hypothesis", "pytest-mock", "pytest-asyncio", "pytest-xdist", "pytest-django",
    "mypy", "mypy-extensions", "ruff", "black", "isort",
    "flake8", "pylint", "pyflakes", "pycodestyle", "bandit",
    "sphinx", "nbconvert", "nbformat", "jupyter-core", "jupyter-client",
    "ipython", "ipykernel", "notebook", "jupyterlab",
    "traitlets", "tornado", "pyzmq", "nest-asyncio",
    "sympy", "networkx", "statsmodels", "xgboost", "lightgbm",
    "transformers", "tokenizers", "huggingface-hub", "safetensors", "datasets",
    "accelerate", "keras", "tensorboard",
    "numba", "llvmlite", "dask", "joblib", "threadpoolctl",
    "psutil", "docker", "kubernetes", "smart-open",
]

GITHUB_REPOS = [
    "kubernetes/kubernetes", "hashicorp/terraform", "hashicorp/vault",
    "hashicorp/consul", "hashicorp/nomad", "hashicorp/packer",
    "docker/compose", "moby/moby", "containerd/containerd",
    "opencontainers/runc", "prometheus/prometheus", "grafana/grafana",
    "argoproj/argo-cd", "helm/helm", "istio/istio",
    "linkerd/linkerd2", "cilium/cilium", "etcd-io/etcd",
    "fluxcd/flux2", "cert-manager/cert-manager",
    "traefik/traefik", "envoyproxy/envoy", "caddyserver/caddy",
    "coredns/coredns", "minio/minio", "rancher/rancher",
    "k3s-io/k3s", "derailed/k9s",
    "aquasecurity/trivy", "anchore/grype", "anchore/syft",
    "sigstore/cosign", "open-policy-agent/opa", "falcosecurity/falco",
    "golang/go", "rust-lang/rust", "denoland/deno",
    "oven-sh/bun", "ziglang/zig",
    "protocolbuffers/protobuf", "grpc/grpc", "bufbuild/buf",
    "cli/cli", "junegunn/fzf", "BurntSushi/ripgrep",
    "sharkdp/bat", "sharkdp/fd", "sharkdp/hyperfine",
    "stedolan/jq", "mikefarah/yq", "direnv/direnv",
    "starship/starship", "ajeetdsouza/zoxide",
    "jesseduffield/lazygit", "jesseduffield/lazydocker",
    "neovim/neovim", "helix-editor/helix",
    "alacritty/alacritty", "FiloSottile/age", "FiloSottile/mkcert",
    "tailscale/tailscale", "cloudflare/cloudflared",
    "gravitational/teleport", "pulumi/pulumi",
    "crossplane/crossplane", "goreleaser/goreleaser",
    "nats-io/nats-server", "goharbor/harbor",
    "cockroachdb/cockroach", "influxdata/influxdb",
    "VictoriaMetrics/VictoriaMetrics", "jaegertracing/jaeger",
    "open-telemetry/opentelemetry-collector",
    "kubernetes-sigs/kustomize", "kubernetes-sigs/kind",
]

# Critical packages get critical priority
NPM_CRITICAL = {
    "next", "@babel/core", "postcss", "esbuild", "rollup", "jest", "vitest", "cypress",
    "acorn", "browserslist", "terser", "cross-spawn", "execa", "readable-stream",
}
PYPI_CRITICAL = {
    "awscli", "google-auth", "protobuf", "grpcio", "celery", "redis", "gunicorn", "uvicorn",
    "transformers", "keras", "tensorboard", "docker", "kubernetes", "httpx", "starlette",
    "alembic", "pyopenssl", "bandit", "jsonschema",
}
GITHUB_CRITICAL = {
    "kubernetes/kubernetes", "hashicorp/terraform", "hashicorp/vault", "docker/compose",
    "prometheus/prometheus", "grafana/grafana", "helm/helm", "golang/go", "rust-lang/rust",
    "denoland/deno", "oven-sh/bun", "protocolbuffers/protobuf", "cli/cli",
    "containerd/containerd", "envoyproxy/envoy", "traefik/traefik",
}


async def seed_npm(db: AsyncSession):
    client = NpmClient()
    sem = asyncio.Semaphore(8)
    added = 0
    skipped = 0

    async def fetch_and_insert(name: str):
        nonlocal added, skipped
        async with sem:
            # Skip if exists
            existing = await db.execute(
                select(Package).where(Package.registry == "npm", Package.name == name)
            )
            if existing.scalar_one_or_none():
                skipped += 1
                return

            try:
                metadata = await client.get_package_metadata(name)
                latest = await client.get_latest_version(name)
                priority = "critical" if name in NPM_CRITICAL else "high"

                pkg = Package(
                    name=name,
                    registry="npm",
                    registry_url=f"https://www.npmjs.com/package/{name}",
                    repository_url=metadata.repository_url,
                    description=metadata.description,
                    latest_known_version=latest.version,
                    monitoring_enabled=True,
                    priority=priority,
                    weekly_downloads=metadata.weekly_downloads,
                )
                db.add(pkg)
                added += 1
                logger.info("  npm %-40s %10s  [%s]", name, latest.version, priority)
            except Exception as e:
                logger.error("  npm %-40s FAILED: %s", name, e)

    logger.info("Seeding %d npm packages...", len(NPM_PACKAGES))
    for name in NPM_PACKAGES:
        await fetch_and_insert(name)
    await db.commit()
    logger.info("npm: added %d, skipped %d", added, skipped)


async def seed_pypi(db: AsyncSession):
    client = PyPIClient()
    sem = asyncio.Semaphore(8)
    added = 0
    skipped = 0

    async def fetch_and_insert(name: str):
        nonlocal added, skipped
        async with sem:
            existing = await db.execute(
                select(Package).where(Package.registry == "pypi", Package.name == name)
            )
            if existing.scalar_one_or_none():
                skipped += 1
                return

            try:
                metadata = await client.get_package_metadata(name)
                latest = await client.get_latest_version(name)
                priority = "critical" if name in PYPI_CRITICAL else "high"

                pkg = Package(
                    name=name,
                    registry="pypi",
                    registry_url=f"https://pypi.org/project/{name}/",
                    repository_url=metadata.repository_url,
                    description=metadata.description,
                    latest_known_version=latest.version,
                    monitoring_enabled=True,
                    priority=priority,
                    weekly_downloads=metadata.weekly_downloads,
                )
                db.add(pkg)
                added += 1
                logger.info("  pypi %-40s %10s  [%s]", name, latest.version, priority)
            except Exception as e:
                logger.error("  pypi %-40s FAILED: %s", name, e)

    logger.info("Seeding %d PyPI packages...", len(PYPI_PACKAGES))
    for name in PYPI_PACKAGES:
        await fetch_and_insert(name)
    await db.commit()
    logger.info("pypi: added %d, skipped %d", added, skipped)


async def seed_github(db: AsyncSession):
    client = GitHubClient()
    sem = asyncio.Semaphore(5)
    added = 0
    skipped = 0

    async def fetch_and_insert(repo: str):
        nonlocal added, skipped
        async with sem:
            existing = await db.execute(
                select(Package).where(Package.registry == "github", Package.name == repo)
            )
            if existing.scalar_one_or_none():
                skipped += 1
                return

            try:
                metadata = await client.get_package_metadata(repo)
                priority = "critical" if repo in GITHUB_CRITICAL else "high"

                latest_version = None
                try:
                    latest = await client.get_latest_version(repo)
                    latest_version = latest.version
                except Exception:
                    pass  # Some repos don't use GitHub Releases

                pkg = Package(
                    name=repo,
                    registry="github",
                    registry_url=f"https://github.com/{repo}",
                    repository_url=f"https://github.com/{repo}",
                    description=metadata.description,
                    latest_known_version=latest_version,
                    monitoring_enabled=True,
                    priority=priority,
                    weekly_downloads=metadata.weekly_downloads,  # stars as proxy
                )
                db.add(pkg)
                added += 1
                logger.info("  github %-40s %10s  [%s]", repo, latest_version or "no-releases", priority)
            except Exception as e:
                logger.error("  github %-40s FAILED: %s", repo, e)

    logger.info("Seeding %d GitHub repos...", len(GITHUB_REPOS))
    for repo in GITHUB_REPOS:
        await fetch_and_insert(repo)
    await db.commit()
    logger.info("github: added %d, skipped %d", added, skipped)


async def main():
    logger.info("=== Ghost Expanded Seed ===")
    async with async_session() as db:
        await seed_npm(db)
        await seed_pypi(db)
        await seed_github(db)

    async with async_session() as db:
        result = await db.execute(text("SELECT COUNT(*) FROM packages"))
        count = result.scalar()
        logger.info("=== Done: %d total packages ===", count)

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
