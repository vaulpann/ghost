"""Codex CLI wrapper — runs Codex as a subprocess and captures structured output."""

import asyncio
import json
import logging
import os
import time

from app.config import settings

logger = logging.getLogger(__name__)


async def run_codex(
    prompt: str,
    working_dir: str,
    model: str | None = None,
    timeout_secs: int | None = None,
) -> dict:
    """Run Codex CLI in the given directory and capture output.

    Returns dict with stdout, stderr, exit_code, duration_secs.
    """
    model = model or settings.codex_discovery_model
    timeout = timeout_secs or settings.codex_timeout_secs

    cmd = [
        "codex",
        "--model", model,
        "--approval-mode", "full-auto",
        "--quiet",
        prompt,
    ]

    env = {**os.environ, "OPENAI_API_KEY": settings.openai_api_key}

    logger.info("Running Codex in %s (model=%s, timeout=%ds)", working_dir, model, timeout)
    start = time.time()

    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            cwd=working_dir,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env=env,
        )

        stdout, stderr = await asyncio.wait_for(
            proc.communicate(),
            timeout=timeout,
        )

        duration = time.time() - start

        logger.info(
            "Codex finished: exit=%d, stdout=%d bytes, stderr=%d bytes, duration=%.1fs",
            proc.returncode, len(stdout), len(stderr), duration,
        )

        return {
            "stdout": stdout.decode(errors="replace"),
            "stderr": stderr.decode(errors="replace"),
            "exit_code": proc.returncode,
            "duration_secs": duration,
        }

    except asyncio.TimeoutError:
        duration = time.time() - start
        logger.error("Codex timed out after %.1fs", duration)
        try:
            proc.kill()
        except Exception:
            pass
        return {
            "stdout": "",
            "stderr": f"Codex timed out after {timeout}s",
            "exit_code": -1,
            "duration_secs": duration,
        }
    except Exception as e:
        duration = time.time() - start
        logger.error("Codex failed: %s", e)
        return {
            "stdout": "",
            "stderr": str(e),
            "exit_code": -1,
            "duration_secs": duration,
        }


def parse_json_from_output(output: str) -> dict | None:
    """Extract JSON from Codex output, handling markdown fences and extra text."""
    # Try direct parse first
    try:
        return json.loads(output.strip())
    except json.JSONDecodeError:
        pass

    # Try extracting from markdown code fence
    for fence in ["```json", "```"]:
        if fence in output:
            start = output.index(fence) + len(fence)
            end = output.index("```", start) if "```" in output[start:] else len(output)
            try:
                return json.loads(output[start:end].strip())
            except (json.JSONDecodeError, ValueError):
                pass

    # Try finding the first { ... } block
    brace_start = output.find("{")
    if brace_start >= 0:
        depth = 0
        for i, c in enumerate(output[brace_start:], brace_start):
            if c == "{":
                depth += 1
            elif c == "}":
                depth -= 1
                if depth == 0:
                    try:
                        return json.loads(output[brace_start:i + 1])
                    except json.JSONDecodeError:
                        break

    return None
