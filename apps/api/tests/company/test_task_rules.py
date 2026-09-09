from datetime import UTC, datetime

from app.company.models import TaskStatus
from app.company.service import completion_timestamp


def test_done_task_gets_completion_timestamp() -> None:
    now = datetime(2026, 9, 9, 12, 0, tzinfo=UTC)

    assert completion_timestamp(TaskStatus.DONE, current=None, now=now) == now


def test_reopened_task_clears_completion_timestamp() -> None:
    completed = datetime(2026, 9, 8, 12, 0, tzinfo=UTC)

    assert completion_timestamp(TaskStatus.IN_PROGRESS, current=completed) is None
