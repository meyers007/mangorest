"""AsyncJobs - a tiny in-process job registry + per-job handle.

Usage (target function):

    def my_target(request=None, job=None, **kwargs):
        for i in range(1, 11):
            time.sleep(1)
            job.running(message=f"step {i}/10")       # interim progress
        return {"answer": 42}                         # auto-finalized by runner

The webapi layer creates an `AsyncJobs(job_id)` and passes it to the target
function via `kwargs["job"]`. Clients poll via /jobs/status/?job_id=...,
which marks the job as 'fetched' once a terminal snapshot has been served.
/jobs/cleanup/ sweeps jobs that are both terminal AND fetched (or a specific
job_id, or all terminal jobs when all=1).
"""
from __future__ import annotations

import threading
from datetime import datetime

# Module-level registry. Shared across importers of this module.
_JOBS: dict[str, dict] = {}
_LOCK = threading.Lock()

_TERMINAL_PREFIXES = ("done", "error", "cancelled")


def _is_terminal(status: str) -> bool:
    s = (status or "")
    return any(s.startswith(p) for p in _TERMINAL_PREFIXES)


class AsyncJobs:
    """Handle around a single job dict in the shared `_JOBS` registry."""

    def __init__(self, job_id: str, target=None, **kwargs):
        """Create a job entry. `target` is the callable / name / URL the
        worker is running. Any additional kwargs are kept on the job for
        introspection; `job_name` is promoted to a top-level field if given."""
        self.job_id = job_id
        with _LOCK:
            _JOBS[job_id] = {
                "job_id":   job_id,
                "target":   target if (target is None or isinstance(target, str)) else getattr(target, "__name__", str(target)),
                "job_name": kwargs.get("job_name"),
                "user":     kwargs.get("user"),
                "status":   "queued",
                "message":  "queued",
                "percent_complete": 0,
                "result":   None,
                "start":    None,
                "end":      None,
                "fetched":  False,   # client has seen a terminal snapshot
                "kwargs":   kwargs,
            }
        self._job = _JOBS[job_id]

    # ---- lifecycle -------------------------------------------------------
    def start(self, message: str = "starting"):
        self._job["start"]   = datetime.now()
        self._job["status"]  = "running"
        self._job["message"] = f"{message} @ {self._job['start']}"
        return self

    def running(self, message=None, result=None, percent_complete=None):
        """Store an interim status message, partial result, and/or
        percent_complete (0..100)."""
        if message          is not None: self._job["message"]          = message
        if result           is not None: self._job["result"]           = result
        if percent_complete is not None: self._job["percent_complete"] = percent_complete
        # keep status as 'running' unless a terminal state was already set
        if not _is_terminal(self._job.get("status", "")):
            self._job["status"] = "running"
        return self

    def end(self, result=None, status: str = "done", message: str | None = None):
        self._job["end"] = datetime.now()
        if result  is not None: self._job["result"]  = result
        if message is not None: self._job["message"] = message
        took = (self._job["end"] - self._job["start"]) if self._job.get("start") else None
        self._job["status"] = f"{status} @ {self._job['end']} took: {took}"
        self._job["percent_complete"] = 100
        return self

    def error(self, exc):
        self._job["end"]     = datetime.now()
        self._job["status"]  = f"error @ {self._job['end']}"
        self._job["message"] = str(exc)
        return self

    def cancel(self, message: str = "cancelled by user"):
        self._job["end"]     = datetime.now()
        self._job["status"]  = f"cancelled @ {self._job['end']}"
        self._job["message"] = message
        return self

    # ---- inspection ------------------------------------------------------
    @property
    def data(self) -> dict:
        return self._job

    def is_terminal(self) -> bool:
        return _is_terminal(self._job.get("status", ""))

    def is_cancelled(self) -> bool:
        """True if the job has been cancelled. Target functions should poll
        this inside their loop and exit early when it returns True, e.g.:

            for item in items:
                if job.is_cancelled():
                    return {"aborted": True}
                ...
        """
        return (self._job.get("status") or "").startswith("cancelled")

    def snapshot(self, mark_fetched: bool = False) -> dict:
        """Return a copy of the job state. If `mark_fetched` and the job is
        terminal, flag it so cleanup() can reap it."""
        snap = {k: v for k, v in self._job.items() if k != "fetched"}
        if mark_fetched and self.is_terminal():
            self._job["fetched"] = True
        return snap

    # ---- class-level registry access ------------------------------------
    @classmethod
    def get(cls, job_id: str) -> "AsyncJobs | None":
        if job_id in _JOBS:
            inst = cls.__new__(cls)
            inst.job_id = job_id
            inst._job   = _JOBS[job_id]
            return inst
        return None

    @classmethod
    def all(cls) -> dict[str, dict]:
        return _JOBS

    @classmethod
    def remove(cls, job_id: str | None = None, only_fetched: bool = True) -> dict:
        """Remove one job (if job_id) or sweep terminal jobs.

        When sweeping, if `only_fetched=True` (default) only jobs the client
        has already polled to completion are removed; otherwise all terminal
        jobs are removed.
        """
        removed: list[str] = []
        with _LOCK:
            if job_id:
                if _JOBS.pop(job_id, None) is not None:
                    removed.append(job_id)
                return {"removed": removed}
            for jid, job in list(_JOBS.items()):
                if _is_terminal(job.get("status", "")):
                    if (not only_fetched) or job.get("fetched"):
                        _JOBS.pop(jid, None)
                        removed.append(jid)
        return {"removed": removed}
