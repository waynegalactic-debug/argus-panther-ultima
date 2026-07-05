"""Cloudflare Pages integration for dashboard deployment.

Deploys the ARGUS-PANTHER interactive radar dashboard to Cloudflare Pages,
enabling global edge distribution with automatic SSL, instant cache
invalidation, and custom domain support.
"""

from __future__ import annotations

import json
import logging
import zipfile
from datetime import datetime, timezone
from io import BytesIO
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)
ACCOUNT_ID: str = "ac0c08179402a581538ae0c886121040"


class CloudflareDashboardDeployer:
    """Manages deployment of the ARGUS-PANTHER dashboard to Cloudflare Pages."""

    def __init__(self) -> None:
        self.account_id: str = ACCOUNT_ID
        logger.info("CloudflareDashboardDeployer initialised")

    async def _mcp_search(self, code: str) -> Any:
        tool_func = globals().get("mcp__plugin-cloudflare_cloudflare__search")
        if tool_func is None:
            return {"success": False, "errors": ["search tool unavailable"]}
        return await tool_func(code=code)

    async def _mcp_execute(self, code: str) -> Any:
        tool_func = globals().get("mcp__plugin-cloudflare_cloudflare__execute")
        if tool_func is None:
            return {"success": False, "errors": ["execute tool unavailable"]}
        return await tool_func(code=code, account_id=self.account_id)

    async def _ensure_project(self, project_name: str) -> bool:
        logger.debug("Ensuring Pages project: %s", project_name)
        code = f"""
async () => {{
  return cloudflare.request({{
    method: "GET",
    path: `/accounts/{self.account_id}/pages/projects/{project_name}`,
  }});
}}
"""
        result = await self._mcp_execute(code)
        if isinstance(result, dict) and result.get("success", False):
            return True
        code = f"""
async () => {{
  return cloudflare.request({{
    method: "POST",
    path: `/accounts/{self.account_id}/pages/projects`,
    body: {{"name": "{project_name}", "production_branch": "main"}},
  }});
}}
"""
        result = await self._mcp_execute(code)
        return isinstance(result, dict) and result.get("success", False)

    def _bundle_html(self, html_content: str) -> bytes:
        buf = BytesIO()
        with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
            zf.writestr("index.html", html_content)
            zf.writestr("_headers", """/*
  X-Frame-Options: DENY
  X-Content-Type-Options: nosniff
  Referrer-Policy: strict-origin-when-cross-origin
""")
        return buf.getvalue()

    async def deploy_dashboard(self, html_content: str, project_name: str = "argus-panther-dashboard") -> str:
        logger.info("Deploying dashboard to Pages project: %s", project_name)
        await self._ensure_project(project_name)
        zip_bytes = self._bundle_html(html_content)
        boundary = f"----PagesDeployBoundary{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}"
        code = f"""
async () => {{
  const zipData = new Uint8Array({list(zip_bytes)});
  return cloudflare.request({{
    method: "POST",
    path: `/accounts/{self.account_id}/pages/projects/{project_name}/deployments`,
    body: zipData,
    contentType: "application/zip",
    rawBody: true,
  }});
}}
"""
        result = await self._mcp_execute(code)
        if isinstance(result, dict) and result.get("success", False):
            deploy_data = result.get("result", {})
            return deploy_data.get("url", f"https://{project_name}.pages.dev")
        return f"https://{project_name}.pages.dev"

    async def update_dashboard(self, project_name: str, html_content: str) -> str:
        logger.info("Updating dashboard: %s", project_name)
        return await self.deploy_dashboard(html_content, project_name)

    async def get_deployment_status(self, project_name: str) -> Dict[str, Any]:
        code = f"""
async () => {{
  return cloudflare.request({{
    method: "GET",
    path: `/accounts/{self.account_id}/pages/projects/{project_name}/deployments`,
  }});
}}
"""
        result = await self._mcp_execute(code)
        if isinstance(result, dict) and "result" in result:
            deployments = result["result"]
            if isinstance(deployments, list) and len(deployments) > 0:
                latest = deployments[0]
                return {
                    "project_name": project_name,
                    "url": f"https://{project_name}.pages.dev",
                    "status": latest.get("deployment_stage", {}).get("name", "unknown"),
                    "latest_deployment": {"id": latest.get("id"), "created_on": latest.get("created_on")},
                    "environment": latest.get("environment", "production"),
                }
        return {"project_name": project_name, "url": f"https://{project_name}.pages.dev", "status": "unknown"}

    async def create_custom_domain(self, project_name: str, domain: str) -> bool:
        logger.info("Attaching custom domain '%s' to project '%s'", domain, project_name)
        code = f"""
async () => {{
  return cloudflare.request({{
    method: "POST",
    path: `/accounts/{self.account_id}/pages/projects/{project_name}/domains`,
    body: {{"name": "{domain}"}},
  }});
}}
"""
        result = await self._mcp_execute(code)
        return isinstance(result, dict) and result.get("success", False)
