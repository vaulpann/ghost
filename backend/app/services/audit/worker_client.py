"""HTTP client for communicating with the audit worker VM."""

import logging

import httpx

from app.config import settings

logger = logging.getLogger(__name__)


class AuditWorkerClient:
    def __init__(self):
        self.base_url = settings.audit_worker_url
        self.headers = {"X-Worker-Key": settings.audit_worker_api_key}

    async def submit_audit(
        self,
        audit_id: str,
        package_name: str,
        registry: str,
        version: str,
        tarball_url: str | None = None,
        callback_url: str | None = None,
    ) -> dict:
        """Submit an audit request to the worker VM. Returns immediately."""
        if not self.base_url:
            raise ValueError("AUDIT_WORKER_URL not configured")

        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                f"{self.base_url}/audit",
                json={
                    "audit_id": audit_id,
                    "package_name": package_name,
                    "registry": registry,
                    "version": version,
                    "tarball_url": tarball_url,
                    "callback_url": callback_url,
                },
                headers=self.headers,
            )
            resp.raise_for_status()
            return resp.json()

    async def get_audit_status(self, audit_id: str) -> dict:
        """Poll the worker for audit status."""
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(
                f"{self.base_url}/audit/{audit_id}/status",
                headers=self.headers,
            )
            resp.raise_for_status()
            return resp.json()

    async def is_healthy(self) -> bool:
        """Check if the worker VM is reachable."""
        if not self.base_url:
            return False
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.get(f"{self.base_url}/health")
                return resp.status_code == 200
        except Exception:
            return False
