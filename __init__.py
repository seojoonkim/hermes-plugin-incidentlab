"""Hermes native observer: records sanitized failures in plugin state."""
import hashlib
import json
import re
import time

MAX_INCIDENTS = 100


def _kind(error):
    value = error.get("type") if isinstance(error, dict) else type(error).__name__ if error else ""
    value = re.sub(r"[^A-Za-z0-9_.-]", "", str(value))[:80]
    return value or "UnknownError"


def _save(ctx, session_id, task_id, failure):
    if not session_id:
        return
    rows = list(ctx.state.get("incidents", default=[]) or [])
    key = hashlib.sha256((session_id + "\0" + str(task_id) + "\0" + failure).encode()).hexdigest()
    for row in rows:
        if row.get("key") == key:
            row["count"] = int(row.get("count", 1)) + 1
            row["last_seen"] = int(time.time())
            ctx.state.set("incidents", rows[-MAX_INCIDENTS:])
            return
    now = int(time.time())
    rows.append({"key": key, "session_id": session_id, "task_id": str(task_id or ""),
                 "failure": failure, "count": 1, "first_seen": now,
                 "last_seen": now, "status": "open"})
    ctx.state.set("incidents", rows[-MAX_INCIDENTS:])


def register(ctx):
    def api_error(*, session_id="", task_id="", error=None, retryable=None,
                  retry_count=None, max_retries=None, **kwargs):
        if not session_id or retryable is True:
            return
        exhausted = retry_count is None or max_retries is None or int(retry_count) >= int(max_retries)
        if exhausted:
            _save(ctx, session_id, task_id, "api:" + _kind(error) + ":exhausted")

    def post_tool(*, session_id="", task_id="", tool_name="", result="", **kwargs):
        if not session_id:
            return
        try:
            parsed = json.loads(result) if isinstance(result, str) else result
            failed = isinstance(parsed, dict) and (parsed.get("success") is False or parsed.get("error") or
                isinstance(parsed.get("exit_code"), int) and parsed["exit_code"] != 0)
        except (ValueError, TypeError):
            failed = bool(re.search(r"\b(error|failed|traceback)\b", str(result), re.I))
        if failed:
            safe_tool = re.sub(r"[^A-Za-z0-9_.-]", "", str(tool_name))[:80] or "unknown"
            _save(ctx, session_id, task_id, "tool:" + safe_tool + ":error")

    def pre_llm(*, session_id="", **kwargs):
        if not session_id:
            return None
        rows = [r for r in (ctx.state.get("incidents", default=[]) or [])
                if r.get("session_id") == session_id and r.get("status") == "open"][-5:]
        if not rows:
            return None
        items = "\n".join("- " + r["failure"] + " (observed " + str(r.get("count", 1)) + "x)" for r in rows)
        return {"context": ("[Incident Lab — observed failures, not root-cause conclusions]\n" + items +
            "\nFinish the current user request. Then diagnose the cause, add a reproducing check, "
            "apply an authorized prevention fix, verify it, and report unresolved boundaries. "
            "Do not fabricate evidence, expand permissions, or restart services unless required.")[:1800]}

    ctx.register_hook("api_request_error", api_error)
    ctx.register_hook("post_tool_call", post_tool)
    ctx.register_hook("pre_llm_call", pre_llm)
