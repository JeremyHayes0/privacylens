import uuid

from redis import Redis
from rq import Queue

from app.core.config import settings

# Neither Redis() nor Queue() connects to anything at construction
# time -- both the redis-py client and RQ's Queue are lazy, so
# importing this module never requires a live Redis instance (it's
# only touched when .enqueue() actually runs). That's what makes it
# safe to import this module in the test suite, which stubs out
# enqueue_scan rather than needing a running Redis to collect tests.
_redis_connection = Redis.from_url(settings.REDIS_URL)
scan_queue = Queue("scans", connection=_redis_connection)


def enqueue_scan(scan_id: uuid.UUID) -> None:
    """
    Enqueue a scan for background processing.

    Deliberately takes only a scan_id (serializable to a plain string),
    never a Scan ORM object or a live Session -- RQ serializes job
    arguments (via pickle) and executes them in a separate worker
    process, so nothing that depends on the caller's in-memory state,
    like an open SQLAlchemy Session, can safely cross that boundary.
    The worker task re-fetches the scan from the database itself (see
    app/worker/tasks.py).
    """
    # Local import: avoids an import cycle, since app/worker/tasks.py
    # has no reason to import anything from this module.
    from app.worker.tasks import run_scan_task

    scan_queue.enqueue(run_scan_task, str(scan_id))
