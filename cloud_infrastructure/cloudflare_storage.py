"""Cloudflare R2 and D1 integration for forensic evidence storage and metadata management.

Provides durable, S3-compatible object storage (R2) for evidentiary files
and a managed SQLite database (D1) for case metadata, enabling rapid
queries across thousands of forensic records.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

ACCOUNT_ID: str = "ac0c08179402a581538ae0c886121040"
DEFAULT_R2_BUCKET: str = "argus-forensic-evidence"
DEFAULT_D1_DATABASE: str = "argus-metadata"


class CloudflareStorageManager:
    """Manages forensic evidence storage via R2 and metadata via D1."""

    def __init__(self, r2_bucket: Optional[str] = None, d1_database: Optional[str] = None) -> None:
        self.account_id: str = ACCOUNT_ID
        self.r2_bucket: str = r2_bucket or DEFAULT_R2_BUCKET
        self.d1_database: str = d1_database or DEFAULT_D1_DATABASE
        self._base_path: str = f"/accounts/{self.account_id}"
        logger.info("CloudflareStorageManager initialised: bucket=%s, database=%s", self.r2_bucket, self.d1_database)

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

    async def _ensure_r2_bucket(self) -> bool:
        logger.debug("Ensuring R2 bucket exists: %s", self.r2_bucket)
        code = f"""
async () => {{
  return cloudflare.request({{
    method: "PUT",
    path: `/accounts/{self.account_id}/r2/buckets/{self.r2_bucket}`,
    body: {{"name": "{self.r2_bucket}"}},
  }});
}}
"""
        result = await self._mcp_execute(code)
        return True

    async def _ensure_d1_database(self) -> bool:
        logger.debug("Ensuring D1 database exists: %s", self.d1_database)
        code = f"""
async () => {{
  return cloudflare.request({{
    method: "POST",
    path: `/accounts/{self.account_id}/d1/database`,
    body: {{"name": "{self.d1_database}"}},
  }});
}}
"""
        result = await self._mcp_execute(code)
        if isinstance(result, dict) and result.get("success", False):
            await self._init_d1_schema()
        return True

    async def _init_d1_schema(self) -> None:
        ddl_statements = [
            "CREATE TABLE IF NOT EXISTS case_metadata (case_id TEXT PRIMARY KEY, title TEXT NOT NULL, status TEXT DEFAULT 'open', priority TEXT DEFAULT 'medium', created_at TEXT DEFAULT (datetime('now')), updated_at TEXT DEFAULT (datetime('now')), assigned_to TEXT, jurisdiction TEXT, tags TEXT, notes TEXT);",
            "CREATE TABLE IF NOT EXISTS evidence_index (id INTEGER PRIMARY KEY AUTOINCREMENT, case_id TEXT NOT NULL, filename TEXT NOT NULL, storage_key TEXT NOT NULL, content_type TEXT, file_size INTEGER, checksum_sha256 TEXT, uploaded_at TEXT DEFAULT (datetime('now')), uploaded_by TEXT);",
            "CREATE TABLE IF NOT EXISTS audit_log (id INTEGER PRIMARY KEY AUTOINCREMENT, case_id TEXT NOT NULL, action TEXT NOT NULL, actor TEXT, details TEXT, timestamp TEXT DEFAULT (datetime('now')));",
            "CREATE INDEX IF NOT EXISTS idx_evidence_case_id ON evidence_index(case_id);",
            "CREATE INDEX IF NOT EXISTS idx_audit_case_id ON audit_log(case_id);",
        ]
        for ddl in ddl_statements:
            await self._execute_d1_query(ddl)

    async def _execute_d1_query(self, sql: str, params: Optional[List[Any]] = None) -> Any:
        db_uuid = await self._get_d1_database_uuid()
        if not db_uuid:
            return {"success": False, "errors": ["D1 database not found"]}
        code = f"""
async () => {{
  return cloudflare.request({{
    method: "POST",
    path: `/accounts/{self.account_id}/d1/database/{db_uuid}/query`,
    body: {{"sql": {json.dumps(sql)}, "params": {json.dumps(params or [])}}},
  }});
}}
"""
        return await self._mcp_execute(code)

    async def _get_d1_database_uuid(self) -> Optional[str]:
        code = f"""
async () => {{
  return cloudflare.request({{
    method: "GET",
    path: `/accounts/{self.account_id}/d1/database`,
  }});
}}
"""
        result = await self._mcp_execute(code)
        if isinstance(result, dict) and "result" in result:
            databases = result["result"]
            if isinstance(databases, list):
                for db in databases:
                    if db.get("name") == self.d1_database:
                        return db.get("uuid")
        return None

    def _storage_key(self, case_id: str, filename: str) -> str:
        ts = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
        safe_case = case_id.replace("/", "_").replace(" ", "_")
        safe_file = filename.replace("/", "_")
        return f"cases/{safe_case}/{ts}_{safe_file}"

    async def store_evidence(self, case_id: str, evidence_data: bytes, filename: str) -> str:
        await self._ensure_r2_bucket()
        storage_key = self._storage_key(case_id, filename)
        checksum = hashlib.sha256(evidence_data).hexdigest()
        logger.info("Storing evidence: case=%s, file=%s, key=%s, size=%d", case_id, filename, storage_key, len(evidence_data))
        code = f"""
