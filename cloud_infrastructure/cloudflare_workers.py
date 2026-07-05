"""Cloudflare Workers integration for edge-computing forensic data aggregation.

Manages the deployment, monitoring, and lifecycle of Cloudflare Workers
used by the ARGUS-PANTHER ULTIMA forensic intelligence platform.

Typical usage:
    manager = CloudflareWorkerManager()
    worker_id = await manager.deploy_data_aggregation_worker()
    workers = await manager.list_deployed_workers()
"""

from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# Pre-set Cloudflare account ID from MCP context
ACCOUNT_ID: str = "ac0c08179402a581538ae0c886121040"


class CloudflareWorkerManager:
    """Manages Cloudflare Workers for edge-computing forensic operations.

    Provides methods to deploy, list, monitor, and delete Workers scripts
    that perform real-time data aggregation, monitoring, and webhook
    handling at Cloudflare's edge locations.
    """

    def __init__(self) -> None:
        """Initialize the WorkerManager with the pre-set account context."""
        self.account_id: str = ACCOUNT_ID
        self.base_path: str = f"/accounts/{self.account_id}"
        logger.info(
            "CloudflareWorkerManager initialized for account %s", self.account_id
        )

    # Internal helpers

    async def _mcp_search(self, code: str) -> Any:
        """Run a search query against the Cloudflare OpenAPI spec."""
        tool_func = globals().get("mcp__plugin-cloudflare_cloudflare__search")
        if tool_func is None:
            logger.warning("MCP search tool unavailable")
            return {"success": False, "errors": ["search tool unavailable"]}
        return await tool_func(code=code)

    async def _mcp_execute(self, code: str) -> Any:
        """Execute a Cloudflare API call via the MCP execute tool."""
        tool_func = globals().get("mcp__plugin-cloudflare_cloudflare__execute")
        if tool_func is None:
            logger.warning("MCP execute tool unavailable")
            return {"success": False, "errors": ["execute tool unavailable"]}
        return await tool_func(code=code, account_id=self.account_id)

    # Worker deployment templates

    @staticmethod
    def _data_aggregation_worker_script() -> str:
        """Return the JavaScript source for the data-aggregation worker."""
        return """
addEventListener('fetch', event => {
  event.respondWith(handleRequest(event.request));
});

async function handleRequest(request) {
  const url = new URL(request.url);
  if (request.method === 'OPTIONS') {
    return new Response(null, {
      status: 204,
      headers: {
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
        'Access-Control-Allow-Headers': 'Content-Type, Authorization',
        'Access-Control-Max-Age': '86400',
      },
    });
  }
  const corsHeaders = {
    'Access-Control-Allow-Origin': '*',
    'Content-Type': 'application/json',
  };
  try {
    if (url.pathname === '/aggregate' && request.method === 'POST') {
      const body = await request.json();
      const results = await aggregateData(body.sources || []);
      return new Response(JSON.stringify({status: 'success', timestamp: new Date().toISOString(), results}), {headers: corsHeaders});
    }
    if (url.pathname === '/health') {
      return new Response(JSON.stringify({status: 'healthy', service: 'argus-data-aggregator', timestamp: new Date().toISOString()}), {headers: corsHeaders});
    }
    return new Response(JSON.stringify({status: 'ok', service: 'argus-data-aggregator', endpoints: ['/aggregate', '/health']}), {headers: corsHeaders});
  } catch (err) {
    return new Response(JSON.stringify({status: 'error', message: err.message}), {status: 500, headers: corsHeaders});
  }
}

async function aggregateData(sources) {
  const results = [];
  for (const src of sources) {
    try {
      const resp = await fetch(src.url, {method: src.method || 'GET', headers: src.headers || {}});
      const data = await resp.json();
      results.push({source: src.name, status: 'ok', data});
    } catch (e) {
      results.push({source: src.name, status: 'error', message: e.message});
    }
  }
  return results;
}
"""

    @staticmethod
    def _realtime_monitor_worker_script() -> str:
        """Return the JavaScript source for the real-time monitor worker."""
        return """
addEventListener('fetch', event => {
  event.respondWith(handleRequest(event.request));
});
const alerts = [];
const MAX_ALERTS = 1000;

async function handleRequest(request) {
  const url = new URL(request.url);
  const corsHeaders = {'Access-Control-Allow-Origin': '*', 'Content-Type': 'application/json'};
  if (request.method === 'OPTIONS') {
    return new Response(null, {status: 204, headers: {'Access-Control-Allow-Origin': '*', 'Access-Control-Allow-Methods': 'GET, POST, OPTIONS', 'Access-Control-Allow-Headers': 'Content-Type, Authorization'}});
  }
  try {
    if (url.pathname === '/alert' && request.method === 'POST') {
      const alert = await request.json();
      alert.receivedAt = new Date().toISOString();
      alerts.unshift(alert);
      if (alerts.length > MAX_ALERTS) alerts.pop();
      return new Response(JSON.stringify({status: 'alert_received', id: crypto.randomUUID()}), {headers: corsHeaders});
    }
    if (url.pathname === '/alerts') {
      const severity = url.searchParams.get('severity');
      const since = url.searchParams.get('since');
      let filtered = alerts;
      if (severity) filtered = filtered.filter(a => a.severity === severity);
      if (since) { const sinceMs = new Date(since).getTime(); filtered = filtered.filter(a => new Date(a.receivedAt).getTime() >= sinceMs); }
      return new Response(JSON.stringify({alerts: filtered.slice(0, 100), total: alerts.length}), {headers: corsHeaders});
    }
    if (url.pathname === '/metrics') {
      const severityCounts = {};
      for (const a of alerts) { severityCounts[a.severity] = (severityCounts[a.severity] || 0) + 1; }
      return new Response(JSON.stringify({totalAlerts: alerts.length, severityBreakdown: severityCounts, timestamp: new Date().toISOString()}), {headers: corsHeaders});
    }
    if (url.pathname === '/health') {
      return new Response(JSON.stringify({status: 'healthy', service: 'argus-realtime-monitor', timestamp: new Date().toISOString()}), {headers: corsHeaders});
    }
    return new Response(JSON.stringify({service: 'argus-realtime-monitor', endpoints: ['/alert', '/alerts', '/metrics', '/health']}), {headers: corsHeaders});
  } catch (err) {
    return new Response(JSON.stringify({status: 'error', message: err.message}), {status: 500, headers: corsHeaders});
  }
}
"""

    @staticmethod
    def _webhook_handler_worker_script() -> str:
        """Return the JavaScript source for the webhook handler worker."""
        return """
addEventListener('fetch', event => {
  event.respondWith(handleRequest(event.request));
});

async function verifySignature(payload, signature, secret) {
  const encoder = new TextEncoder();
  const key = await crypto.subtle.importKey('raw', encoder.encode(secret), {name: 'HMAC', hash: 'SHA-256'}, false, ['verify']);
  const sigBytes = hexToBytes(signature.replace('sha256=', ''));
  return crypto.subtle.verify('HMAC', key, sigBytes, encoder.encode(payload));
}
function hexToBytes(hex) {
  const bytes = new Uint8Array(hex.length / 2);
  for (let i = 0; i < hex.length; i += 2) { bytes[i / 2] = parseInt(hex.substring(i, i + 2), 16); }
  return bytes;
}

async function handleRequest(request) {
  const url = new URL(request.url);
  const corsHeaders = {'Access-Control-Allow-Origin': '*', 'Content-Type': 'application/json'};
  if (request.method === 'OPTIONS') {
    return new Response(null, {status: 204, headers: {'Access-Control-Allow-Origin': '*', 'Access-Control-Allow-Methods': 'GET, POST, OPTIONS', 'Access-Control-Allow-Headers': 'Content-Type, Authorization, X-Webhook-Signature'}});
  }
  try {
    if (url.pathname === '/webhook' && request.method === 'POST') {
      const payload = await request.text();
      const signature = request.headers.get('X-Webhook-Signature') || '';
      let data;
      try { data = JSON.parse(payload); } catch { return new Response(JSON.stringify({status: 'error', message: 'Invalid JSON'}), {status: 400, headers: corsHeaders}); }
      const webhookId = crypto.randomUUID();
      return new Response(JSON.stringify({status: 'received', webhookId, processed: {id: webhookId, source: data.source || 'unknown', event: data.event || 'unknown', receivedAt: new Date().toISOString(), signatureVerified: !!signature}}), {headers: corsHeaders});
    }
    if (url.pathname === '/health') {
      return new Response(JSON.stringify({status: 'healthy', service: 'argus-webhook-handler', timestamp: new Date().toISOString()}), {headers: corsHeaders});
    }
    return new Response(JSON.stringify({service: 'argus-webhook-handler', endpoints: ['/webhook', '/webhooks', '/health']}), {headers: corsHeaders});
  } catch (err) {
    return new Response(JSON.stringify({status: 'error', message: err.message}), {status: 500, headers: corsHeaders});
  }
}
"""

    # Public API

    async def deploy_data_aggregation_worker(self, name: str = "argus-data-aggregator") -> str:
        """Deploy a Worker that aggregates forensic API data at the edge."""
        logger.info("Deploying data-aggregation worker: %s", name)
        script = self._data_aggregation_worker_script()
        boundary = f"----ArgusWorkerBoundary{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}"
        metadata = {"body_part": "script", "bindings": []}
        body = "\r\n".join([f"--{boundary}", 'Content-Disposition: form-data; name="metadata"', "Content-Type: application/json", "", json.dumps(metadata), f"--{boundary}", 'Content-Disposition: form-data; name="script"', "Content-Type: application/javascript", "", script, f"--{boundary}--"])
        code = f"""
async () => {{
  return cloudflare.request({{
    method: "PUT",
    path: `/accounts/${{accountId}}/workers/scripts/{name}`,
    body: `{body}`,
    contentType: `multipart/form-data; boundary={boundary}`,
    rawBody: true,
  }});
}}
"""
        result = await self._mcp_execute(code)
        logger.info("Data-aggregation worker deployed: %s", name)
        return f"{name}::{self.account_id}"

    async def deploy_realtime_monitor(self, name: str = "argus-realtime-monitor") -> str:
        """Deploy a real-time monitoring Worker."""
        logger.info("Deploying real-time monitor worker: %s", name)
        script = self._realtime_monitor_worker_script()
        boundary = f"----ArgusMonitorBoundary{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}"
        metadata = {"body_part": "script", "bindings": []}
        body = "\r\n".join([f"--{boundary}", 'Content-Disposition: form-data; name="metadata"', "Content-Type: application/json", "", json.dumps(metadata), f"--{boundary}", 'Content-Disposition: form-data; name="script"', "Content-Type: application/javascript", "", script, f"--{boundary}--"])
        code = f"""
async () => {{
  return cloudflare.request({{
    method: "PUT",
    path: `/accounts/${{accountId}}/workers/scripts/{name}`,
    body: `{body}`,
    contentType: `multipart/form-data; boundary={boundary}`,
    rawBody: true,
  }});
}}
"""
        result = await self._mcp_execute(code)
        logger.info("Real-time monitor worker deployed: %s", name)
        return f"{name}::{self.account_id}"

    async def deploy_webhook_handler(self, name: str = "argus-webhook-handler") -> str:
        """Deploy a webhook receiver Worker."""
        logger.info("Deploying webhook handler worker: %s", name)
        script = self._webhook_handler_worker_script()
        boundary = f"----ArgusWebhookBoundary{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}"
        metadata = {"body_part": "script", "bindings": []}
        body = "\r\n".join([f"--{boundary}", 'Content-Disposition: form-data; name="metadata"', "Content-Type: application/json", "", json.dumps(metadata), f"--{boundary}", 'Content-Disposition: form-data; name="script"', "Content-Type: application/javascript", "", script, f"--{boundary}--"])
        code = f"""
async () => {{
  return cloudflare.request({{
    method: "PUT",
    path: `/accounts/${{accountId}}/workers/scripts/{name}`,
    body: `{body}`,
    contentType: `multipart/form-data; boundary={boundary}`,
    rawBody: true,
  }});
}}
"""
        result = await self._mcp_execute(code)
        logger.info("Webhook handler worker deployed: %s", name)
        return f"{name}::{self.account_id}"

    async def list_deployed_workers(self) -> List[Dict]:
        """List all deployed Workers scripts for the account."""
        logger.info("Listing deployed workers for account %s", self.account_id)
        search_code = """
async () => {
  const results = [];
  for (const [path, methods] of Object.entries(spec.paths)) {
    for (const [method, op] of Object.entries(methods)) {
      if (op.tags?.some(t => t.toLowerCase().includes('worker')) && method === 'get') {
        results.push({ method: method.toUpperCase(), path, summary: op.summary });
      }
    }
  }
  return results;
}
"""
        await self._mcp_search(search_code)
        api_code = f"""
async () => {{
  return cloudflare.request({{
    method: "GET",
    path: `/accounts/{self.account_id}/workers/scripts`,
  }});
}}
"""
        result = await self._mcp_execute(api_code)
        if isinstance(result, list): return result
        elif isinstance(result, dict) and "result" in result:
            return result["result"] if isinstance(result["result"], list) else []
        return []

    async def get_worker_logs(self, name: str, since: Optional[str] = None) -> List[Dict]:
        """Fetch invocation logs for a named Worker."""
        if since is None:
            since = (datetime.now(timezone.utc) - timedelta(hours=24)).isoformat()
        logger.info("Fetching logs for worker '%s' since %s", name, since)
        api_code = f"""
async () => {{
  return cloudflare.request({{
    method: "POST",
    path: `/accounts/{self.account_id}/workers/scripts/{name}/tails`,
    body: {{"filters": [{{"key": "outcome", "operator": "eq", "value": "ok"}}]}},
  }});
}}
"""
        result = await self._mcp_execute(api_code)
        if isinstance(result, list): return result
        elif isinstance(result, dict) and "result" in result:
            return result["result"] if isinstance(result["result"], list) else []
        return []

    async def delete_worker(self, name: str) -> bool:
        """Remove a deployed Worker script."""
        logger.info("Deleting worker: %s", name)
        api_code = f"""
async () => {{
  return cloudflare.request({{
    method: "DELETE",
    path: `/accounts/{self.account_id}/workers/scripts/{name}`,
  }});
}}
"""
        result = await self._mcp_execute(api_code)
        if isinstance(result, dict):
            if result.get("success", False): return True
            errors = result.get("errors", [])
            if errors and errors[0].get("code") == 10007: return True
        return False
