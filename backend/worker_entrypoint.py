"""
Entrypoint for an RQ worker process.

Run as its own process, separate from the API server:

    python worker_entrypoint.py

This is what actually executes queued scans -- the API process only
ever enqueues them (see app/core/queue.py) and returns immediately.
Without a worker process running, scans will sit in `queued` forever,
which is expected and by design (see the README's "Architecture"
section on why scans are asynchronous).
"""

from rq import Worker

from app.core.queue import scan_queue

if __name__ == "__main__":
    worker = Worker([scan_queue], connection=scan_queue.connection)
    worker.work()