async () => {{
  return cloudflare.request({{
    method: "PUT",
    path: `/accounts/{self.account_id}/r2/buckets/{self.r2_bucket}/objects/{storage_key}`,
    body: Buffer.from({list(evidence_data)}),
    contentType: "application/octet-stream",
    rawBody: true,
  }});
}}
"""
        result = await self._mcp_execute(code)
        if isinstance(result, dict) and result.get("success", False):
            await self._ensure_d1_database()
            await self._execute_d1_query(
                "INSERT INTO evidence_index (case_id, filename, storage_key, file_size, checksum_sha256) VALUES (?, ?, ?, ?, ?);",
                [case_id, filename, storage_key, len(evidence_data), checksum]
            )
            await self._execute_d1_query(
                "INSERT INTO audit_log (case_id, action, actor, details) VALUES (?, 'EVIDENCE_UPLOADED', 'system', ?);",
                [case_id, json.dumps({"filename": filename, "key": storage_key})]
            )
            return f"r2://{self.r2_bucket}/{storage_key}"
        raise RuntimeError(f"Failed to store evidence in R2: {result}")

    async def retrieve_evidence(self, case_id: str, filename: str) -> bytes:
        await self._ensure_d1_database()
        db_result = await self._execute_d1_query(
            "SELECT storage_key FROM evidence_index WHERE case_id = ? AND filename = ? ORDER BY uploaded_at DESC LIMIT 1;",
            [case_id, filename]
        )
        storage_key = None
        if isinstance(db_result, dict) and "result" in db_result:
            rows = db_result["result"][0].get("results", []) if isinstance(db_result["result"], list) else []
            if rows: storage_key = rows[0].get("storage_key")
        if not storage_key:
            raise FileNotFoundError(f"Evidence not found: case={case_id}, file={filename}")
        code = f"""
async () => {{
  return cloudflare.request({{
    method: "GET",
    path: `/accounts/{self.account_id}/r2/buckets/{self.r2_bucket}/objects/{storage_key}`,
  }});
}}
"""
        result = await self._mcp_execute(code)
        if isinstance(result, dict) and "result" in result:
            data = result["result"]
            if isinstance(data, str): return data.encode("utf-8")
            elif isinstance(data, bytes): return data
            elif isinstance(data, dict) and "data" in data:
                raw = data["data"]
                if isinstance(raw, list): return bytes(raw)
                return raw if isinstance(raw, bytes) else str(raw).encode("utf-8")
        raise FileNotFoundError(f"Failed to retrieve evidence: case={case_id}, file={filename}")

    async def list_evidence(self, case_id: str) -> List[str]:
        await self._ensure_d1_database()
        result = await self._execute_d1_query(
            "SELECT filename FROM evidence_index WHERE case_id = ? ORDER BY uploaded_at DESC;", [case_id]
        )
        filenames = []
        if isinstance(result, dict) and "result" in result:
            rows = result["result"][0].get("results", []) if isinstance(result["result"], list) else []
            for row in rows:
                if isinstance(row, dict) and "filename" in row: filenames.append(row["filename"])
        return filenames

    async def store_metadata_d1(self, case_id: str, metadata: Dict) -> bool:
        await self._ensure_d1_database()
        title = metadata.get("title", case_id)
        status = metadata.get("status", "open")
        priority = metadata.get("priority", "medium")
        assigned_to = metadata.get("assigned_to", "")
        jurisdiction = metadata.get("jurisdiction", "")
        tags = json.dumps(metadata.get("tags", [])) if isinstance(metadata.get("tags"), list) else str(metadata.get("tags", ""))
        notes = metadata.get("notes", "")
        result = await self._execute_d1_query(
            """INSERT INTO case_metadata (case_id, title, status, priority, assigned_to, jurisdiction, tags, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(case_id) DO UPDATE SET title=excluded.title, status=excluded.status,
            priority=excluded.priority, assigned_to=excluded.assigned_to,
            jurisdiction=excluded.jurisdiction, tags=excluded.tags, notes=excluded.notes,
            updated_at=datetime('now');""",
            [case_id, title, status, priority, assigned_to, jurisdiction, tags, notes]
        )
        success = isinstance(result, dict) and result.get("success", False)
        if success:
            await self._execute_d1_query(
                "INSERT INTO audit_log (case_id, action, actor, details) VALUES (?, 'METADATA_UPDATED', 'system', ?);",
                [case_id, json.dumps(metadata)]
            )
        return success

    async def query_metadata_d1(self, sql: str) -> List[Dict]:
        await self._ensure_d1_database()
        result = await self._execute_d1_query(sql)
        rows = []
        if isinstance(result, dict) and "result" in result:
            result_sets = result["result"]
            if isinstance(result_sets, list) and len(result_sets) > 0:
                raw_rows = result_sets[0].get("results", [])
                for row in raw_rows:
                    if isinstance(row, dict): rows.append(row)
        return rows

    async def get_case_summary(self, case_id: str) -> Dict[str, Any]:
        await asyncio.gather(self._ensure_r2_bucket(), self._ensure_d1_database())
        meta_rows = await self.query_metadata_d1(f"SELECT * FROM case_metadata WHERE case_id = '{case_id}';")
        metadata = meta_rows[0] if meta_rows else {}
        evidence_files = await self.list_evidence(case_id)
        audit_rows = await self.query_metadata_d1(f"SELECT * FROM audit_log WHERE case_id = '{case_id}' ORDER BY timestamp DESC LIMIT 20;")
        usage_rows = await self.query_metadata_d1(f"SELECT COALESCE(SUM(file_size), 0) AS total_bytes FROM evidence_index WHERE case_id = '{case_id}';")
        total_bytes = usage_rows[0].get("total_bytes", 0) if usage_rows else 0
        return {
            "case_id": case_id, "metadata": metadata, "evidence_files": evidence_files,
            "evidence_count": len(evidence_files), "audit_log": audit_rows,
            "storage_usage": {"total_bytes": total_bytes, "total_kb": round(total_bytes/1024, 2), "total_mb": round(total_bytes/(1024*1024), 2)},
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }
