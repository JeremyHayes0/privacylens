import uuid
from unittest.mock import MagicMock

from app.core import queue as queue_module


def test_enqueue_scan_calls_rq_queue_enqueue(monkeypatch):
    """
    Verifies enqueue_scan's contract (it hands the right function and
    argument to RQ's Queue.enqueue) without opening a real connection
    to Redis -- monkeypatching the Queue instance's own .enqueue method
    intercepts the call before it would ever touch the network, since
    that's the one point where redis-py's lazy connection would
    actually try to connect.
    """
    fake_enqueue = MagicMock()
    monkeypatch.setattr(queue_module.scan_queue, "enqueue", fake_enqueue)

    scan_id = uuid.uuid4()
    queue_module.enqueue_scan(scan_id)

    fake_enqueue.assert_called_once()
    called_function, called_scan_id = fake_enqueue.call_args.args
    assert called_function.__name__ == "run_scan_task"
    assert called_scan_id == str(scan_id)
